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

class SocraticTutor:
    def __init__(self):
        self.model_name = settings.VERTEX_MODEL
        
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
            prompt_parts.append(f"CURRENT PLAYGROUND/PORTFOLIO CONTEXT:\n{json.dumps(context, indent=2)}\n\n")
            
        prompt_parts.append("CONVERSATION HISTORY:")
        for msg in chat_history:
            role = "User" if msg["role"] == "user" else "Assistant"
            prompt_parts.append(f"{role}: {msg['content']}")
            
        prompt_parts.append(f"User: {message}")
        prompt_parts.append("Assistant:")
        
        full_prompt = "\n".join(prompt_parts)

        api_key = settings.GEMINI_API_KEY
        if api_key:
            import requests
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            
            data = {
                "systemInstruction": {
                    "parts": [{"text": TUTOR_SYSTEM_PROMPT}]
                },
                "contents": [{"parts": [{"text": full_prompt}]}]
            }
            
            if enable_grounding:
                data["tools"] = [{"googleSearch": {}}]

            # Try up to 3 times with exponential backoff
            for attempt in range(1, 4):
                try:
                    logger.info(f"Calling Gemini API via Google AI Studio for Socratic Tutor (attempt {attempt}): {self.model_name} (grounding={enable_grounding})")
                    response = requests.post(url, headers=headers, json=data, timeout=60)
                    response.raise_for_status()
                    res_json = response.json()
                    
                    candidate = res_json["candidates"][0]
                    text_content = candidate["content"]["parts"][0]["text"]
                    
                    # Check for Google Search Grounding sources
                    grounding_metadata = candidate.get("groundingMetadata", {})
                    web_sources = grounding_metadata.get("groundingChunks", [])
                    if web_sources:
                        text_content += "\n\n**🔍 Grounding Sources:**\n"
                        for chunk in web_sources[:3]:
                            web = chunk.get("web", {})
                            if web.get("uri") and web.get("title"):
                                text_content += f"- [{web['title']}]({web['uri']})\n"
                                
                    return text_content
                except Exception as e:
                    logger.warning(f"⚠️ Gemini API attempt {attempt} failed: {e}")
                    if attempt < 3:
                        import time
                        time.sleep(1)

        # Check if Vertex AI fallback is disabled
        if os.getenv("DISABLE_VERTEX_FALLBACK", "false").lower() == "true":
            logger.error("Vertex AI fallback is disabled and Gemini API failed.")
            return (
                "I apologize, but I encountered a network timeout connecting to Gemini. "
                "Please try sending your message again."
            )

        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel, Tool
            location = os.getenv("GCP_LOCATION") or os.getenv("VERTEX_LOCATION") or "us-central1"
            vertexai.init(project=settings.PROJECT_ID, location=location)
            
            vertex_model_name = self.model_name
            if vertex_model_name == "gemini-flash-latest":
                vertex_model_name = "gemini-2.5-flash"
            elif vertex_model_name == "gemini-1.5-flash":
                vertex_model_name = "gemini-1.5-flash-002"
            elif vertex_model_name == "gemini-1.5-pro":
                vertex_model_name = "gemini-1.5-pro-002"
                
            tools = [Tool.from_google_search_retrieval()] if enable_grounding else None
            
            model = GenerativeModel(
                model_name=vertex_model_name,
                system_instruction=TUTOR_SYSTEM_PROMPT,
                tools=tools
            )
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating Socratic tutor response: {e}")
            return (
                "I apologize, but I encountered an error connecting to my core brain (Gemini). "
                "Let me know what options strategy or Greeks question you'd like to break down."
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
        api_key = settings.GEMINI_API_KEY
        if api_key:
            try:
                import requests
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={api_key}"
                headers = {"Content-Type": "application/json"}
                data = {"contents": [{"parts": [{"text": prompt}]}]}
                response = requests.post(url, headers=headers, json=data, timeout=20)
                response.raise_for_status()
                res_json = response.json()
                return "💡 **Hint:** " + res_json["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                logger.warning(f"Failed to generate hint via AI Studio: {e}")
                
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
        api_key = settings.GEMINI_API_KEY
        if api_key:
            try:
                import requests
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={api_key}"
                headers = {"Content-Type": "application/json"}
                data = {"contents": [{"parts": [{"text": prompt}]}]}
                response = requests.post(url, headers=headers, json=data, timeout=30)
                response.raise_for_status()
                res_json = response.json()
                return res_json["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                logger.warning(f"⚠️ Concept explanation failed via AI Studio: {e}")

        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel
            vertexai.init(project=settings.PROJECT_ID)
            model = GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating explanation for {concept}: {e}")
            return f"Unable to fetch automated explanation for '{concept}'. Let's talk about it directly!"

    def summarize_learnings(self, chat_history: List[Dict[str, str]]) -> str:
        """
        Generates 3-5 key financial learnings/takeaways from the chat history.
        """
        if len(chat_history) <= 1:
            return "- Started a Socratic learning session."
            
        transcript = []
        for msg in chat_history:
            role = "User" if msg["role"] == "user" else "Tutor"
            transcript.append(f"{role}: {msg['content']}")
        full_transcript = "\n".join(transcript)
        
        prompt = f"""
Analyze the following Socratic chat history between a Senior Financial Analyst/Research Desk Assistant and a user.
Extract 3 to 5 key financial learnings, takeaways, or concepts discussed in this conversation as concise, high-value bullet points.
Return only the bullet points in plain text format, with each point starting with a dash ("- "). Do not include any introductory or concluding text.

CHAT HISTORY:
{full_transcript}
"""
        api_key = settings.GEMINI_API_KEY
        if api_key:
            try:
                import requests
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={api_key}"
                headers = {"Content-Type": "application/json"}
                data = {"contents": [{"parts": [{"text": prompt}]}]}
                response = requests.post(url, headers=headers, json=data, timeout=30)
                response.raise_for_status()
                res_json = response.json()
                return res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception as e:
                logger.warning(f"⚠️ summarize_learnings failed via AI Studio: {e}")

        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel
            vertexai.init(project=settings.PROJECT_ID)
            model = GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error generating learning summary: {e}")
            return "- Discussed options Greeks and volatility strategies."
