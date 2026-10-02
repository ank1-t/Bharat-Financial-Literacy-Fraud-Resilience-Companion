"""
ui/components.py
─────────────────
Reusable Streamlit UI building blocks for the Bharat Financial Literacy app.
All rendering functions use st.markdown() with pre-defined CSS classes.
"""

import streamlit as st
from rag.generator import extract_citations


def render_hero():
    """Render the app hero header with name, tagline, and feature badges."""
    st.markdown("""
    <div class="hero-container">
      <div class="hero-title">🇮🇳 भारत वित्तीय साथी</div>
      <div class="hero-title" style="font-size:18px; margin-top:-4px;">
        Bharat Financial Literacy & Fraud Resilience Companion
      </div>
      <div class="hero-tagline">
        आपका विश्वसनीय AI वित्तीय मार्गदर्शक | Your trusted AI financial guide
      </div>
      <div class="hero-badges">
        <span class="hero-badge badge-sebi">📄 SEBI-Sourced Knowledge</span>
        <span class="hero-badge badge-gemini">✨ Gemini 1.5 Flash</span>
        <span class="hero-badge badge-voice">🎤 Voice-First</span>
        <span class="hero-badge badge-sebi" style="color:#D29922;border-color:#D29922;background:rgba(210,153,34,0.1);">
          🛡️ No Stock Tips
        </span>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_answer_card(answer: str, is_refusal: bool = False):
    """
    Render the LLM answer in a styled card.
    Refusal answers get a red-accented card; normal answers get green.
    Also extracts and displays citation badges.
    """
    card_class = "refusal-card" if is_refusal else "answer-card"
    st.markdown(f"""
    <div class="{card_class}">
      <div class="card-header">
        {'🚫 Safety Guardrail Active' if is_refusal else '💡 Saarthi का जवाब | Saarthi\'s Answer'}
      </div>
      <div class="answer-text">{answer.replace(chr(10), '<br>')}</div>
    </div>
    """, unsafe_allow_html=True)

    # Render citation badges
    if not is_refusal:
        citations = extract_citations(answer)
        if citations:
            badges_html = '<div class="citations-row">'
            for cit in citations:
                if cit.startswith("[Source:"):
                    badges_html += f'<span class="citation-badge citation-pdf">📄 {cit}</span>'
                elif cit.startswith("[Video:"):
                    badges_html += f'<span class="citation-badge citation-video">🎬 {cit}</span>'
            badges_html += '</div>'
            st.markdown(badges_html, unsafe_allow_html=True)


def render_kb_status(chunk_count: int):
    """Render the knowledge base loading status in the sidebar."""
    if chunk_count > 0:
        dot_class = "dot-green"
        label = f"Knowledge base ready ({chunk_count} chunks)"
    else:
        dot_class = "dot-orange"
        label = "Knowledge base loading..."

    st.sidebar.markdown(f"""
    <div class="kb-status">
      <span class="status-dot {dot_class}"></span>
      <span>{label}</span>
    </div>
    """, unsafe_allow_html=True)


def render_source_pills(results: list[dict]):
    """
    Render a compact list of retrieved sources as expandable pills.
    Useful for showing judges which exact chunks were used.
    """
    if not results:
        return

    with st.expander("📚 Retrieved Sources (for transparency)", expanded=False):
        for i, r in enumerate(results, 1):
            meta = r["metadata"]
            src_type = meta.get("type", "unknown")
            if src_type == "pdf":
                icon = "📄"
                info = f"{meta.get('source','?')} — Page {meta.get('page','?')}"
            elif src_type == "youtube":
                icon = "🎬"
                info = f"{meta.get('source','?')} — {meta.get('timestamp','00:00')}"
                url = meta.get("watch_url", "")
                if url:
                    info += f" ([Watch]({url}))"
            else:
                icon = "📋"
                info = meta.get("source", "Unknown source")

            st.markdown(f"**{icon} {i}.** {info}")
            with st.expander(f"Show chunk {i}", expanded=False):
                st.text(r["text"][:400] + ("..." if len(r["text"]) > 400 else ""))


def render_quiz_progress(answered: int, total: int, score: int):
    """Render the quiz progress bar and running score."""
    progress = answered / total if total > 0 else 0
    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
      <span style="font-size:13px; color:#8B949E;">
        Question {answered + 1} of {total}
      </span>
      <span style="font-size:13px; font-weight:600; color:#3FB950;">
        Score: {score}/{answered}
      </span>
    </div>
    """, unsafe_allow_html=True)
    st.progress(progress)


def render_score_badge(result: dict):
    """Render the final quiz score badge."""
    st.markdown(f"""
    <div class="score-badge">
      <div class="score-emoji">{result['badge_emoji']}</div>
      <div class="score-title">{result['badge_title']}</div>
      <div class="score-num">{result['score']}<span style="font-size:20px;color:#8B949E;">/{result['total']}</span></div>
      <div class="score-sub">{result['percentage']}% CORRECT</div>
      <div class="score-desc" style="margin-top:12px;">{result['badge_desc']}</div>
    </div>
    """, unsafe_allow_html=True)


def render_safety_footer():
    """Render the always-visible SEBI disclaimer footer."""
    st.markdown("""
    <div class="safety-footer">
      ⚠️ <strong>Disclaimer:</strong> This app is for educational purposes only.
      It does not constitute financial advice. All information is sourced from publicly available
      SEBI investor awareness materials. Consult a
      <a href="https://www.sebi.gov.in" target="_blank" style="color:#FF6B00;">SEBI-registered advisor</a>
      before investing. &nbsp;|&nbsp;
      📞 SEBI Helpline: <strong>1800-266-7575</strong> &nbsp;|&nbsp;
      🌐 <a href="https://cybercrime.gov.in" target="_blank" style="color:#FF6B00;">cybercrime.gov.in</a>
    </div>
    """, unsafe_allow_html=True)


def render_example_questions(lang_code: str):
    """Render clickable example questions to guide first-time users."""
    is_hindi = lang_code.startswith("hi")

    if is_hindi:
        examples = [
            "म्यूचुअल फंड क्या होता है?",
            "WhatsApp पर 40% रिटर्न का वादा — क्या यह सच है?",
            "SEBI क्या है और यह निवेशकों की रक्षा कैसे करता है?",
            "SIP और lump sum निवेश में क्या अंतर है?",
        ]
    else:
        examples = [
            "What is a mutual fund and how does it work?",
            "Is a WhatsApp group promising 40% returns safe?",
            "What does SEBI do to protect investors?",
            "What is the difference between SIP and lump sum investment?",
        ]

    st.markdown("**💬 Try asking:**" if not is_hindi else "**💬 पूछकर देखें:**")
    cols = st.columns(2)
    for i, example in enumerate(examples):
        with cols[i % 2]:
            if st.button(f"'{example}'", key=f"ex_{i}", use_container_width=True):
                st.session_state["pending_query"] = example
                st.rerun()
