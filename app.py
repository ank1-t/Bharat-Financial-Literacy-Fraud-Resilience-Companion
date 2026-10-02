"""
app.py
───────
Main Streamlit entry point for the
Bharat Financial Literacy & Fraud Resilience Companion.

Run with:
    streamlit run app.py

Requires:
    - GEMINI_API_KEY in .env
    - SEBI PDFs in data/pdfs/ (see data/pdfs/README.txt)
    - Chrome/Edge browser for voice input
"""

import logging
import streamlit as st

# ── Page config MUST be the first Streamlit call ──────────────────────────────
st.set_page_config(
    page_title="Bharat Financial Literacy Companion",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help":    "https://www.sebi.gov.in",
        "Report a bug": None,
        "About": "Bharat Financial Literacy & Fraud Resilience Companion — Built for IIT BHU Sangyan & IIT Mandi Hackathons",
    }
)

# ── Imports (after set_page_config) ───────────────────────────────────────────
from config.settings import (
    GEMINI_API_KEY, APP_NAME, APP_TAGLINE,
    LANGUAGE_OPTIONS, DEFAULT_LANGUAGE_LABEL, DEFAULT_LANGUAGE_CODE,
)
from ingestion.pdf_loader import load_all_pdfs
from ingestion.youtube_loader import load_all_youtube
from rag.embedder import embed_texts
from rag.vector_store import upsert_chunks, get_collection_count
from rag.retriever import retrieve, format_context_block
from rag.generator import generate_answer
from guardrails.safety_filter import check_query, check_answer, get_refusal_message, get_fraud_alert_message
from quiz.quiz_engine import QuizSession
from voice.speech_component import render_voice_input, render_tts_player
from ui.styles import get_global_css
from ui.components import (
    render_hero,
    render_answer_card,
    render_kb_status,
    render_source_pills,
    render_quiz_progress,
    render_score_badge,
    render_safety_footer,
    render_example_questions,
)

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

# ── Inject Global CSS ──────────────────────────────────────────────────────────
st.markdown(get_global_css(), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Knowledge Base Initialization (cached — runs once per server session)
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner=False)
def initialize_knowledge_base():
    """
    Load PDFs + YouTube transcripts, embed them, and upsert into ChromaDB.
    Cached by Streamlit — runs only once when the app first starts.

    Returns:
        Total number of chunks indexed.
    """
    logger.info("Initializing knowledge base...")

    # 1. Load all document chunks
    pdf_chunks = load_all_pdfs()
    yt_chunks  = load_all_youtube()
    all_chunks = pdf_chunks + yt_chunks

    if not all_chunks:
        logger.warning("No chunks loaded! Check data/pdfs/ directory and YouTube config.")
        return 0

    # 2. Embed all chunks
    texts = [c["text"] for c in all_chunks]
    logger.info(f"Embedding {len(texts)} chunks...")
    embeddings = embed_texts(texts, task_type="retrieval_document")

    # 3. Upsert into ChromaDB
    upsert_chunks(all_chunks, embeddings)
    total = get_collection_count()
    logger.info(f"Knowledge base ready: {total} chunks indexed")
    return total


# ══════════════════════════════════════════════════════════════════════════════
# Session State Initialization
# ══════════════════════════════════════════════════════════════════════════════

