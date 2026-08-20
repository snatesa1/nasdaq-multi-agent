import logging
import json
import os
from typing import Dict, Any, List, Optional
from .config import settings

logger = logging.getLogger(__name__)

TUTOR_SYSTEM_PROMPT = """
You are OptionsLab's Socratic Tutor, acting in the capacity of a Senior Financial Analyst and Quantitative Options Desk Director.
Your style is that of an experienced equity derivatives trader and senior risk manager following Google's LearnLM pedagogical principles.

LEARNLM SOCRATIC PEDAGOGY PRINCIPLES:
1. Encourage Productive Struggle: DO NOT give direct formulas or answers immediately. Guide the user to discover options mechanics, Greeks, and volatility dynamics step-by-step.
2. Misconception Diagnosis: Actively spot common options misconceptions (e.g. confusing Delta with Probability of Profit, misinterpreting Vega as a fixed number rather than sensitivity to 1% vol change, or forgetting IV crush after earnings) and gently lead the user to self-correct.
3. Adaptive Scaffolding: Tailor the difficulty to the user's responses. If they struggle, provide an intuitive analogy (e.g., house insurance for protective puts) or break down the question into simpler sub-questions.
4. Quantitative Rigor: Maintain institutional standards (Black-Scholes assumptions, log-normal price distributions, Gamma risk, Theta decay acceleration near expiration) while keeping explanations intuitive.
5. Real-World Applications: Connect concepts to live market scenarios (FOMC decisions, VIX spikes, institutional collar hedging, delta-neutral market making).
6. Fundamental Indexation (Arnott et al. 80/20 Rule): When discussing index construction or value vs growth:
   - Highlight the 20% drag of Market Cap weighting (noise causes prices to fluctuate around true value, leading cap-weighted indexes to systematically over-weight overvalued stocks and under-weight undervalued stocks).
   - Explain the 6 Fundamental size metrics (Book Value, Cash Flow/Operating Income, Revenues, Sales, Gross Dividends, Total Employment) as objective "Main Street" size measures.
   - Connect fundamental weight divergence (W_fund vs W_cap) to actionable options overlays: write covered calls / buy protective puts on market-cap overweighted stocks (negative delta), and sell cash-secured puts or buy long call LEAPs on fundamental underweighted stocks (positive delta).

"""

import threading

