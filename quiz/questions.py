"""
quiz/questions.py
──────────────────
Question bank for the adaptive fraud-awareness quiz.
Three difficulty levels — the engine escalates based on correct answers.

Difficulty levels:
  1 = Beginner   — Obvious scam recognition
  2 = Intermediate — Subtle red flags, social engineering
  3 = Advanced    — Regulatory knowledge, legal recourse

Each question dict:
  {
    "id":          str,         # Unique question ID
    "difficulty":  int,         # 1, 2, or 3
    "text_en":     str,         # Question in English
    "text_hi":     str,         # Question in Hindi (Devanagari)
    "options_en":  list[str],   # 4 answer options in English
    "options_hi":  list[str],   # 4 answer options in Hindi
    "correct":     int,         # 0-indexed correct option
    "explanation_en": str,      # Why this is the answer (English)
    "explanation_hi": str,      # Why this is the answer (Hindi)
    "source":      str,         # Citation tag for the explanation
    "fraud_type":  str,         # Category tag for analytics
  }
"""

QUESTIONS: list[dict] = [

    # ── DIFFICULTY 1: Beginner ────────────────────────────────────────────────

    {
        "id": "d1_q1",
        "difficulty": 1,
        "fraud_type": "whatsapp_scam",
        "text_en": (
            "You get a WhatsApp message: 'Join our SECRET VIP investment group! "
            "40% GUARANTEED monthly returns! Limited spots — pay ₹5,000 now!' What do you do?"
        ),
        "text_hi": (
            "आपको WhatsApp पर संदेश आया: 'हमारे SECRET VIP निवेश ग्रुप में जुड़ें! "
            "40% गारंटीड मासिक रिटर्न! सीमित सीटें — अभी ₹5,000 जमा करें!' आप क्या करेंगे?"
        ),
        "options_en": [
            "Join immediately — 40% monthly sounds amazing!",
            "Ask the sender for their SEBI registration number first",
            "Report the number and block it — this is a scam",
            "Share it with 5 friends so they can also benefit",
        ],
        "options_hi": [
            "तुरंत जुड़ें — 40% मासिक रिटर्न बहुत अच्छा लगता है!",
            "पहले SEBI पंजीकरण नंबर मांगें",
            "नंबर रिपोर्ट करें और ब्लॉक करें — यह धोखाधड़ी है",
            "5 दोस्तों के साथ शेयर करें ताकि वे भी फायदा उठा सकें",
        ],
        "correct": 2,
        "explanation_en": (
            "This is a classic 'Guaranteed Return' scam. SEBI warns that NO legitimate "
            "investment can guarantee fixed high returns. Monthly returns of 40% would mean "
            "480% annual returns — economically impossible. Always report such messages to "
            "cybercrime.gov.in and block the sender immediately."
        ),
        "explanation_hi": (
            "यह एक क्लासिक 'गारंटीड रिटर्न' धोखाधड़ी है। SEBI के अनुसार कोई भी वैध निवेश "
            "निश्चित उच्च रिटर्न की गारंटी नहीं दे सकता। 40% मासिक रिटर्न का मतलब 480% "
            "वार्षिक रिटर्न होगा — जो आर्थिक रूप से असंभव है। ऐसे संदेशों को cybercrime.gov.in "
            "पर रिपोर्ट करें और नंबर तुरंत ब्लॉक करें।"
        ),
        "source": "[Source: SEBI Fraud Awareness Guide, Pg 8]",
    },

    {
        "id": "d1_q2",
        "difficulty": 1,
        "fraud_type": "guaranteed_return",
        "text_en": (
            "An online advertisement claims: 'Double your money in 3 months with our "
            "AI-powered trading bot! Zero risk, 100% profit guaranteed!' Is this legitimate?"
        ),
        "text_hi": (
            "एक ऑनलाइन विज्ञापन का दावा है: 'हमारे AI ट्रेडिंग बॉट से 3 महीने में "
            "पैसा दोगुना करें! शून्य जोखिम, 100% लाभ की गारंटी!' क्या यह वैध है?"
        ),
        "options_en": [
            "Yes — AI technology can guarantee returns",
            "Maybe — I should invest a small amount to test it",
            "No — 'Zero risk + guaranteed profit' is always a fraud signal",
            "Yes — if the website looks professional, it must be legitimate",
        ],
        "options_hi": [
            "हां — AI तकनीक रिटर्न की गारंटी दे सकती है",
            "शायद — मैं थोड़ी राशि से परीक्षण करूंगा",
            "नहीं — 'शून्य जोखिम + गारंटीड लाभ' हमेशा धोखाधड़ी का संकेत है",
            "हां — अगर वेबसाइट professional दिखती है तो वैध होगी",
        ],
        "correct": 2,
        "explanation_en": (
            "Any investment promising 'zero risk + guaranteed profit' is fraud. "
            "SEBI's core principle: ALL investments carry risk. No algorithm or AI "
            "can eliminate market risk. Professional website design is easy to fake "
            "and not a sign of legitimacy. Report such ads to sebi.gov.in/SCORES."
        ),
        "explanation_hi": (
            "'शून्य जोखिम + गारंटीड लाभ' का वादा करने वाला हर निवेश धोखाधड़ी है। "
            "SEBI का मूल सिद्धांत: सभी निवेश में जोखिम होता है। कोई भी एल्गोरिदम या AI "
            "बाजार के जोखिम को खत्म नहीं कर सकता। ऐसे विज्ञापन sebi.gov.in/SCORES पर रिपोर्ट करें।"
        ),
        "source": "[Source: SEBI Investor Rights Booklet, Pg 3]",
    },

    # ── DIFFICULTY 2: Intermediate ─────────────────────────────────────────────

    {
        "id": "d2_q1",
        "difficulty": 2,
        "fraud_type": "social_engineering",
        "text_en": (
            "A 'SEBI-registered analyst' calls you and says: 'I have insider information "
            "about a stock that will rise 200% next week. I'm sharing this only with "
            "select clients. Act now before it's too late!' What is the RED FLAG here?"
        ),
        "text_hi": (
            "एक 'SEBI-पंजीकृत विश्लेषक' आपको कॉल करता है: 'मेरे पास एक स्टॉक के बारे में "
            "insider जानकारी है जो अगले हफ्ते 200% बढ़ेगा। मैं यह केवल चुनिंदा clients के साथ "
            "share कर रहा हूं। देर होने से पहले अभी निर्णय लें!' यहाँ RED FLAG क्या है?"
        ),
        "options_en": [
            "Nothing — SEBI-registered analysts are always trustworthy",
            "Multiple red flags: insider tips are illegal, urgency is manipulation",
            "The 200% return claim — it should be at least 300% to be believable",
            "He should have texted instead of called",
        ],
        "options_hi": [
            "कुछ नहीं — SEBI-पंजीकृत विश्लेषक हमेशा भरोसेमंद होते हैं",
            "कई red flags: insider tips अवैध हैं, urgency manipulation है",
            "200% रिटर्न का दावा — कम से कम 300% होना चाहिए था",
            "उसे call की बजाय text करना चाहिए था",
        ],
        "correct": 1,
        "explanation_en": (
            "Multiple SEBI violations here: (1) Trading on 'insider information' is a "
            "criminal offence under SEBI (Prohibition of Insider Trading) Regulations. "
            "(2) Artificial urgency ('act now!') is a classic manipulation tactic. "
            "(3) Verify any SEBI registration at sebi.gov.in before trusting anyone. "
            "Real SEBI-registered advisors provide written research reports, not rushed phone calls."
        ),
        "explanation_hi": (
            "यहां कई SEBI उल्लंघन हैं: (1) 'Insider information' पर ट्रेडिंग SEBI (Insider Trading) "
            "Regulations के तहत आपराधिक अपराध है। (2) कृत्रिम urgency ('अभी करें!') एक क्लासिक "
            "manipulation तकनीक है। (3) किसी पर भरोसा करने से पहले sebi.gov.in पर उनकी "
            "SEBI पंजीकरण सत्यापित करें।"
        ),
        "source": "[Source: SEBI Fraud Awareness Guide, Pg 15]",
    },

    {
        "id": "d2_q2",
        "difficulty": 2,
        "fraud_type": "ponzi_scheme",
        "text_en": (
            "Your friend says: 'I joined this investment scheme 2 months ago and already got "
            "₹20,000 back on ₹10,000 invested! The returns come from recruiting new members.' "
            "What type of scheme is this?"
        ),
        "text_hi": (
            "आपका दोस्त कहता है: 'मैं 2 महीने पहले इस निवेश योजना में शामिल हुआ और पहले से "
            "₹10,000 के निवेश पर ₹20,000 वापस मिले! यह रिटर्न नए सदस्यों की भर्ती से आते हैं।' "
            "यह किस प्रकार की योजना है?"
        ),
        "options_en": [
            "A legitimate multi-level marketing opportunity",
            "A Ponzi / pyramid scheme — illegal under SEBI regulations",
            "A standard mutual fund referral programme",
            "A government-backed savings scheme",
        ],
        "options_hi": [
            "एक वैध multi-level marketing अवसर",
            "एक Ponzi/pyramid scheme — SEBI नियमों के तहत अवैध",
            "एक मानक म्यूचुअल फंड referral कार्यक्रम",
            "एक सरकार-समर्थित बचत योजना",
        ],
        "correct": 1,
        "explanation_en": (
            "This is a classic Ponzi/pyramid scheme. Key sign: returns come from recruiting "
            "new members, not from real investments or business profits. "
            "These schemes always collapse when recruitment slows — early joiners "
            "profit at late joiners' expense. Illegal under SEBI CIS Regulations. "
            "Report to SEBI SCORES portal or call 1800-266-7575."
        ),
        "explanation_hi": (
            "यह एक क्लासिक Ponzi/pyramid scheme है। मुख्य संकेत: रिटर्न वास्तविक निवेश से नहीं, "
            "बल्कि नए सदस्यों की भर्ती से आते हैं। ये योजनाएं हमेशा तब ध्वस्त होती हैं जब "
            "भर्ती धीमी होती है। SEBI CIS Regulations के तहत अवैध। "
            "SEBI SCORES पोर्टल पर रिपोर्ट करें या 1800-266-7575 पर कॉल करें।"
        ),
        "source": "[Source: SEBI Fraud Awareness Guide, Pg 22]",
    },

    # ── DIFFICULTY 3: Advanced ─────────────────────────────────────────────────

    {
        "id": "d3_q1",
        "difficulty": 3,
        "fraud_type": "regulatory_knowledge",
        "text_en": (
            "You lost ₹2 lakh to an investment fraud run by someone claiming to be "
            "a SEBI-registered advisor. Which of the following is the CORRECT first step?"
        ),
        "text_hi": (
            "आपने SEBI-पंजीकृत सलाहकार होने का दावा करने वाले किसी व्यक्ति द्वारा चलाई गई "
            "निवेश धोखाधड़ी में ₹2 लाख खो दिए। निम्नलिखित में से कौन सा सही पहला कदम है?"
        ),
        "options_en": [
            "Accept the loss — nothing can be done against financial fraud",
            "File a complaint on SEBI SCORES portal + file police FIR + report to cybercrime.gov.in",
            "Post about it on social media only",
            "Try to get your money back by investing more in the scheme",
        ],
        "options_hi": [
            "नुकसान स्वीकार करें — वित्तीय धोखाधड़ी के खिलाफ कुछ नहीं किया जा सकता",
            "SEBI SCORES पोर्टल पर शिकायत दर्ज करें + पुलिस FIR करें + cybercrime.gov.in पर रिपोर्ट करें",
            "केवल social media पर पोस्ट करें",
            "योजना में अधिक निवेश करके पैसे वापस पाने की कोशिश करें",
        ],
        "correct": 1,
        "explanation_en": (
            "Multi-channel reporting maximises recovery chances: "
            "(1) SEBI SCORES (scores.gov.in) — SEBI's official investor complaint portal, "
            "expects response within 30 days. "
            "(2) Police FIR — creates legal record for prosecution. "
            "(3) cybercrime.gov.in — handles online fraud cases. "
            "(4) Also inform your bank to attempt transaction reversal if recent. "
            "Option D is the Advance Fee Fraud trap — fraudsters often promise 'recovery' for more money."
        ),
        "explanation_hi": (
            "बहु-चैनल रिपोर्टिंग से रिकवरी की संभावना बढ़ती है: "
            "(1) SEBI SCORES (scores.gov.in) — SEBI का आधिकारिक निवेशक शिकायत पोर्टल। "
            "(2) पुलिस FIR — अभियोजन के लिए कानूनी रिकॉर्ड बनाती है। "
            "(3) cybercrime.gov.in — ऑनलाइन धोखाधड़ी के मामले संभालता है। "
            "(4) हाल का लेनदेन हो तो बैंक को भी सूचित करें। "
            "विकल्प D Advance Fee Fraud का जाल है।"
        ),
        "source": "[Source: SEBI Investor Rights Booklet, Pg 18]",
    },

    {
        "id": "d3_q2",
        "difficulty": 3,
        "fraud_type": "regulatory_knowledge",
        "text_en": (
            "Which of these is a REAL, SEBI-regulated investment product that a first-time "
            "investor can safely consider?"
        ),
        "text_hi": (
            "इनमें से कौन सा एक वास्तविक, SEBI-विनियमित निवेश उत्पाद है जिसे एक "
            "पहली बार निवेशक सुरक्षित रूप से विचार कर सकता है?"
        ),
        "options_en": [
            "WhatsApp VIP trading group with 'guaranteed' daily profits",
            "SEBI-registered Mutual Fund via AMFI-registered distributor",
            "Cryptocurrency scheme promising 10x returns in 30 days",
            "Chit fund run by a local agent with verbal agreements only",
        ],
        "options_hi": [
            "'गारंटीड' दैनिक लाभ वाला WhatsApp VIP trading group",
            "AMFI-पंजीकृत वितरक के माध्यम से SEBI-पंजीकृत म्यूचुअल फंड",
            "30 दिनों में 10x रिटर्न का वादा करने वाली cryptocurrency scheme",
            "केवल मौखिक समझौतों के साथ स्थानीय एजेंट द्वारा चलाया गया chit fund",
        ],
        "correct": 1,
        "explanation_en": (
            "SEBI-registered mutual funds are the only fully regulated option here. "
            "Key safeguards: (1) Fund houses are regulated by SEBI. "
            "(2) NAVs published daily. (3) Distributor must be AMFI-registered (ARN number). "
            "(4) Investor can verify everything at mfcentral.com or amfiindia.com. "
            "Start with index funds or large-cap funds for lowest risk. "
            "All investments still carry market risk — returns are not guaranteed."
        ),
        "explanation_hi": (
            "SEBI-पंजीकृत म्यूचुअल फंड ही एकमात्र पूर्णतः विनियमित विकल्प है। "
            "मुख्य सुरक्षा उपाय: (1) फंड हाउस SEBI द्वारा विनियमित। "
            "(2) NAV दैनिक प्रकाशित। (3) वितरक AMFI-पंजीकृत होना चाहिए (ARN नंबर)। "
            "(4) निवेशक mfcentral.com या amfiindia.com पर सब कुछ सत्यापित कर सकता है। "
            "Index funds या large-cap funds से शुरुआत करें। बाजार जोखिम फिर भी रहता है।"
        ),
        "source": "[Source: SEBI Mutual Funds Guide, Pg 5]",
    },
]


def get_questions_by_difficulty(difficulty: int) -> list[dict]:
    """Return all questions of a given difficulty level."""
    return [q for q in QUESTIONS if q["difficulty"] == difficulty]


def get_question_by_id(question_id: str) -> dict | None:
    """Return a question by its unique ID."""
    for q in QUESTIONS:
        if q["id"] == question_id:
            return q
    return None
