import logging
import json
from typing import Dict, Any, List, Optional
from .config import settings

logger = logging.getLogger(__name__)

TUTOR_SYSTEM_PROMPT = """
You are OptionsLab's Socratic Tutor, an expert options educator and quantitative finance guide.
Your purpose is to teach the user options trading, quantitative math (like Geometric Brownian Motion and Black-Scholes), risk management, and hedging strategies in a Socratic way.

CORE TUTORIAL STYLE:
1. Socratic Method: Do not just feed the student answers. Guide them to discover concepts by asking short, targeted questions. Break down complex topics into digestible steps.
2. Analogies & Real-World Examples: Use everyday metaphors (e.g., insurance, real estate options, car leasing) to explain financial mechanisms.
3. Interactive Analysis: When the student gives a portfolio scenario (e.g., 100 shares of PANW, protecting against earnings drop), help them calculate the exact math (premium, break-even, strike choices, delta values) and ask them to evaluate the trade-offs of different hedging structures (Collar, Protective Put, Covered Call).
4. Socratic Quiz: Give mini scenario-based challenges to test their understanding.
5. Code Analysis: Explain that in Monte Carlo simulations, multiplying by T inside a loop of N steps is a classic mistake. Instead, step-by-step simulation uses dt = T/N. Explain how the time grid and standard random variables compound correctly.

MARKDOWN & VISUAL FORMATTING:
- Use clean formatting, lists, tables, and bold highlights.
- Highlight risk warnings clearly with bold or quotes (e.g., naked call risks).
- Present option chains or strategy comparison tables when evaluating trades.
- Keep responses relatively concise to fit a conversational web layout.
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
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
                headers = {
                    "Content-Type": "application/json",
                    "X-goog-api-key": api_key
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
                logger.warning(f"⚠️ Free Gemini API tutor response failed: {e}. Falling back to Vertex AI.")

        try:
            # Initialize Vertex AI
            import vertexai
            from vertexai.generative_models import GenerativeModel
            vertexai.init(project=settings.PROJECT_ID)
            model = GenerativeModel(
                model_name=self.model_name,
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
