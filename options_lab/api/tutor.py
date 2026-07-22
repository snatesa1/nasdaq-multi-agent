import logging
import json
from typing import Dict, Any, List, Optional
from .config import settings

logger = logging.getLogger(__name__)

TUTOR_SYSTEM_PROMPT = """
You are OptionsLab's Socratic Tutor, acting in the capacity of a Senior Financial Analyst and Research Desk Assistant.
Your style is that of an experienced equity trader and senior analyst. You have a sound, professional understanding of financial markets, capital allocation, corporate earnings, risk exposure, portfolio hedging, and regulatory developments.

CORE TUTORIAL STYLE:
1. Socratic Method: Do not just feed the user direct answers. Guide them to discover insights by asking short, targeted, and professional questions. Break down complex topics into clear steps.
2. Analyst & Trader Persona: Talk like a seasoned market professional. Connect concepts to corporate finance (e.g., share buybacks, cash flow management, debt structures), macro trends (interest rates, CPI, earnings season), and risk management (VIX spikes, delta exposure, credit risk).
3. Real-World Applications: Explain financial mechanisms through concrete analogies and institutional examples (e.g., how commercial banks hedge interest rate risk, or how a tech firm uses collar structures to hedge key employee stock grants).
4. Socratic Quiz: Challenge the user with real-world scenarios to test their financial reasoning.
5. Quantitative Rigor: Provide mathematically correct guidance (e.g., explain Black-Scholes assumptions, GBM simulations, time-step scaling, or log returns) while making the underlying financial logic intuitive.
"""

class SocraticTutor:
    def __init__(self):
        self.model_name = settings.VERTEX_MODEL
        
    def generate_response(
        self,
        message: str,
        chat_history: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generates Socratic response based on conversation history and active app context.
        """
        # Format chat history + context into prompt
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
            try:
                import requests
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={api_key}"
                headers = {
                    "Content-Type": "application/json"
                }
                data = {
                    "systemInstruction": {
                        "parts": [{"text": TUTOR_SYSTEM_PROMPT}]
                    },
                    "contents": [{"parts": [{"text": full_prompt}]}]
                }
                logger.info(f"Calling free Gemini API via Google AI Studio for Socratic Tutor: {self.model_name}")
                response = requests.post(url, headers=headers, json=data, timeout=30)
                response.raise_for_status()
                res_json = response.json()
                return res_json["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                logger.warning(f"⚠️ Free Gemini API tutor response failed: {e}.")
                disable_fallback = getattr(settings, "DISABLE_VERTEX_FALLBACK", False)
                if disable_fallback:
                    raise Exception(f"Google AI Studio call failed: {e}. Fallback to Vertex AI is disabled.")
                logger.warning("Falling back to Vertex AI.")

        try:
            # Initialize Vertex AI
            import vertexai
            from vertexai.generative_models import GenerativeModel
            location = os.getenv("GCP_LOCATION") or os.getenv("VERTEX_LOCATION") or "us-central1"
            vertexai.init(project=settings.PROJECT_ID, location=location)
            # Map standard model names to Vertex AI specific versioned names
            vertex_model_name = self.model_name
            if vertex_model_name == "gemini-flash-latest":
                vertex_model_name = "gemini-2.5-flash"
            elif vertex_model_name == "gemini-1.5-flash":
                vertex_model_name = "gemini-1.5-flash-002"
            elif vertex_model_name == "gemini-1.5-pro":
                vertex_model_name = "gemini-1.5-pro-002"
                
            model = GenerativeModel(
                model_name=vertex_model_name,
                system_instruction=TUTOR_SYSTEM_PROMPT
            )
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating Socratic tutor response: {e}")
            return (
                "I apologize, but I encountered an error connecting to my core brain (Gemini). "
                "Let's focus on the math of the options: call options give you the right to buy, "
                "while put options give you the right to sell. What strategy would you like to explore next?"
            )
            
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
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
                headers = {
                    "Content-Type": "application/json",
                    "X-goog-api-key": api_key
                }
                data = {
                    "contents": [{"parts": [{"text": prompt}]}]
                }
                logger.info(f"Calling free Gemini API via Google AI Studio for concept '{concept}': {self.model_name}")
                response = requests.post(url, headers=headers, json=data, timeout=30)
                response.raise_for_status()
                res_json = response.json()
                return res_json["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                logger.warning(f"⚠️ Free Gemini API concept explanation failed: {e}. Falling back to Vertex AI.")

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
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
                headers = {
                    "Content-Type": "application/json",
                    "X-goog-api-key": api_key
                }
                data = {
                    "contents": [{"parts": [{"text": prompt}]}]
                }
                response = requests.post(url, headers=headers, json=data, timeout=30)
                response.raise_for_status()
                res_json = response.json()
                return res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception as e:
                logger.warning(f"⚠️ Free Gemini API summarize_learnings failed: {e}. Falling back to Vertex AI.")

        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel
            vertexai.init(project=settings.PROJECT_ID)
            model = GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error generating learning summary: {e}")
            return "- Discussed financial markets and quantitative modeling strategies."

