"""
guardrails/safety_filter.py
────────────────────────────
Two-layer safety filter that prevents any stock tips, price predictions,
buy/sell advice, or broker promotions from entering the RAG pipeline.

Layer 1 — Pre-LLM Regex Filter (fast, zero-cost):
  Blocks obvious violating queries before they reach Gemini.

Layer 2 — Post-LLM Pattern Check (lightweight string scan):
  Scans the generated answer for any advice that may have slipped through.
"""

import re
import logging

logger = logging.getLogger(__name__)

# ── Blocked Query Patterns ─────────────────────────────────────────────────────
# Regex patterns that flag user queries as requesting prohibited content.
# Case-insensitive. Covers English and transliterated Hindi.

_BLOCKED_QUERY_PATTERNS = [
    # Direct buy/sell/hold requests (both word orders)
    r"\b(buy|sell|hold|kharidna|kharido|becho|bechu)\b.{0,30}\b(stocks?|shares?|equity|script|scrip)\b",
    r"\b(stocks?|shares?|equity)\b.{0,30}\b(buy|sell|hold|kharidna|kharido|becho|bechu)\b",
    # Stock tips phrase
    r"\bstock\s+tip\b",
    # Price targets / predictions
    r"\b(price target|target price|target |\bTP\b|fair value|will.*reach|kitna jayega)\b",
    # Guaranteed returns
    r"\bguaranteed?\b.{0,20}\b(return|profit|income|munafa|faida)\b",
    r"\b\d+\s*%\s*(guaranteed?|assured?|fixed|pakka|confirm)\b",
    # Stock tips requests
    r"\b(tip|tips|recommend|suggest)\b.{0,20}\b(stock|share|mutual fund|mf)\b",
    r"\bkonsa (stock|share|fund)\b",
    r"\bkaunsa (stock|share|fund)\b",
    # Pump and dump / specific stock names with action verbs
    r"\b(invest|lagao|lagana) .{0,20}\b(reliance|tata|infosys|hdfc|sbi|wipro|adani)\b",
    # "Will XYZ stock go up?"
    r"\b(stock|share).{0,30}(upar jayega|neeche jayega|badhega|girega|go up|go down|rise|fall)\b",
    # Broker promotions
    r"\b(zerodha|groww|upstox|angel broking|sharekhan)\b.{0,30}\b(good|best|use|open|account)\b",
]

_COMPILED_QUERY_PATTERNS = [
    re.compile(p, re.IGNORECASE | re.DOTALL) for p in _BLOCKED_QUERY_PATTERNS
]

# ── Blocked Answer Patterns ────────────────────────────────────────────────────
# Patterns that flag LLM output as potentially violating safety rules.

_BLOCKED_ANSWER_PATTERNS = [
    r"\b(buy|sell|hold)\b.{0,30}\b(stocks?|shares?|equity)\b",
    r"\bprice target\b",
    r"\bI recommend (buying|selling|investing in)\b",
    r"\byou should (buy|sell|invest in|purchase)\b",
    r"\bguaranteed?.{0,15}(returns?|profits?)\b",
    r"\b\d+%\s*(guaranteed?|assured?)\b",
]

_COMPILED_ANSWER_PATTERNS = [
    re.compile(p, re.IGNORECASE | re.DOTALL) for p in _BLOCKED_ANSWER_PATTERNS
]


def check_query(query: str) -> tuple[bool, str]:
    """
    Layer 1: Check if a user query should be blocked before reaching the LLM.

    Returns:
        (is_blocked: bool, violation_type: str)
        violation_type is one of: "stock_tip", "price_prediction", "guaranteed_return",
        "broker_promotion", or "" if not blocked.
    """
    for pattern in _COMPILED_QUERY_PATTERNS:
        if pattern.search(query):
            logger.warning(f"Query blocked by safety filter: '{query[:60]}...'")
            return True, "investment_advice"
    return False, ""


