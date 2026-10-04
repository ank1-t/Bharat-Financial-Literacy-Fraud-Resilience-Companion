import base64

from config.settings import YOUTUBE_SOURCES
from ui import components
from ui import localization
from voice import speech_component


def test_hero_does_not_render_technology_badges(monkeypatch):
    rendered = []
    monkeypatch.setattr(components.st, "markdown", lambda text, **kwargs: rendered.append(text))

    components.render_hero()

    assert len(rendered) == 1
    assert "hero-badges" not in rendered[0]
    assert "Gemini" not in rendered[0]
    assert "ChromaDB" not in rendered[0]


def test_supported_languages_have_translation_names():
    from config.settings import LANGUAGE_NAMES, LANGUAGE_OPTIONS

    assert set(LANGUAGE_OPTIONS.values()) == set(LANGUAGE_NAMES)


def test_voice_controls_use_selected_language_translations(monkeypatch):
    rendered = []
    monkeypatch.setattr(
        speech_component.components,
        "html",
        lambda content, height: rendered.append(content),
    )
    ui_text = dict(localization.UI_TEXT)
    ui_text.update({
        "speak": "स्थानिक बोला",
        "listening": "ऐकत आहे",
        "got_it": "समजले",
        "microphone_unavailable": "मायक्रोफोन उपलब्ध नाही",
    })

    speech_component.render_voice_input("mr-IN", translations=ui_text)

    assert "🎤 स्थानिक बोला" in rendered[0]
    assert "ऐकत आहे" in rendered[0]
    assert "मायक्रोफोन उपलब्ध नाही" in rendered[0]


def test_youtube_watch_url_uses_video_id_and_timestamp():
    url = components._youtube_watch_url({
        "video_id": YOUTUBE_SOURCES[0]["video_id"],
        "start_sec": 154.8,
    })

    assert url == f"https://youtu.be/{YOUTUBE_SOURCES[0]['video_id']}?t=154s"


def test_youtube_watch_url_rejects_invalid_video_id():
    assert components._youtube_watch_url({"video_id": "not a video id"}) is None


def test_youtube_watch_url_rejects_removed_source():
    assert components._youtube_watch_url({"video_id": "0Jl-cJJBFdA"}) is None


def test_mutual_fund_video_is_configured_as_active_nse_source():
    mutual_fund_source = next(
        source for source in YOUTUBE_SOURCES
        if source["video_id"] == "PS4amNfYx0k"
    )

    assert mutual_fund_source["source_tag"] == "NSE India — Mutual Funds"
    assert components._youtube_watch_url(mutual_fund_source) == (
        "https://youtu.be/PS4amNfYx0k?t=0s"
    )


def test_pdf_link_opens_at_cited_page(tmp_path, monkeypatch):
    pdf_path = tmp_path / "investor-guide.pdf"
    pdf_content = b"%PDF-test-content"
    pdf_path.write_bytes(pdf_content)
    rendered = {}
    monkeypatch.setattr(
        components.components,
        "html",
        lambda html, height: rendered.update(html=html, height=height),
    )

    components._render_pdf_link(pdf_path, 7, "Open PDF — Page 7")

    assert base64.b64encode(pdf_content).decode("ascii") in rendered["html"]
    assert "application/pdf" in rendered["html"]
    assert "#page=7" in rendered["html"]
    assert rendered["height"] == 48


def test_render_tts_player_controls_and_translations(monkeypatch):
    rendered = []
    monkeypatch.setattr(
        speech_component.components,
        "html",
        lambda content, height: rendered.append({"content": content, "height": height}),
    )
    ui_text = dict(localization.UI_TEXT)
    ui_text.update({
        "listen": "ऐका",
        "stop": "थांबवा",
        "playing": "वाजत आहे...",
    })

    sample_answer = "म्युच्युअल फंड [Source: sebi_mf_guide.pdf, Pg 3] **गुंतवणूक** करण्यासाठी उत्तम पर्याय आहे."
    speech_component.render_tts_player(sample_answer, language_code="mr-IN", translations=ui_text)

    assert len(rendered) == 1
    html_out = rendered[0]["content"]
    assert "🔊 ऐका" in html_out
    assert "⏹ थांबवा" in html_out
    assert "वाजत आहे..." in html_out
    assert "speakText()" in html_out
    assert "stopText()" in html_out
    # Check citation stripped from spoken text json
    assert "sebi_mf_guide.pdf" not in html_out
    assert "targetLang = 'mr-IN'" in html_out

