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
# Matches actual advice or promises, while allowing educational fraud warnings
# (e.g. "beware of guaranteed returns", "no guaranteed returns in mutual funds").

_BLOCKED_ANSWER_PATTERNS = [
    r"\b(buy|sell|hold)\b.{0,30}\b(stocks?|shares?|equity)\b",
    r"\bprice target\b",
    r"\bI recommend (buying|selling|investing in)\b",
    r"\byou should (buy|sell|invest in|purchase)\b",
    # Matches promises like "offers guaranteed returns" or "provides guaranteed returns", but not "claims of guaranteed returns" or "beware of guaranteed returns"
    r"(?<!no\s)(?<!never\s)(?<!beware of\s)(?<!fake\s)(?<!claims of\s)\b(offers?|provides?|gives?|ensures?|with)\s+guaranteed?\s+(returns?|profits?)\b",
    r"\b\d+%\s*(guaranteed?|assured?)\s*(returns?|profits?)\s*(?:is|are|will be|provided|offered)\b",
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
    if lang_code.startswith("en"):
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

    messages = {
        "mr": (
            "🙏 मी शेअर टिप्स, खरेदी-विक्रीचा सल्ला किंवा हमी परताव्याचे आश्वासन देऊ शकत नाही.\n\n"
            "- प्रत्येक गुंतवणुकीत जोखीम असते.\n"
            "- हमी परताव्याचे आश्वासन हा फसवणुकीचा इशारा असू शकतो.\n"
            "- वैयक्तिक सल्ल्यासाठी SEBI-नोंदणीकृत गुंतवणूक सल्लागाराशी संपर्क साधा.\n\n"
            "📞 SEBI हेल्पलाइन: **1800-266-7575**"
        ),
        "pa": (
            "🙏 ਮੈਂ ਸ਼ੇਅਰ ਟਿੱਪਸ, ਖਰੀਦਣ-ਵੇਚਣ ਦੀ ਸਲਾਹ ਜਾਂ ਪੱਕੇ ਮੁਨਾਫ਼ੇ ਦਾ ਵਾਅਦਾ ਨਹੀਂ ਕਰ ਸਕਦਾ।\n\n"
            "- ਹਰ ਨਿਵੇਸ਼ ਵਿੱਚ ਜੋਖਮ ਹੁੰਦਾ ਹੈ।\n"
            "- ਪੱਕੇ ਮੁਨਾਫ਼ੇ ਦਾ ਵਾਅਦਾ ਧੋਖਾਧੜੀ ਦੀ ਨਿਸ਼ਾਨੀ ਹੋ ਸਕਦਾ ਹੈ।\n"
            "- ਨਿੱਜੀ ਸਲਾਹ ਲਈ SEBI-ਰਜਿਸਟਰਡ ਨਿਵੇਸ਼ ਸਲਾਹਕਾਰ ਨਾਲ ਸੰਪਰਕ ਕਰੋ।\n\n"
            "📞 SEBI ਹੈਲਪਲਾਈਨ: **1800-266-7575**"
        ),
        "gu": (
            "🙏 હું શેર ટિપ્સ, ખરીદ-વેચાણની સલાહ અથવા નિશ્ચિત વળતરની ખાતરી આપી શકતો નથી.\n\n"
            "- દરેક રોકાણમાં જોખમ હોય છે.\n"
            "- નિશ્ચિત વળતરની ખાતરી છેતરપિંડીનો સંકેત હોઈ શકે છે.\n"
            "- વ્યક્તિગત સલાહ માટે SEBI-નોંધાયેલ રોકાણ સલાહકારનો સંપર્ક કરો.\n\n"
            "📞 SEBI હેલ્પલાઇન: **1800-266-7575**"
        ),
        "kn": (
            "🙏 ನಾನು ಷೇರು ಸಲಹೆಗಳು, ಖರೀದಿ-ಮಾರಾಟದ ಸಲಹೆ ಅಥವಾ ಖಚಿತ ಆದಾಯದ ಭರವಸೆ ನೀಡಲು ಸಾಧ್ಯವಿಲ್ಲ.\n\n"
            "- ಪ್ರತಿಯೊಂದು ಹೂಡಿಕೆಯಲ್ಲೂ ಅಪಾಯವಿದೆ.\n"
            "- ಖಚಿತ ಆದಾಯದ ಭರವಸೆ ವಂಚನೆಯ ಸೂಚನೆಯಾಗಿರಬಹುದು.\n"
            "- ವೈಯಕ್ತಿಕ ಸಲಹೆಗಾಗಿ SEBI-ನೋಂದಾಯಿತ ಹೂಡಿಕೆ ಸಲಹೆಗಾರರನ್ನು ಸಂಪರ್ಕಿಸಿ.\n\n"
            "📞 SEBI ಸಹಾಯವಾಣಿ: **1800-266-7575**"
        ),
        "ta": (
            "🙏 பங்கு குறிப்புகள், வாங்க/விற்கும் ஆலோசனை அல்லது உறுதியான வருமான வாக்குறுதியை என்னால் வழங்க முடியாது.\n\n"
            "- ஒவ்வொரு முதலீட்டிலும் ஆபத்து உண்டு.\n"
            "- உறுதியான வருமான வாக்குறுதி மோசடியின் அறிகுறியாக இருக்கலாம்.\n"
            "- தனிப்பட்ட ஆலோசனைக்கு SEBI-யில் பதிவுசெய்த முதலீட்டு ஆலோசகரை அணுகவும்.\n\n"
            "📞 SEBI உதவி எண்: **1800-266-7575**"
        ),
        "bn": (
            "🙏 আমি শেয়ার টিপস, কেনা-বেচার পরামর্শ বা নিশ্চিত আয়ের প্রতিশ্রুতি দিতে পারি না।\n\n"
            "- প্রতিটি বিনিয়োগেই ঝুঁকি থাকে।\n"
            "- নিশ্চিত আয়ের প্রতিশ্রুতি প্রতারণার লক্ষণ হতে পারে।\n"
            "- ব্যক্তিগত পরামর্শের জন্য SEBI-নিবন্ধিত বিনিয়োগ উপদেষ্টার সঙ্গে যোগাযোগ করুন।\n\n"
            "📞 SEBI হেল্পলাইন: **1800-266-7575**"
        ),
        "te": (
            "🙏 నేను షేర్ చిట్కాలు, కొనుగోలు/అమ్మకం సలహా లేదా హామీ ఇచ్చిన రాబడి వాగ్దానం చేయలేను.\n\n"
            "- ప్రతి పెట్టుబడిలోనూ ప్రమాదం ఉంటుంది.\n"
            "- హామీ ఇచ్చిన రాబడి వాగ్దానం మోసానికి సంకేతం కావచ్చు.\n"
            "- వ్యక్తిగత సలహా కోసం SEBI-నమోదిత పెట్టుబడి సలహాదారుని సంప్రదించండి.\n\n"
            "📞 SEBI హెల్ప్‌లైన్: **1800-266-7575**"
        ),
        "ml": (
            "🙏 ഓഹരി നിർദേശങ്ങളോ വാങ്ങൽ/വിൽപ്പന ഉപദേശമോ ഉറപ്പായ വരുമാന വാഗ്ദാനമോ നൽകാൻ എനിക്ക് കഴിയില്ല.\n\n"
            "- എല്ലാ നിക്ഷേപങ്ങളിലും അപകടസാധ്യതയുണ്ട്.\n"
            "- ഉറപ്പായ വരുമാന വാഗ്ദാനം തട്ടിപ്പിന്റെ സൂചനയായിരിക്കാം.\n"
            "- വ്യക്തിഗത ഉപദേശത്തിന് SEBI-യിൽ രജിസ്റ്റർ ചെയ്ത നിക്ഷേപ ഉപദേഷ്ടാവിനെ സമീപിക്കുക.\n\n"
            "📞 SEBI ഹെൽപ്‌ലൈൻ: **1800-266-7575**"
        ),
        "or": (
            "🙏 ମୁଁ ଷ୍ଟକ୍ ଟିପ୍ସ, କିଣା-ବିକା ପରାମର୍ଶ କିମ୍ବା ନିଶ୍ଚିତ ଲାଭର ପ୍ରତିଶ୍ରୁତି ଦେଇପାରିବି ନାହିଁ।\n\n"
            "- ପ୍ରତ୍ୟେକ ନିବେଶରେ ବିପଦ ରହିଛି।\n"
            "- ନିଶ୍ଚିତ ଲାଭର ପ୍ରତିଶ୍ରୁତି ଠକେଇର ସଙ୍କେତ ହୋଇପାରେ।\n"
            "- ବ୍ୟକ୍ତିଗତ ପରାମର୍ଶ ପାଇଁ SEBI-ପଞ୍ଜୀକୃତ ନିବେଶ ପରାମର୍ଶଦାତାଙ୍କୁ ଯୋଗାଯୋଗ କରନ୍ତୁ।\n\n"
            "📞 SEBI ହେଲ୍ପଲାଇନ୍: **1800-266-7575**"
        ),
    }
    return messages.get(lang_code.split("-")[0], get_refusal_message("en-IN"))


def get_no_context_message(lang_code: str = "en-IN") -> str:
    """Return the localized message shown when retrieval finds no source material."""
    messages = {
        "hi": "मुझे इस विषय पर SEBI के दस्तावेज़ों में जानकारी नहीं मिली। कृपया sebi.gov.in पर जाएं।",
        "en": "I couldn't find relevant information in the SEBI knowledge base. Please visit sebi.gov.in.",
        "mr": "या विषयावर SEBI च्या माहितीस्रोतांमध्ये माहिती मिळाली नाही. कृपया sebi.gov.in ला भेट द्या.",
        "pa": "SEBI ਦੀ ਜਾਣਕਾਰੀ ਵਿੱਚ ਇਸ ਵਿਸ਼ੇ ਬਾਰੇ ਕੁਝ ਨਹੀਂ ਮਿਲਿਆ। ਕਿਰਪਾ ਕਰਕੇ sebi.gov.in ਵੇਖੋ।",
        "gu": "SEBIની માહિતીમાં આ વિષય વિશે જાણકારી મળી નથી. કૃપા કરીને sebi.gov.in જુઓ.",
        "kn": "SEBI ಮಾಹಿತಿಯಲ್ಲಿ ಈ ವಿಷಯದ ಬಗ್ಗೆ ಮಾಹಿತಿ ಸಿಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು sebi.gov.in ಗೆ ಭೇಟಿ ನೀಡಿ.",
        "ta": "SEBI தகவல் ஆதாரங்களில் இந்தத் தலைப்பைப் பற்றிய தகவல் கிடைக்கவில்லை. sebi.gov.in-ஐப் பார்க்கவும்.",
        "bn": "SEBI-এর তথ্যভান্ডারে এই বিষয়ের তথ্য পাওয়া যায়নি। অনুগ্রহ করে sebi.gov.in দেখুন।",
        "te": "SEBI సమాచారంలో ఈ విషయం గురించి సమాచారం కనుగొనలేకపోయాను. దయచేసి sebi.gov.in చూడండి.",
        "ml": "SEBI വിവരശേഖരത്തിൽ ഈ വിഷയത്തെക്കുറിച്ചുള്ള വിവരം കണ്ടെത്താനായില്ല. sebi.gov.in സന്ദർശിക്കുക.",
        "or": "SEBI ତଥ୍ୟରେ ଏହି ବିଷୟ ବିଷୟରେ ସୂଚନା ମିଳିଲା ନାହିଁ। ଦୟାକରି sebi.gov.in ଦେଖନ୍ତୁ।",
    }
    return messages.get(lang_code.split("-")[0], messages["en"])


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
