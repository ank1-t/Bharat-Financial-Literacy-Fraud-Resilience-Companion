"""
ui/components.py
─────────────────
Reusable Streamlit UI building blocks for the Bharat Financial Literacy app.
All rendering functions use st.markdown() with pre-defined CSS classes.
"""

import base64
import html
import re
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from config.settings import PDF_DIR, YOUTUBE_SOURCES
from rag.generator import extract_citations
from ui.localization import UI_TEXT


def render_hero(translations: dict | None = None):
    """Render the app hero header with its name and tagline."""
    ui_text = translations or UI_TEXT
    st.markdown(f"""
    <div class="hero-container">
      <div class="hero-title">🇮🇳 {html.escape(ui_text['hero_title'])}</div>
      <div class="hero-title" style="font-size:18px; margin-top:-4px;">
        {html.escape(ui_text['app_title'])}
      </div>
      <div class="hero-tagline">
        {html.escape(ui_text['hero_tagline'])}
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_answer_card(
    answer: str,
    is_refusal: bool = False,
    sources: list[dict] | None = None,
    translations: dict | None = None,
):
    """
    Render the LLM answer in a styled card.
    Refusal answers get a red-accented card; normal answers get green.
    Uses native st.markdown for proper formatting (lists, bolding, headings).
    """
    border_color = "rgba(248, 81, 73, 0.4)" if is_refusal else "rgba(63, 185, 80, 0.4)"
    bg_gradient = (
        "linear-gradient(135deg, rgba(31, 13, 13, 0.8) 0%, rgba(36, 21, 21, 0.8) 100%)"
        if is_refusal else
        "linear-gradient(135deg, rgba(13, 31, 13, 0.8) 0%, rgba(15, 36, 21, 0.8) 100%)"
    )
    ui_text = translations or UI_TEXT
    header_text = (
        f"🚫 {ui_text['safety_header']}"
        if is_refusal else f"💡 {ui_text['answer_header']}"
    )
    header_color = "#F85149" if is_refusal else "#3FB950"

    st.markdown(
        f'<div style="background:{bg_gradient}; border:1px solid {border_color}; border-left:4px solid {header_color}; '
        f'border-radius:12px; padding:16px 20px 8px 20px; margin:16px 0;">'
        f'<div style="font-size:13px; font-weight:600; text-transform:uppercase; letter-spacing:1px; color:{header_color}; margin-bottom:12px;">{html.escape(header_text)}</div>',
        unsafe_allow_html=True
    )
    st.markdown(answer)
    st.markdown('</div>', unsafe_allow_html=True)

    # Render citation badges
    if not is_refusal:
        citations = extract_citations(answer)
        if citations:
            badges_html = '<div class="citations-row">'
            replaced_video_citation = False
            for cit in citations:
                source = _find_citation_source(cit, sources or [])
                metadata = source.get("metadata", {}) if source else {}
                if cit.startswith("[Source:") and metadata:
                    pdf_path = (PDF_DIR / metadata.get("filename", "")).resolve()
                    if pdf_path.parent == PDF_DIR.resolve() and pdf_path.is_file():
                        badges_html += "</div>"
                        st.markdown(badges_html, unsafe_allow_html=True)
                        _render_pdf_link(pdf_path, metadata.get("page", 1), f"📄 {cit}")
                        badges_html = '<div class="citations-row">'
                    else:
                        badges_html += f'<span class="citation-badge citation-pdf">📄 {html.escape(cit)}</span>'
                elif cit.startswith("[Video:") and metadata:
                    watch_url = _youtube_watch_url(metadata)
                    if watch_url:
                        badges_html += "</div>"
                        st.markdown(badges_html, unsafe_allow_html=True)
                        st.link_button(f"🎬 {cit}", watch_url)
                        badges_html = '<div class="citations-row">'
                    else:
                        badges_html += f'<span class="citation-badge citation-video">🎬 {html.escape(cit)}</span>'
                        replaced_video_citation = replaced_video_citation or bool(metadata)
                elif cit.startswith("[Source:"):
                    badges_html += f'<span class="citation-badge citation-pdf">📄 {html.escape(cit)}</span>'
                elif cit.startswith("[Video:"):
                    badges_html += f'<span class="citation-badge citation-video">🎬 {html.escape(cit)}</span>'
            badges_html += '</div>'
            st.markdown(badges_html, unsafe_allow_html=True)
            if replaced_video_citation:
                st.caption(ui_text["replaced_video"])



def render_kb_status(chunk_count: int, translations: dict | None = None):
    """Render the knowledge base loading status in the sidebar."""
    ui_text = translations or UI_TEXT
    if chunk_count > 0:
        dot_class = "dot-green"
        label = f"{ui_text['knowledge_ready']} ({chunk_count})"
    else:
        dot_class = "dot-orange"
        label = ui_text["knowledge_loading"]

    st.sidebar.markdown(f"""
    <div class="kb-status">
      <span class="status-dot {dot_class}"></span>
      <span>{label}</span>
    </div>
    """, unsafe_allow_html=True)


def render_source_pills(results: list[dict], translations: dict | None = None):
    """
    Render a compact list of retrieved sources as expandable pills.
    Useful for showing judges which exact chunks were used.
    """
    if not results:
        return

    ui_text = translations or UI_TEXT
    with st.expander(f"📚 {ui_text['retrieved_sources']}", expanded=False):
        retrieved_video_ids = set()
        for i, r in enumerate(results, 1):
            meta = r["metadata"]
            src_type = meta.get("type", "unknown")
            if src_type == "pdf":
                icon = "📄"
                info = (
                    f"{meta.get('source','?')} — "
                    f"{ui_text['page']} {meta.get('page','?')}"
                )
                filename = meta.get("filename", "")
                pdf_path = (PDF_DIR / filename).resolve() if filename else None
                if pdf_path and pdf_path.parent == PDF_DIR.resolve() and pdf_path.is_file():
                    _render_pdf_link(
                        pdf_path,
                        meta.get("page", 1),
                        f"{ui_text['open_pdf_page']} {meta.get('page', '?')}",
                    )
                else:
                    st.caption(f"{ui_text['pdf_unavailable']}: {filename or '—'}")
            elif src_type == "youtube":
                icon = "🎬"
                info = f"{meta.get('source','?')} — {meta.get('timestamp','00:00')}"
                retrieved_video_ids.add(meta.get("video_id"))
                watch_url = _youtube_watch_url(meta)
                if watch_url:
                    st.link_button(
                        f"🎬 {ui_text['watch_video']}",
                        watch_url,
                    )
                else:
                    st.caption(ui_text["replaced_video"])
            else:
                icon = "📋"
                info = meta.get("source", ui_text["unknown_source"])

            st.markdown(f"**{icon} {i}.** {info}")
            with st.expander(f"{ui_text['show_chunk']} {i}", expanded=False):
                st.text(r["text"][:400] + ("..." if len(r["text"]) > 400 else ""))

        additional_videos = [
            source for source in YOUTUBE_SOURCES
            if source["video_id"] not in retrieved_video_ids
        ]
        if additional_videos:
            st.markdown(f"**{ui_text['official_videos']}**")
            for source in additional_videos:
                watch_url = _youtube_watch_url(source)
                if watch_url:
                    st.link_button(f"🎬 {ui_text['watch_video']}: {source['title']}", watch_url)


def _youtube_watch_url(metadata: dict) -> str | None:
    """Build a timestamped YouTube URL from a transcript source's metadata."""
    video_id = metadata.get("video_id", "")
    if not isinstance(video_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        return None
    if video_id not in {source["video_id"] for source in YOUTUBE_SOURCES}:
        return None

    try:
        start_seconds = max(0, int(float(metadata.get("start_sec", 0))))
    except (TypeError, ValueError):
        start_seconds = 0
    return f"https://youtu.be/{video_id}?t={start_seconds}s"


def _find_citation_source(citation: str, sources: list[dict]) -> dict | None:
    """Find the retrieved chunk whose metadata matches a generated citation."""
    match = re.fullmatch(r"\[Source: (.*), Pg (\d+)\]", citation)
    if match:
        source_name, page = match.groups()
        return next(
            (
                source
                for source in sources
                if source.get("metadata", {}).get("type") == "pdf"
                and source["metadata"].get("source") == source_name
                and str(source["metadata"].get("page")) == page
            ),
            None,
        )

    match = re.fullmatch(r"\[Video: (.*), Time ([^\]]+)\]", citation)
    if match:
        source_name, timestamp = match.groups()
        return next(
            (
                source
                for source in sources
                if source.get("metadata", {}).get("type") == "youtube"
                and source["metadata"].get("source") == source_name
                and source["metadata"].get("timestamp") == timestamp
            ),
            None,
        )
    return None


def _render_pdf_link(pdf_path: Path, page: int | str, label: str):
    """Open an existing local PDF in a new browser tab at its cited page."""
    try:
        page_number = max(1, int(page))
    except (TypeError, ValueError):
        page_number = 1

    encoded_pdf = base64.b64encode(pdf_path.read_bytes()).decode("ascii")
    safe_label = html.escape(label)
    components.html(
        f"""
        <button id="open-pdf" type="button">{safe_label}</button>
        <script>
          const bytes = Uint8Array.from(atob("{encoded_pdf}"), c => c.charCodeAt(0));
          const pdfUrl = URL.createObjectURL(new Blob([bytes], {{type: "application/pdf"}}));
          document.getElementById("open-pdf").addEventListener("click", () => {{
            window.open(pdfUrl + "#page={page_number}", "_blank");
          }});
        </script>
        <style>
          button {{
            background: #ff6b00; color: white; border: 0; border-radius: 6px;
            padding: 0.45rem 0.8rem; cursor: pointer; font: inherit;
          }}
        </style>
        """,
        height=48,
    )


def render_quiz_progress(answered: int, total: int, score: int, translations: dict | None = None):
    """Render the quiz progress bar and running score."""
    ui_text = translations or UI_TEXT
    progress = answered / total if total > 0 else 0
    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
      <span style="font-size:13px; color:#8B949E;">
        {html.escape(ui_text['quiz_question_progress'].format(current=answered + 1, total=total))}
      </span>
      <span style="font-size:13px; font-weight:600; color:#3FB950;">
        {html.escape(ui_text['quiz_score'].format(score=score, answered=answered))}
      </span>
    </div>
    """, unsafe_allow_html=True)
    st.progress(progress)


def render_score_badge(result: dict, translations: dict | None = None):
    """Render the final quiz score badge."""
    ui_text = translations or UI_TEXT
    st.markdown(f"""
    <div class="score-badge">
      <div class="score-emoji">{result['badge_emoji']}</div>
      <div class="score-title">{html.escape(result['badge_title'])}</div>
      <div class="score-num">{result['score']}<span style="font-size:20px;color:#8B949E;">/{result['total']}</span></div>
      <div class="score-sub">{result['percentage']}% {html.escape(ui_text['score_correct'])}</div>
      <div class="score-desc" style="margin-top:12px;">{html.escape(result['badge_desc'])}</div>
    </div>
    """, unsafe_allow_html=True)


def render_safety_footer(translations: dict | None = None):
    """Render the always-visible SEBI disclaimer footer."""
    ui_text = translations or UI_TEXT
    st.markdown(f"""
    <div class="safety-footer">
      ⚠️ <strong>{html.escape(ui_text['disclaimer_title'])}</strong>
      {html.escape(ui_text['disclaimer'])}
      <a href="https://www.sebi.gov.in" target="_blank" style="color:#FF6B00;">{html.escape(ui_text['advisor'])}</a>
      {html.escape(ui_text['before_investing'])} &nbsp;|&nbsp;
      📞 {html.escape(ui_text['sebi_helpline'])}: <strong>1800-266-7575</strong> &nbsp;|&nbsp;
      🌐 <a href="https://cybercrime.gov.in" target="_blank" style="color:#FF6B00;">{html.escape(ui_text['cybercrime'])}</a>
    </div>
    """, unsafe_allow_html=True)


def render_example_questions(language_pack: dict) -> str | None:
    """Render clickable example questions to guide first-time users.
    Returns the clicked question string if an example button was pressed, else None.
    """
    ui_text = language_pack["ui"]
    examples = list(language_pack["examples"].values())
    st.markdown(f"**💬 {ui_text['try_asking']}**")
    cols = st.columns(2)
    clicked_query = None
    for i, example in enumerate(examples):
        with cols[i % 2]:
            if st.button(
                f"'{example}'",
                key=f"ex_{i}",
                use_container_width=True,
            ):
                clicked_query = example

    return clicked_query