def init_session():
    """Initialize all session state variables on first run."""
    defaults = {
        "lang_label":       DEFAULT_LANGUAGE_LABEL,
        "lang_code":        DEFAULT_LANGUAGE_CODE,
        "chat_history":     [],   # list of {"role": "user"/"assistant", "content": str}
        "last_results":     [],   # last RAG retrieval results for source display
        "last_answer":      "",   # last generated answer for TTS
        "quiz_session":     QuizSession(),
        "quiz_active":      False,
        "quiz_question":    None,
        "quiz_answered":    False,
        "quiz_result":      None,
        "pending_query":    None,  # set by example question buttons
        "kb_chunk_count":   0,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_session()


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### ⚙️ Settings")

    # Language selector
    selected_lang = st.selectbox(
        "🌐 Language / भाषा",
        options=list(LANGUAGE_OPTIONS.keys()),
        index=list(LANGUAGE_OPTIONS.keys()).index(st.session_state["lang_label"]),
        key="lang_selector",
    )
    if selected_lang != st.session_state["lang_label"]:
        st.session_state["lang_label"] = selected_lang
        st.session_state["lang_code"]  = LANGUAGE_OPTIONS[selected_lang]
        st.rerun()

    lang_code = st.session_state["lang_code"]
    is_hindi  = lang_code.startswith("hi")

    st.divider()

    # Knowledge base status
    st.markdown("### 📚 Knowledge Base")
    render_kb_status(st.session_state.get("kb_chunk_count", 0))

    if not GEMINI_API_KEY:
        st.error("⚠️ GEMINI_API_KEY not found!\nAdd it to your `.env` file.")
    else:
        st.success("✅ Gemini API key loaded")

    st.divider()

    # About section
    st.markdown("### ℹ️ About")
    st.markdown("""
    Built for:
    - 🏆 IIT BHU Sangyan (Track C + D)
    - 🏆 IIT Mandi Multimodal AI (Track D)

    **Stack**: Streamlit · Gemini 1.5 Flash · ChromaDB · Web Speech API

    **Sources**: SEBI PDFs · YouTube Transcripts

    ---
    📞 SEBI: **1800-266-7575**
    🌐 [cybercrime.gov.in](https://cybercrime.gov.in)
    """)

    st.divider()

    # Clear chat button
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state["chat_history"] = []
        st.session_state["last_results"] = []
        st.session_state["last_answer"]  = ""
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# Initialize Knowledge Base (shows spinner on first load)
# ══════════════════════════════════════════════════════════════════════════════

lang_code = st.session_state["lang_code"]
is_hindi  = lang_code.startswith("hi")

with st.spinner("📚 Loading SEBI knowledge base... (first load only, ~30 seconds)"):
    chunk_count = initialize_knowledge_base()
    st.session_state["kb_chunk_count"] = chunk_count


# ══════════════════════════════════════════════════════════════════════════════
# Main Layout
# ══════════════════════════════════════════════════════════════════════════════

# Hero
render_hero()

# Two-column layout: main content | quiz panel
col_main, col_quiz = st.columns([3, 2], gap="large")


# ─── LEFT COLUMN: Q&A ──────────────────────────────────────────────────────
with col_main:

    # ── Voice / Text Input ──────────────────────────────────────────────────
    st.markdown('<div class="card-header">🎤 Ask Your Question</div>', unsafe_allow_html=True)

    # Voice input component
    voice_result = render_voice_input(language_code=lang_code, key="main_voice")

    # Text fallback
    placeholder = (
        "उदाहरण: म्यूचुअल फंड क्या होता है?" if is_hindi
        else "e.g. What is a mutual fund? Is this WhatsApp group safe?"
    )

    # Pre-fill from voice result or example button
    pre_fill = ""
    if voice_result and isinstance(voice_result, str):
        pre_fill = voice_result
    elif st.session_state.get("pending_query"):
        pre_fill = st.session_state.pop("pending_query")

    user_query = st.text_input(
        "✏️ Or type your question:" if not is_hindi else "✏️ या टाइप करें:",
        value=pre_fill,
        placeholder=placeholder,
        key="text_input",
        label_visibility="visible",
    )

    ask_label = "पूछें 🚀" if is_hindi else "Ask 🚀"
    ask_clicked = st.button(ask_label, use_container_width=True, type="primary")

    # ── Example Questions ───────────────────────────────────────────────────
    render_example_questions(lang_code)

    # ── Process Query ───────────────────────────────────────────────────────
    if ask_clicked and user_query.strip():
        query = user_query.strip()

        with st.spinner("🔍 Searching knowledge base..." if not is_hindi else "🔍 खोज रहा हूं..."):

            # Layer 1 safety check
            is_blocked, violation_type = check_query(query)

            if is_blocked:
                refusal = get_refusal_message(lang_code)
                st.session_state["chat_history"].append({"role": "user", "content": query})
                st.session_state["chat_history"].append({"role": "assistant", "content": refusal, "is_refusal": True})
                st.session_state["last_answer"] = refusal

            else:
                # Retrieve relevant chunks
                results = retrieve(query, top_k=5)
                st.session_state["last_results"] = results

                if not results:
                    no_ctx = (
                        "मुझे इस विषय पर SEBI के दस्तावेज़ों में जानकारी नहीं मिली। कृपया sebi.gov.in पर जाएं।"
                        if is_hindi else
                        "I couldn't find relevant information in the SEBI knowledge base. Please visit sebi.gov.in."
                    )
                    answer = no_ctx
                else:
                    context = format_context_block(results)
                    answer = generate_answer(query, context)

                    # Layer 2: post-generation answer check
                    is_violating, snippet = check_answer(answer)
                    if is_violating:
                        logger.warning(f"Answer post-filter triggered for snippet: {snippet}")
                        answer = get_refusal_message(lang_code)
                        st.session_state["chat_history"].append({"role": "user", "content": query})
                        st.session_state["chat_history"].append({"role": "assistant", "content": answer, "is_refusal": True})
                        st.session_state["last_answer"] = answer
                    else:
                        st.session_state["chat_history"].append({"role": "user", "content": query})
                        st.session_state["chat_history"].append({"role": "assistant", "content": answer, "is_refusal": False})
                        st.session_state["last_answer"] = answer

        st.rerun()

    # ── Chat History ────────────────────────────────────────────────────────
    if st.session_state["chat_history"]:
        st.markdown("---")
        st.markdown("### 💬 Conversation" if not is_hindi else "### 💬 बातचीत")

        for i, msg in enumerate(reversed(st.session_state["chat_history"])):
            if msg["role"] == "user":
                st.markdown(f"""
                <div class="card" style="border-left:3px solid #58A6FF; margin-bottom:8px;">
                  <strong style="color:#58A6FF;">👤 {'आप' if is_hindi else 'You'}:</strong><br>
                  {msg['content']}
                </div>
                """, unsafe_allow_html=True)
            else:
                is_refusal = msg.get("is_refusal", False)
                render_answer_card(msg["content"], is_refusal=is_refusal)

                # TTS for the most recent answer only
                if i == 0 and msg["content"] == st.session_state.get("last_answer", ""):
                    render_tts_player(msg["content"], language_code=lang_code)

        # Show source pills for last retrieval
        if st.session_state["last_results"]:
            render_source_pills(st.session_state["last_results"])


# ─── RIGHT COLUMN: Adaptive Quiz ───────────────────────────────────────────
with col_quiz:
    quiz_title = "🧠 धोखाधड़ी जागरूकता क्विज़" if is_hindi else "🧠 Fraud Awareness Quiz"
    st.markdown(f'<div class="quiz-card"><div class="card-header">{quiz_title}</div>', unsafe_allow_html=True)

    quiz_subtitle = (
        "क्या आप निवेश धोखाधड़ी पहचान सकते हैं? परीक्षण करें!"
        if is_hindi else
        "Can you spot investment fraud? Test your skills!"
    )
    st.markdown(f"<p style='font-size:13px;color:#8B949E;'>{quiz_subtitle}</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    quiz: QuizSession = st.session_state["quiz_session"]

    # Start / Restart button
    start_label = (
        "🔄 नया क्विज़ शुरू करें" if (is_hindi and quiz.is_complete) else
        "▶️ क्विज़ शुरू करें" if is_hindi else
        "🔄 Restart Quiz" if quiz.is_complete else "▶️ Start Quiz"
    )

    if not st.session_state["quiz_active"] or quiz.is_complete:
        if st.button(start_label, key="start_quiz", use_container_width=True):
            quiz.reset()
            st.session_state["quiz_active"] = True
            st.session_state["quiz_question"] = quiz.get_next_question()
            st.session_state["quiz_answered"] = False
            st.session_state["quiz_result"] = None
            st.rerun()

    # Active quiz
    if st.session_state["quiz_active"] and not quiz.is_complete:
        question = st.session_state.get("quiz_question")

        if question:
            answered, total = quiz.progress
            render_quiz_progress(answered, total, quiz.score)

            # Difficulty badge
            diff_colors = {1: "#3FB950", 2: "#D29922", 3: "#F85149"}
            diff_labels_en = {1: "Beginner", 2: "Intermediate", 3: "Advanced"}
            diff_labels_hi = {1: "शुरुआती", 2: "मध्यम", 3: "उन्नत"}
            diff = question["difficulty"]
            diff_label = diff_labels_hi[diff] if is_hindi else diff_labels_en[diff]
            st.markdown(
                f'<span style="font-size:11px;font-weight:600;color:{diff_colors[diff]};'
                f'border:1px solid {diff_colors[diff]};padding:2px 8px;border-radius:12px;">'
                f'Level {diff}: {diff_label}</span>',
                unsafe_allow_html=True
            )
            st.markdown("<br>", unsafe_allow_html=True)

            # Question text
            q_text = question["text_hi"] if is_hindi else question["text_en"]
            st.markdown(f'<div class="quiz-question">{q_text}</div>', unsafe_allow_html=True)

            # Options
            options = question["options_hi"] if is_hindi else question["options_en"]

            if not st.session_state["quiz_answered"]:
                for opt_idx, opt_text in enumerate(options):
                    if st.button(opt_text, key=f"opt_{question['id']}_{opt_idx}", use_container_width=True):
                        result = quiz.submit_answer(question, opt_idx)
                        st.session_state["quiz_answered"] = True
                        st.session_state["_last_quiz_result"] = result
                        st.rerun()
            else:
                # Show result with explanation
                res = st.session_state.get("_last_quiz_result", {})
                for opt_idx, opt_text in enumerate(options):
                    if opt_idx == res.get("correct_index"):
                        st.markdown(
                            f'<div style="padding:10px;border:2px solid #3FB950;border-radius:8px;'
                            f'background:rgba(63,185,80,0.1);color:#3FB950;margin:4px 0;">'
                            f'✅ {opt_text}</div>',
                            unsafe_allow_html=True
                        )
                    elif opt_idx == st.session_state.get("_chosen_idx"):
                        st.markdown(
                            f'<div style="padding:10px;border:2px solid #F85149;border-radius:8px;'
                            f'background:rgba(248,81,73,0.1);color:#F85149;margin:4px 0;">'
                            f'❌ {opt_text}</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            f'<div style="padding:10px;border:1px solid #30363D;border-radius:8px;'
                            f'color:#8B949E;margin:4px 0;">{opt_text}</div>',
                            unsafe_allow_html=True
                        )

                # Explanation
                is_correct = res.get("is_correct", False)
                result_icon = "✅ सही!" if (is_correct and is_hindi) else "✅ Correct!" if is_correct else ("❌ गलत" if is_hindi else "❌ Wrong")
                explanation = res.get("explanation_hi" if is_hindi else "explanation_en", "")
                source = res.get("source", "")

                st.markdown(f"""
                <div style="background:{'rgba(63,185,80,0.08)' if is_correct else 'rgba(248,81,73,0.08)'};
                  border:1px solid {'#3FB950' if is_correct else '#F85149'};
                  border-radius:8px;padding:16px;margin-top:12px;">
                  <strong style="color:{'#3FB950' if is_correct else '#F85149'}">{result_icon}</strong><br>
                  <span style="font-size:13px;color:#E6EDF3;">{explanation}</span><br>
                  <span style="font-size:11px;color:#58A6FF;margin-top:6px;display:block;">{source}</span>
                </div>
                """, unsafe_allow_html=True)

                next_label = "अगला सवाल →" if is_hindi else "Next Question →"
                if st.button(next_label, key="quiz_next", use_container_width=True, type="primary"):
                    if quiz.is_complete:
                        st.session_state["quiz_result"] = quiz.get_final_result(lang_code)
                    else:
                        st.session_state["quiz_question"] = quiz.get_next_question()
                        st.session_state["quiz_answered"] = False
                    st.rerun()

    # Quiz complete — show score badge
    if quiz.is_complete and st.session_state.get("quiz_result") is None:
        st.session_state["quiz_result"] = quiz.get_final_result(lang_code)

    if quiz.is_complete and st.session_state.get("quiz_result"):
        render_score_badge(st.session_state["quiz_result"])

        missed = st.session_state["quiz_result"].get("fraud_types_missed", [])
        if missed:
            learn_label = "📚 इन विषयों पर और जानें:" if is_hindi else "📚 Learn more about:"
            st.markdown(f"**{learn_label}**")
            for ft in set(missed):
                ft_readable = ft.replace("_", " ").title()
                st.markdown(f"- {ft_readable}")


# ── Safety Footer ───────────────────────────────────────────────────────────
render_safety_footer()
