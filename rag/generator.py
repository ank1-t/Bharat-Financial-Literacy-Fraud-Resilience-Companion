"""
rag/generator.py
─────────────────
RAG generation layer using Gemini 1.5 Flash.
Combines retrieved context with a strict safety-enforcing system prompt
to produce grounded, citation-rich answers.
"""

import logging
import google.generativeai as genai
from config.settings import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TEMPERATURE, LANGUAGE_NAMES

logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)

# ── System Prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT_TEMPLATE = """You are "Saarthi" (साथी) — a warm, trusted, and empathetic financial education mentor built for everyday citizens and first-time investors across India (Bharat).
You explain financial concepts clearly, like an encouraging elder brother or mentor who wants to protect their family's hard-earned savings.

CONTEXT FROM OFFICIAL KNOWLEDGE BASE:
{context}

USER QUESTION:
{question}

RESPONSE LANGUAGE:
Write the full answer in {answer_language}. Do not switch to Hindi or English unless that is the selected language. Keep citation tags exactly as written in the context.

═══════════════════════ INSTRUCTIONS FOR YOUR ANSWER ═══════════════════════
1. **Directly Answer the Core Question First:**
   - Always focus 80% of your answer on thoroughly and clearly explaining what the user asked about (e.g. for "what is SIP?", explain Systematic Investment Plan, rupee cost averaging, power of compounding, and how it works).
   - Use simple real-world analogies (e.g. SIP is like a monthly RD or piggy bank into mutual funds).

2. **Structure & Formatting:**
   - 1-2 sentence warm introduction and direct definition.
   - Core concepts in bullet points with **bold titles**.
   - Use the selected response language above, including for headings, cautions, and explanations.
   - Add a brief 1-2 bullet "⚠️ Things to Keep in Mind / ध्यान दें" at the end (e.g., market risk, no guaranteed returns). Do not let scam warnings overshadow the actual answer.
   - Only bring in fraud hotlines (1930 / 1800-266-7575) when the topic involves scams, fraud, or high-risk claims.

3. **Citations:**
   - Include appropriate citation tags where supported by context: [Source: <source_tag>, Pg <page_number>] or [Video: <source_tag>, Time <MM:SS>].

4. **Strict Rules:**
   - Zero stock tips or specific fund promotions.
   - Zero guaranteed returns promises.

YOUR DIRECT, COMPREHENSIVE & HELPFUL ANSWER:"""


def _build_prompt(question: str, context: str, language_code: str) -> str:
    answer_language = LANGUAGE_NAMES.get(language_code, LANGUAGE_NAMES["en-IN"])
    return SYSTEM_PROMPT_TEMPLATE.format(
        context=context,
        question=question,
        answer_language=answer_language,
    )


def generate_answer(question: str, context: str, language_code: str = "en-IN") -> str:
    """
    Generate a grounded, citation-rich answer using Gemini 1.5 Flash.

    Args:
        question: The user's question (Hindi or English).
        context:  Formatted context string from retriever.format_context_block().
        language_code: Selected BCP-47 response language code.

    Returns:
        The model's answer as a string.
    """
    if not GEMINI_API_KEY:
        return "⚠️ GEMINI_API_KEY is not configured. Please add it to your .env file."

    prompt = _build_prompt(question, context, language_code)

    fallback_models = [GEMINI_MODEL, "gemini-3.5-flash-lite", "gemini-3-flash-preview", "gemini-3.5-flash", "gemini-3.8-flash"]
    # De-duplicate while preserving order
    seen = set()
    models_to_try = [m for m in fallback_models if not (m in seen or seen.add(m))]

    last_error = None
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=genai.types.GenerationConfig(
                    temperature=GEMINI_TEMPERATURE,
                    max_output_tokens=1024,
                    candidate_count=1,
                ),
            )
            response = model.generate_content(prompt)
            if response and response.text:
                answer = response.text.strip()
                logger.info(f"Generated answer with {model_name} ({len(answer)} chars)")
                return answer
        except Exception as e:
            last_error = e
            logger.warning(f"Model {model_name} failed: {e}. Trying fallback if available...")

    logger.error(f"All Gemini generation models failed: {last_error}")
    err_str = str(last_error) if last_error else "Unknown error"
    
    if "429" in err_str or "quota" in err_str.lower():
        return (
            "⚠️ **API Quota Exceeded (दर सीमा समाप्त):** Gemini API free tier limit reached for today.\n\n"
            "कृपया थोड़ी देर बाद प्रयास करें या `.env` फ़ाइल में नया Google AI Studio API key डालें।"
        )
    return (
        f"⚠️ मुझे अभी उत्तर देने में समस्या हो रही है ({err_str[:80]}). कृपया थोड़ी देर बाद पुनः प्रयास करें।\n"
        "⚠️ I'm having trouble generating a response right now. Please try again shortly."
    )



def extract_citations(answer: str) -> list[str]:
    """
    Parse all citation tags from a generated answer for display purposes.

    Returns:
        List of citation strings like ["[Source: SEBI, Pg 5]", "[Video: NSE, Time 02:10]"]
    """
    import re
    pattern = r'\[(?:Source|Video):[^\]]+\]'
    return re.findall(pattern, answer)