class SocraticTutor:
    def __init__(self):
        self._model_pool = list(settings.GEMINI_MODEL_POOL)
        if not self._model_pool:
            self._model_pool = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-1.5-flash"]
        self._rr_index = 0
        self._lock = threading.Lock()

    def _get_ordered_models(self) -> List[str]:
        """
        Returns models ordered starting from the current round-robin index,
        distributing requests evenly across the pool to balance RPM and RPD.
        """
        with self._lock:
            start_idx = self._rr_index % len(self._model_pool)
            self._rr_index = (self._rr_index + 1) % len(self._model_pool)
        
        # Rotated list: e.g. [Model_i, Model_i+1, ..., Model_i-1]
        return self._model_pool[start_idx:] + self._model_pool[:start_idx]

    def _call_gemini_with_fallback(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        enable_grounding: bool = False,
        timeout: int = 25
    ) -> Optional[str]:
        """
        Executes a prompt across the Round-Robin model pool with instant failover on 429/503/timeout.
        """
        api_key = settings.GEMINI_API_KEY
        ordered_models = self._get_ordered_models()

        if api_key:
            import requests
            headers = {"Content-Type": "application/json"}
            payload: Dict[str, Any] = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            if system_prompt:
                payload["systemInstruction"] = {
                    "parts": [{"text": system_prompt}]
                }
            if enable_grounding:
                payload["tools"] = [{"googleSearch": {}}]

            for model in ordered_models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                try:
                    logger.info(f"⚡ [Round-Robin Load Balancer] Calling Gemini model '{model}' (grounding={enable_grounding})...")
                    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
                    
                    if resp.status_code == 200:
                        res_json = resp.json()
                        candidate = res_json.get("candidates", [{}])[0]
                        text_content = candidate.get("content", {}).get("parts", [{}])[0].get("text", "")
                        if text_content:
                            # Attach grounding citations if present
                            grounding_metadata = candidate.get("groundingMetadata", {})
                            web_sources = grounding_metadata.get("groundingChunks", [])
                            if web_sources:
                                text_content += "\n\n**🔍 Grounding Sources:**\n"
                                for chunk in web_sources[:3]:
                                    web = chunk.get("web", {})
                                    if web.get("uri") and web.get("title"):
                                        text_content += f"- [{web['title']}]({web['uri']})\n"
                            return text_content
                    elif resp.status_code in (429, 503):
                        logger.warning(f"⚠️ Model '{model}' returned HTTP {resp.status_code} (Rate Limit / Unavailable). Failing over immediately to next model...")
                        continue
                    else:
                        logger.warning(f"⚠️ Model '{model}' returned HTTP {resp.status_code}: {resp.text[:120]}. Failing over...")
                        continue
                except Exception as e:
                    logger.warning(f"⚠️ Error or timeout connecting to model '{model}': {e}. Failing over to next model...")
                    continue

        # Vertex AI fallback if configured & not disabled
        if os.getenv("DISABLE_VERTEX_FALLBACK", "false").lower() != "true":
            try:
                import vertexai
                from vertexai.generative_models import GenerativeModel, Tool
                location = os.getenv("GCP_LOCATION") or os.getenv("VERTEX_LOCATION") or "us-central1"
                vertexai.init(project=settings.PROJECT_ID, location=location)
                
                tools = [Tool.from_google_search_retrieval()] if enable_grounding else None
                model_inst = GenerativeModel(
                    model_name="gemini-2.5-flash",
                    system_instruction=system_prompt,
                    tools=tools
                )
                response = model_inst.generate_content(prompt)
                if response and response.text:
                    return response.text
            except Exception as e:
                logger.error(f"Vertex AI fallback failed: {e}")

        return None

    def _prune_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prunes large nested arrays, path matrices, and verbose payloads from context
        to maintain a compact, high-speed context window.
        """
        pruned = {}
        for k, v in context.items():
            if isinstance(v, list):
                if len(v) > 5:
                    pruned[k] = v[:5] + [f"... ({len(v) - 5} more items omitted for brevity)"]
                else:
                    pruned[k] = v
            elif isinstance(v, dict):
                pruned[k] = {sub_k: sub_v for sub_k, sub_v in list(v.items())[:8]}
            elif isinstance(v, (str, int, float, bool)) or v is None:
                pruned[k] = v
        return pruned

    def generate_response(
        self,
        message: str,
        chat_history: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
        enable_grounding: bool = False
    ) -> str:
        """
        Generates Socratic response based on conversation history and active app context.
        """
        prompt_parts = []
        
        if context:
            pruned_ctx = self._prune_context(context)
            prompt_parts.append(f"CURRENT PLAYGROUND/PORTFOLIO CONTEXT:\n{json.dumps(pruned_ctx, indent=2)}\n\n")
            
        prompt_parts.append("CONVERSATION HISTORY:")
        # Keep last 10 messages for high-speed response times and low token usage
        recent_history = chat_history[-10:] if len(chat_history) > 10 else chat_history
        for msg in recent_history:
            role = "User" if msg.get("role") == "user" else "Assistant"
            prompt_parts.append(f"{role}: {msg.get('content', '')}")
            
        prompt_parts.append(f"User: {message}")
        prompt_parts.append("Assistant:")
        
        full_prompt = "\n".join(prompt_parts)

        result = self._call_gemini_with_fallback(
            prompt=full_prompt,
            system_prompt=TUTOR_SYSTEM_PROMPT,
            enable_grounding=enable_grounding,
            timeout=25
        )

        if result:
            return result

        return (
            "I apologize, but I encountered a temporary connection issue. "
            "Let's continue: what is your quantitative intuition or risk objective for this position?"
        )

    def generate_hint(
        self,
        chat_history: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generates a LearnLM pedagogical hint to help the user move forward without giving away the direct answer.
        """
        prompt = f"""
You are an expert Socratic options tutor applying Google LearnLM principles.
The user is working through a Socratic learning scenario on options trading and quantitative finance.

Provide a helpful, encouraging **💡 HINT** (2-3 sentences max) that scaffold their thinking:
- Do NOT reveal the direct answer or final calculation.
- Point out a key relationship, principle, or formula variable they should consider (e.g., think about how Theta behaves as DTE approaches 0, or how Delta changes as the stock moves ITM).
- End with a motivating question to guide their next thought.

CONVERSATION HISTORY:
{json.dumps(chat_history[-6:], indent=2)}

ACTIVE CONTEXT:
{json.dumps(context or {}, indent=2)}
"""
        result = self._call_gemini_with_fallback(prompt=prompt, timeout=15)
        if result:
            return "💡 **Hint:** " + result.replace("💡 **Hint:**", "").strip()

        return "💡 **Hint:** Think about how time decay (Theta) accelerates as expiration approaches, and consider the direction of your Delta exposure."

    def get_concept_explanation(self, concept: str) -> str:
        """
        Generates a structured Socratic explanation card for a specific concept.
        """
        prompt = f"""
You are a Socratic finance tutor. Explain the following concept: "{concept}".
Include:
1. An intuitive layman's summary.
2. A clear real-world analogy.
3. A short question for the reader to test their intuition about the concept.
Use clear Markdown formatting with nice headings.
"""
        result = self._call_gemini_with_fallback(prompt=prompt, timeout=20)
        if result:
            return result

        return f"Unable to fetch automated explanation for '{concept}'. Let's discuss its options mechanics directly!"

    def summarize_learnings(self, chat_history: List[Dict[str, str]]) -> str:
        """
        Generates 3-5 key financial learnings/takeaways from the chat history.
        """
        if len(chat_history) <= 1:
            return "- Started a Socratic learning session."
            
        transcript = []
        for msg in chat_history[-12:]:
            role = "User" if msg.get("role") == "user" else "Tutor"
            transcript.append(f"{role}: {msg.get('content', '')}")
        full_transcript = "\n".join(transcript)
        
        prompt = f"""
Analyze the following Socratic chat history between a Senior Financial Analyst/Research Desk Assistant and a user.
Extract 3 to 5 key financial learnings, takeaways, or concepts discussed in this conversation as concise, high-value bullet points.
Return only the bullet points in plain text format, with each point starting with a dash ("- "). Do not include any introductory or concluding text.

CHAT HISTORY:
{full_transcript}
"""
        result = self._call_gemini_with_fallback(prompt=prompt, timeout=20)
        if result:
            return result.strip()

        return "- Discussed options Greeks, volatility surfaces, and systematic trading strategies."