def check_answer(answer: str) -> tuple[bool, str]:
    """
    Layer 2: Check if a generated answer contains prohibited content.

    Returns:
        (is_violating: bool, matched_snippet: str)
    """
    for pattern in _COMPILED_ANSWER_PATTERNS:
        match = pattern.search(answer)
        if match:
            logger.warning(f"Answer failed safety check at: '{match.group()}'")
            return True, match.group()
    return False, ""


def get_refusal_message(lang_code: str = "hi-IN") -> str:
    """
    Return a polite, educational refusal message in the appropriate language.
    The refusal always redirects to SEBI-registered advisors.

    Args:
        lang_code: BCP-47 language code — "hi-IN" for Hindi, "en-IN" for English.

    Returns:
        Refusal message string.
    """
    if lang_code.startswith("hi"):
        return (
            "🙏 **मैं स्टॉक टिप्स, खरीद/बिक्री की सलाह, या गारंटीड रिटर्न के वादे नहीं दे सकता।**\n\n"
            "SEBI के नियमों के अनुसार:\n"
            "- हर निवेश में जोखिम होता है\n"
            "- गारंटीड रिटर्न का वादा करना **धोखाधड़ी की निशानी** है\n"
            "- केवल SEBI-पंजीकृत सलाहकार ही व्यक्तिगत निवेश सलाह दे सकते हैं\n\n"
            "📞 SEBI निवेशक हेल्पलाइन: **1800-266-7575** (निःशुल्क)\n"
            "🌐 SEBI-पंजीकृत सलाहकार खोजें: **sebi.gov.in/sebiweb/other/OtherAction.do?doRecognisedFpi=yes&intmId=13**\n\n"
            "मैं आपको म्यूचुअल फंड के प्रकार, शेयर बाजार की बुनियादी बातें, "
            "या धोखाधड़ी से बचने के तरीके बता सकता हूं। क्या आप यह जानना चाहेंगे?"
        )
    else:
        return (
            "🙏 **I cannot provide stock tips, buy/sell recommendations, or guaranteed return promises.**\n\n"
            "Per SEBI regulations:\n"
            "- All investments carry risk\n"
            "- Promises of 'guaranteed returns' are a **major red flag for fraud**\n"
            "- Only SEBI-registered investment advisors can provide personalised advice\n\n"
            "📞 SEBI Investor Helpline: **1800-266-7575** (toll-free)\n"
            "🌐 Find a SEBI-registered advisor at: **sebi.gov.in**\n\n"
            "I can help you understand types of mutual funds, stock market basics, "
            "or how to protect yourself from investment fraud. Would you like that?"
        )


def get_fraud_alert_message(lang_code: str = "hi-IN") -> str:
    """
    Return an alert message for queries that appear to be describing a fraud scenario.
    """
    if lang_code.startswith("hi"):
        return (
            "🚨 **यह एक संभावित निवेश धोखाधड़ी हो सकती है!**\n\n"
            "सावधान रहें अगर:\n"
            "- कोई 'गारंटीड' या 'पक्का' रिटर्न का वादा करे\n"
            "- WhatsApp/Telegram ग्रुप पर 'VIP टिप्स' मिलें\n"
            "- पैसे जल्दी लगाने का दबाव बनाया जाए\n\n"
            "📢 साइबर क्राइम शिकायत दर्ज करें: **cybercrime.gov.in**\n"
            "📞 SEBI हेल्पलाइन: **1800-266-7575**"
        )
    else:
        return (
            "🚨 **This may be an investment fraud attempt!**\n\n"
            "Warning signs:\n"
            "- Promises of 'guaranteed' or 'assured' returns\n"
            "- 'VIP tips' shared via WhatsApp/Telegram groups\n"
            "- Pressure to invest quickly without time to verify\n\n"
            "📢 Report cybercrime: **cybercrime.gov.in**\n"
            "📞 SEBI helpline: **1800-266-7575**"
        )
