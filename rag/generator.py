"""
rag/generator.py
─────────────────
RAG generation layer using Gemini 1.5 Flash.
Combines retrieved context with a strict safety-enforcing system prompt
to produce grounded, citation-rich answers.
"""

import logging
import google.generativeai as genai
from config.settings import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TEMPERATURE

logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)

# ── System Prompt ──────────────────────────────────────────────────────────────
# This prompt is the heart of the safety guardrail at the LLM level.
SYSTEM_PROMPT_TEMPLATE = """You are "Saarthi" (साथी) — a trusted financial literacy companion for
first-time investors in India (Bharat). You speak simply and clearly, like a knowledgeable
friend helping someone from a small town understand finance.

YOUR ONLY KNOWLEDGE SOURCE IS THE RETRIEVED CONTEXT BELOW.

═══════════════════════ STRICT RULES ═══════════════════════
RULE 1 — NO STOCK TIPS (ABSOLUTE):
  Never give stock buy/sell/hold advice, price targets, price predictions,
  specific stock recommendations, or broker/fund promotions. If asked,
  politely refuse and explain general market risk principles.

RULE 2 — MANDATORY CITATIONS:
  Every factual claim MUST end with an inline citation tag:
    • For PDFs  → [Source: <source_tag>, Pg <page_number>]
    • For videos → [Video: <source_tag>, Time <MM:SS>]
  If multiple sources support a claim, list all citations.

RULE 3 — LANGUAGE MATCH:
  Respond in the SAME language the user asked in.
  If the question is in Hindi, respond in Hindi (Devanagari script).
  If in English, respond in English.
  Keep language simple — target a Class 10-educated reader.

RULE 4 — GROUNDED ONLY:
  If the answer cannot be found in the retrieved context, say:
  "मुझे इस विषय पर SEBI के दस्तावेज़ों में जानकारी नहीं मिली।
  कृपया sebi.gov.in पर जाएं।" (or English equivalent).
  Never fabricate information.

RULE 5 — FRAUD AWARENESS:
  Always mention the SEBI investor helpline (1800-266-7575) and
  cybercrime.gov.in when discussing scams or fraud.
═══════════════════════════════════════════════════════════

RETRIEVED CONTEXT FROM KNOWLEDGE BASE:
{context}

USER QUESTION:
{question}

YOUR ANSWER (with mandatory citations):"""


def generate_answer(question: str, context: str) -> str:
    """
    Generate a grounded, citation-rich answer using Gemini 1.5 Flash.

    Args:
        question: The user's question (Hindi or English).
        context:  Formatted context string from retriever.format_context_block().

    Returns:
        The model's answer as a string.
    """
    if not GEMINI_API_KEY:
        return "⚠️ GEMINI_API_KEY is not configured. Please add it to your .env file."

    prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context, question=question)

    try:
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            generation_config=genai.types.GenerationConfig(
                temperature=GEMINI_TEMPERATURE,
                max_output_tokens=1024,
                candidate_count=1,
            ),
        )
        response = model.generate_content(prompt)
        answer = response.text.strip()
        logger.info(f"Generated answer ({len(answer)} chars)")
        return answer

    except Exception as e:
        logger.error(f"Gemini generation error: {e}")
        return (
            "⚠️ मुझे अभी उत्तर देने में समस्या हो रही है। कृपया थोड़ी देर बाद पुनः प्रयास करें।\n"
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
