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
import html
import streamlit as st

# ── Page config MUST be the first Streamlit call ──────────────────────────────
st.set_page_config(
    page_title="Bharat Financial Literacy Companion",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Imports (after set_page_config) ───────────────────────────────────────────
from config.settings import (
    GEMINI_API_KEY, APP_NAME, APP_TAGLINE,
    LANGUAGE_OPTIONS, DEFAULT_LANGUAGE_LABEL, DEFAULT_LANGUAGE_CODE,
    SEBI_PDF_SOURCES, YOUTUBE_SOURCES,
)
from ingestion.pdf_loader import load_all_pdfs
from ingestion.youtube_loader import load_all_youtube
from rag.embedder import embed_texts
from rag.vector_store import upsert_chunks, get_collection_count, reset_collection
from rag.retriever import retrieve, format_context_block
from rag.generator import generate_answer
from guardrails.safety_filter import (
    check_query,
    check_answer,
    get_no_context_message,
    get_refusal_message,
)
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
from ui.localization import UI_TEXT, get_language_pack, get_translated_history

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

# ── Inject Global CSS ──────────────────────────────────────────────────────────
st.markdown(get_global_css(), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Knowledge Base Initialization (cached — runs once per server session)
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner=False)
def initialize_knowledge_base(source_fingerprint: tuple[str, ...]):
    """
    Load PDFs + YouTube transcripts, embed them, and upsert into ChromaDB.
    Cached by Streamlit for each configured source set.

    Returns:
        Total number of chunks indexed.
    """
    logger.info("Initializing knowledge base for source set %s", source_fingerprint)

    # 1. Load all document chunks
    pdf_chunks = load_all_pdfs()
    yt_chunks  = load_all_youtube()
    all_chunks = pdf_chunks + yt_chunks

    if not all_chunks:
        logger.warning("No chunks loaded! Check data/pdfs/ directory and YouTube config.")
        reset_collection()
        return 0

    # 2. Embed all chunks
    texts = [c["text"] for c in all_chunks]
    logger.info(f"Embedding {len(texts)} chunks...")
    embeddings = embed_texts(texts, task_type="retrieval_document")

    # Rebuild instead of upserting so removed or replaced sources cannot linger.
    reset_collection()

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
    settings_heading = st.empty()

    # Language selector
    selected_lang = st.selectbox(
        f"🌐 {st.session_state['lang_label']}",
        options=list(LANGUAGE_OPTIONS.keys()),
        index=list(LANGUAGE_OPTIONS.keys()).index(st.session_state["lang_label"]),
        key="lang_selector",
    )
    if selected_lang != st.session_state["lang_label"]:
        st.session_state["lang_label"] = selected_lang
        st.session_state["lang_code"]  = LANGUAGE_OPTIONS[selected_lang]
        st.rerun()

    lang_code = st.session_state["lang_code"]

try:
    with st.spinner(UI_TEXT["translation_loading"]):
        language_pack = get_language_pack(lang_code)
except (RuntimeError, ValueError) as error:
    st.error(UI_TEXT["translation_error"])
    st.caption(str(error))
    st.stop()

ui_text = language_pack["ui"]
settings_heading.markdown(f"### ⚙️ {ui_text['settings']}")

# Re-localize existing messages when the language changes.
try:
    with st.spinner(ui_text["translation_loading"]):
        display_history = get_translated_history(
            st.session_state["chat_history"],
            lang_code,
        )
except (RuntimeError, ValueError) as error:
    st.error(ui_text["translation_error"])
    st.caption(str(error))
    st.stop()

with st.sidebar:
    st.divider()

    # Knowledge base status
    st.markdown(f"### 📚 {ui_text['knowledge_base']}")
    render_kb_status(st.session_state.get("kb_chunk_count", 0), ui_text)

    if not GEMINI_API_KEY:
        st.error(ui_text["api_key_missing"])
    else:
        st.success(ui_text["api_key_loaded"])

    st.divider()

    # About section
    st.markdown(f"### ℹ️ {ui_text['about']}")
    st.markdown(f"""

    ---
    📞 {ui_text['sebi_helpline']}: **1800-266-7575**
    🌐 [{ui_text['cybercrime']}](https://cybercrime.gov.in)
    """)

    st.divider()

    # Clear chat button
    if st.button(f"🗑️ {ui_text['clear_chat']}", use_container_width=True):
        st.session_state["chat_history"] = []
        st.session_state["last_results"] = []
        st.session_state["last_answer"]  = ""
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# Initialize Knowledge Base (shows spinner on first load)
# ══════════════════════════════════════════════════════════════════════════════

lang_code = st.session_state["lang_code"]

with st.spinner(f"📚 {ui_text['kb_spinner']}"):
    source_fingerprint = tuple(
        [f"pdf:{source['filename']}:{source['title']}:{source['source_tag']}" for source in SEBI_PDF_SOURCES]
        + [
            f"youtube:{source['video_id']}:{source['title']}:{source['source_tag']}:{','.join(source['languages'])}"
            for source in YOUTUBE_SOURCES
        ]
    )
    chunk_count = initialize_knowledge_base(source_fingerprint)
    st.session_state["kb_chunk_count"] = chunk_count


# ══════════════════════════════════════════════════════════════════════════════
# Main Layout
# ══════════════════════════════════════════════════════════════════════════════

# Hero
render_hero(ui_text)

# Two-column layout: main content | quiz panel
col_main, col_quiz = st.columns([3, 2], gap="large")


# ─── LEFT COLUMN: Q&A ──────────────────────────────────────────────────────
with col_main:

    # ── Voice / Text Input ──────────────────────────────────────────────────
    st.markdown(f'<div class="card-header">🎤 {ui_text["ask_question"]}</div>', unsafe_allow_html=True)

    # Voice input component
    voice_result = render_voice_input(
        language_code=lang_code,
        key="main_voice",
        translations=ui_text,
    )

    # Text fallback
    placeholder = ui_text["question_placeholder"]

    # Clear input on successful submit from previous run
    if st.session_state.pop("clear_input", False):
        st.session_state["text_input"] = ""

    # Handle voice input pre-fill
    if voice_result and isinstance(voice_result, str) and voice_result.strip():
        if st.session_state.get("text_input") != voice_result.strip():
            st.session_state["text_input"] = voice_result.strip()

    user_query = st.text_input(
        f"✏️ {ui_text['text_input']}",
        placeholder=placeholder,
        key="text_input",
        label_visibility="visible",
    )

    ask_clicked = st.button(f"{ui_text['ask_button']} 🚀", use_container_width=True, type="primary")

    # ── Example Questions ───────────────────────────────────────────────────
    example_clicked = render_example_questions(language_pack)

    # Check if triggered by Ask button click or by clicking an example question
    triggered_query = None
    if ask_clicked and user_query.strip():
        triggered_query = user_query.strip()
    elif example_clicked:
        triggered_query = example_clicked

    if triggered_query:
        query = triggered_query



        with st.spinner(ui_text["searching"]):

            # Layer 1 safety check
            is_blocked, violation_type = check_query(query)

            if is_blocked:
                refusal = get_refusal_message(lang_code)
                st.session_state["chat_history"].append({
                    "role": "user",
                    "content": query,
                    "language_code": lang_code,
                })
                st.session_state["chat_history"].append({
                    "role": "assistant",
                    "content": refusal,
                    "is_refusal": True,
                    "language_code": lang_code,
                })
                st.session_state["last_answer"] = refusal

            else:
                # Retrieve relevant chunks
                results = retrieve(query, top_k=5)
                st.session_state["last_results"] = results

                if not results:
                    answer = get_no_context_message(lang_code)
                else:
                    context = format_context_block(results)
                    answer = generate_answer(query, context, language_code=lang_code)

                    # Layer 2: post-generation answer check
                    is_violating, snippet = check_answer(answer)
                    if is_violating:
                        logger.warning(f"Answer post-filter triggered for snippet: {snippet}")
                        answer = get_refusal_message(lang_code)
                        st.session_state["chat_history"].append({
                            "role": "user",
                            "content": query,
                            "language_code": lang_code,
                        })
                        st.session_state["chat_history"].append({
                            "role": "assistant",
                            "content": answer,
                            "is_refusal": True,
                            "language_code": lang_code,
                        })
                        st.session_state["last_answer"] = answer
                    else:
                        st.session_state["chat_history"].append({
                            "role": "user",
                            "content": query,
                            "language_code": lang_code,
                        })
                        st.session_state["chat_history"].append({
                            "role": "assistant",
                            "content": answer,
                            "is_refusal": False,
                            "sources": results,
                            "language_code": lang_code,
                        })
                        st.session_state["last_answer"] = answer

        st.session_state["clear_input"] = True
        st.rerun()

    # ── Chat History ────────────────────────────────────────────────────────
    if st.session_state["chat_history"]:
        st.markdown("---")
        st.markdown(f"### 💬 {ui_text['conversation']}")

        for i, msg in enumerate(reversed(display_history)):
            if msg["role"] == "user":
                st.markdown(f"""
                <div class="card" style="border-left:3px solid #58A6FF; margin-bottom:8px;">
                  <strong style="color:#58A6FF;">👤 {ui_text['you']}:</strong><br>
                  {html.escape(msg['content'])}
                </div>
                """, unsafe_allow_html=True)
            else:
                is_refusal = msg.get("is_refusal", False)
                render_answer_card(
                    msg["content"],
                    is_refusal=is_refusal,
                    sources=msg.get("sources", []),
                    translations=ui_text,
                )

                # TTS for the most recent answer only
                if i == 0:
                    render_tts_player(
                        msg["content"],
                        language_code=lang_code,
                        translations=ui_text,
                    )

        # Show source pills for last retrieval
        if st.session_state["last_results"]:
            render_source_pills(st.session_state["last_results"], ui_text)


# ─── RIGHT COLUMN: Adaptive Quiz ───────────────────────────────────────────
with col_quiz:
    quiz_title = f"🧠 {ui_text['quiz_title']}"
    st.markdown(
        f'<div class="quiz-card"><div class="card-header">{html.escape(quiz_title)}</div>',
        unsafe_allow_html=True,
    )

    quiz_subtitle = ui_text["quiz_subtitle"]
    st.markdown(
        f"<p style='font-size:13px;color:#8B949E;'>{html.escape(quiz_subtitle)}</p>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    quiz: QuizSession = st.session_state["quiz_session"]

    # Start / Restart button
    start_label = (
        f"🔄 {ui_text['quiz_restart']}"
        if quiz.is_complete else f"▶️ {ui_text['quiz_start']}"
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
            render_quiz_progress(answered, total, quiz.score, ui_text)
            question_translation = language_pack["questions"][question["id"]]

            # Difficulty badge
            diff_colors = {1: "#3FB950", 2: "#D29922", 3: "#F85149"}
            diff_labels = {
                1: ui_text["beginner"],
                2: ui_text["intermediate"],
                3: ui_text["advanced"],
            }
            diff = question["difficulty"]
            diff_label = ui_text["difficulty"].format(level=diff, label=diff_labels[diff])
            st.markdown(
                f'<span style="font-size:11px;font-weight:600;color:{diff_colors[diff]};'
                f'border:1px solid {diff_colors[diff]};padding:2px 8px;border-radius:12px;">'
                f'{html.escape(diff_label)}</span>',
                unsafe_allow_html=True
            )
            st.markdown("<br>", unsafe_allow_html=True)

            # Question text
            q_text = question_translation["text"]
            st.markdown(
                f'<div class="quiz-question">{html.escape(q_text)}</div>',
                unsafe_allow_html=True,
            )

            # Options
            options = question_translation["options"]

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
                            f'✅ {html.escape(opt_text)}</div>',
                            unsafe_allow_html=True
                        )
                    elif opt_idx == st.session_state.get("_chosen_idx"):
                        st.markdown(
                            f'<div style="padding:10px;border:2px solid #F85149;border-radius:8px;'
                            f'background:rgba(248,81,73,0.1);color:#F85149;margin:4px 0;">'
                            f'❌ {html.escape(opt_text)}</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            f'<div style="padding:10px;border:1px solid #30363D;border-radius:8px;'
                            f'color:#8B949E;margin:4px 0;">{html.escape(opt_text)}</div>',
                            unsafe_allow_html=True
                        )

                # Explanation
                is_correct = res.get("is_correct", False)
                result_icon = f"✅ {ui_text['correct']}" if is_correct else f"❌ {ui_text['wrong']}"
                explanation = question_translation["explanation"]
                source = res.get("source", "")

                st.markdown(f"""
                <div style="background:{'rgba(63,185,80,0.08)' if is_correct else 'rgba(248,81,73,0.08)'};
                  border:1px solid {'#3FB950' if is_correct else '#F85149'};
                  border-radius:8px;padding:16px;margin-top:12px;">
                  <strong style="color:{'#3FB950' if is_correct else '#F85149'}">{result_icon}</strong><br>
                  <span style="font-size:13px;color:#E6EDF3;">{html.escape(explanation)}</span><br>
                  <span style="font-size:11px;color:#58A6FF;margin-top:6px;display:block;">{html.escape(source)}</span>
                </div>
                """, unsafe_allow_html=True)

                next_label = f"{ui_text['next_question']} →"
                if st.button(next_label, key="quiz_next", use_container_width=True, type="primary"):
                    if quiz.is_complete:
                        result = quiz.get_final_result(lang_code)
                        badge = language_pack["badges"][str(result["score"])]
                        result["badge_title"] = badge["title"]
                        result["badge_desc"] = badge["description"]
                        st.session_state["quiz_result"] = result
                    else:
                        st.session_state["quiz_question"] = quiz.get_next_question()
                        st.session_state["quiz_answered"] = False
                    st.rerun()

    # Quiz complete — show score badge
    if quiz.is_complete and st.session_state.get("quiz_result") is None:
        result = quiz.get_final_result(lang_code)
        badge = language_pack["badges"][str(result["score"])]
        result["badge_title"] = badge["title"]
        result["badge_desc"] = badge["description"]
        st.session_state["quiz_result"] = result

    if quiz.is_complete and st.session_state.get("quiz_result"):
        current_result = st.session_state["quiz_result"]
        current_badge = language_pack["badges"][str(current_result["score"])]
        current_result["badge_title"] = current_badge["title"]
        current_result["badge_desc"] = current_badge["description"]
        render_score_badge(current_result, ui_text)

        missed = st.session_state["quiz_result"].get("fraud_types_missed", [])
        if missed:
            learn_label = f"📚 {ui_text['learn_more']}"
            st.markdown(f"**{learn_label}**")
            for ft in set(missed):
                ft_readable = language_pack["fraud_types"].get(
                    ft,
                    ft.replace("_", " ").title(),
                )
                st.markdown(f"- {ft_readable}")


# ── Safety Footer ───────────────────────────────────────────────────────────
render_safety_footer(ui_text)
