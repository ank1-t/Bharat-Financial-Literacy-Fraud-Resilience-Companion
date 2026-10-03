"""Translate all visible app copy and quiz content into the selected language."""

import json
import logging
import re
from copy import deepcopy

import google.generativeai as genai
import streamlit as st

from config.settings import GEMINI_API_KEY, GEMINI_MODEL, LANGUAGE_NAMES
from quiz.questions import QUESTIONS
from quiz.quiz_engine import SCORE_BADGES

logger = logging.getLogger(__name__)

UI_TEXT = {
    "app_title": "Bharat Financial Literacy Companion",
    "hero_title": "Bharat Financial Literacy & Fraud Resilience Companion",
    "hero_tagline": "Your trusted AI financial guide",
    "settings": "Settings",
    "knowledge_base": "Knowledge Base",
    "knowledge_ready": "Knowledge base ready",
    "knowledge_loading": "Knowledge base loading...",
    "api_key_missing": "AI service is not configured. Add your API key to the .env file.",
    "api_key_loaded": "AI service is ready",
    "about": "About",
    "sebi_helpline": "SEBI Investor Helpline",
    "clear_chat": "Clear Chat",
    "translation_loading": "Preparing this language...",
    "translation_error": "Could not load the selected language. Please try again or select English.",
    "kb_spinner": "Loading the investor education resources...",
    "ask_question": "Ask your question",
    "text_input": "Or type your question:",
    "question_placeholder": "e.g. What is a mutual fund? Is this WhatsApp group safe?",
    "ask_button": "Ask",
    "searching": "Searching trusted resources...",
    "no_context": "I couldn't find relevant information in the investor education resources. Please visit sebi.gov.in.",
    "conversation": "Conversation",
    "you": "You",
    "answer_header": "Saarthi's Answer",
    "safety_header": "Safety protection active",
    "retrieved_sources": "Retrieved Sources (for transparency)",
    "open_pdf_page": "Open PDF — Page",
    "pdf_unavailable": "PDF unavailable locally",
    "watch_video": "Watch video",
    "replaced_video": "This video source was replaced. Ask the question again for updated sources.",
    "show_chunk": "Show excerpt",
    "official_videos": "Official videos",
    "try_asking": "Try asking:",
    "quiz_title": "Fraud Awareness Quiz",
    "quiz_subtitle": "Can you spot investment fraud? Test your skills!",
    "quiz_start": "Start Quiz",
    "quiz_restart": "Restart Quiz",
    "quiz_question_progress": "Question {current} of {total}",
    "quiz_score": "Score: {score}/{answered}",
    "difficulty": "Level {level}: {label}",
    "beginner": "Beginner",
    "intermediate": "Intermediate",
    "advanced": "Advanced",
    "correct": "Correct!",
    "wrong": "Wrong",
    "next_question": "Next Question",
    "learn_more": "Learn more about:",
    "whatsapp_scam": "WhatsApp scam",
    "guaranteed_return": "Guaranteed return",
    "social_engineering": "Social engineering",
    "ponzi_scheme": "Ponzi scheme",
    "fake_advisor": "Fake advisor",
    "phishing": "Phishing",
    "regulatory_knowledge": "Investor rights and regulations",
    "page": "Page",
    "unknown_source": "Unknown source",
    "score_correct": "CORRECT",
    "speak": "Speak",
    "listening": "Listening...",
    "got_it": "Got it!",
    "microphone_unavailable": "Microphone unavailable",
    "copy_transcript": "Copy transcript",
    "copied": "Copied!",
    "speech_help": "Please use a browser that supports speech recognition.",
    "speech_retry": "Retrying with the language's standard speech code...",
    "speech_network_error": "Speech service is unreachable. You can type your question below.",
    "microphone_denied": "Microphone access denied. Allow microphone permission in your browser.",
    "no_speech": "No speech detected. Please try again.",
    "voice_error": "Voice input error. Please try again or type below.",
    "speech_start_error": "Could not start the microphone.",
    "listen": "Listen",
    "stop": "Stop",
    "tts_unsupported": "Speech playback is not supported in this browser.",
    "playing": "Playing...",
    "disclaimer_title": "Disclaimer:",
    "disclaimer": "This app is for educational purposes only. It does not constitute financial advice. Consult a",
    "advisor": "SEBI-registered advisor",
    "before_investing": "before investing.",
    "cybercrime": "Report cybercrime",
    "example_mutual_funds": "What is a mutual fund and how does it work?",
    "example_scams": "Is a WhatsApp group promising 40% returns safe?",
    "example_sebi": "What does SEBI do to protect investors?",
    "example_sip": "What is the difference between SIP and lump sum investment?",
}

def _source_bundle() -> dict:
    return {
        "ui": UI_TEXT,
        "examples": {
            "mutual_funds": UI_TEXT["example_mutual_funds"],
            "scams": UI_TEXT["example_scams"],
            "sebi": UI_TEXT["example_sebi"],
            "sip": UI_TEXT["example_sip"],
        },
        "questions": {
            question["id"]: {
                "text": question["text_en"],
                "options": question["options_en"],
                "explanation": question["explanation_en"],
            }
            for question in QUESTIONS
        },
        "badges": {
            str(score): {
                "title": badge["title_en"],
                "description": badge["desc_en"],
            }
            for score, badge in SCORE_BADGES.items()
        },
        "fraud_types": {
            "whatsapp_scam": UI_TEXT["whatsapp_scam"],
            "guaranteed_return": UI_TEXT["guaranteed_return"],
            "social_engineering": UI_TEXT["social_engineering"],
            "ponzi_scheme": UI_TEXT["ponzi_scheme"],
            "fake_advisor": UI_TEXT["fake_advisor"],
            "phishing": UI_TEXT["phishing"],
        },
    }


def _validate_translation(source, translated, path="root"):
    if isinstance(source, dict):
        if not isinstance(translated, dict) or source.keys() != translated.keys():
            raise ValueError(f"Translation response has an invalid object shape at {path}")
        for key, value in source.items():
            _validate_translation(value, translated[key], f"{path}.{key}")
    elif isinstance(source, list):
        if not isinstance(translated, list) or len(source) != len(translated):
            raise ValueError(f"Translation response has an invalid list shape at {path}")
        for index, value in enumerate(source):
            _validate_translation(value, translated[index], f"{path}[{index}]")
    elif not isinstance(translated, str) or not translated.strip():
        raise ValueError(f"Translation response contains invalid text at {path}")
    elif isinstance(source, str):
        placeholders = re.findall(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}", source)
        if any(placeholder not in translated for placeholder in placeholders):
            raise ValueError(f"Translation response changed a format placeholder at {path}")


@st.cache_data(show_spinner=False, max_entries=10)
def _translate_bundle(language_code: str, source_json: str) -> dict:
    if not GEMINI_API_KEY:
        raise RuntimeError("A Gemini API key is required to translate the complete interface.")

    source = json.loads(source_json)
    language = LANGUAGE_NAMES.get(language_code)
    if not language:
        raise ValueError(f"Unsupported language code: {language_code}")

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(model_name=GEMINI_MODEL)
        response = model.generate_content(
            (
                f"Translate every human-readable text value in this JSON into {language}. "
                "Return only valid JSON with exactly the same object keys, array lengths, and structure. "
                "Use the target language's native script and translate complete sentences; leave English "
                "only for proper nouns, official names, and standard abbreviations. "
                "Do not translate proper nouns, product names, SEBI, URLs, website domains, amounts, "
                "or the symbols/numbers inside text. Translate quiz wording and options faithfully; "
                "do not change their meaning or order. Keep citations and source references unchanged. "
                "Do not add explanations or omit any fields.\n\n"
                f"JSON:\n{source_json}"
            ),
            generation_config=genai.types.GenerationConfig(
                temperature=0,
                response_mime_type="application/json",
                max_output_tokens=8192,
            ),
        )
    except Exception as error:
        logger.exception("Could not translate interface into %s", language_code)
        raise RuntimeError(f"Translation service failed for {language}.") from error
    if not response or not response.text:
        raise RuntimeError(f"The translation service returned no content for {language}.")

    translated = json.loads(response.text)
    _validate_translation(source, translated)
    logger.info("Loaded translated interface for %s", language_code)
    return translated


def get_language_pack(language_code: str) -> dict:
    """Return translations for app copy, examples, quiz content, and result badges."""
    if language_code == "en-IN":
        return _source_bundle()

    source_json = json.dumps(_source_bundle(), ensure_ascii=False, sort_keys=True)
    return _translate_bundle(language_code, source_json)


def get_translated_history(history: list[dict], language_code: str) -> list[dict]:
    """Translate existing chat text when a user changes the app language."""
    translated = deepcopy(history)
    if language_code == "en-IN":
        return translated

    messages_to_translate = []
    target_messages = []
    for message in translated:
        if message.get("language_code") == language_code:
            continue
        target_messages.append(message)
        messages_to_translate.append(message["content"])

    if messages_to_translate:
        translated_texts = _translate_history_texts(
            language_code,
            json.dumps(messages_to_translate, ensure_ascii=False),
        )
        if len(translated_texts) != len(target_messages):
            raise ValueError("The translation service changed the conversation length.")
        for message, content in zip(target_messages, translated_texts):
            message["content"] = content
            message["language_code"] = language_code
    return translated


@st.cache_data(show_spinner=False, max_entries=512)
def _translate_history_texts(language_code: str, messages_json: str) -> list[str]:
    """Translate chat history in one request while preserving citation tokens."""
    if not GEMINI_API_KEY:
        raise RuntimeError("A Gemini API key is required to translate conversation history.")

    language = LANGUAGE_NAMES[language_code]
    source_texts = json.loads(messages_json)
    placeholders = []
    protected_texts = []
    for message_index, text in enumerate(source_texts):
        protected_text = text
        message_placeholders = []
        for citation_index, citation in enumerate(
            re.findall(r"\[(?:Source|Video):[^\]]+\]", text)
        ):
            marker = f"__MSG{message_index}_CITATION{citation_index}__"
            protected_text = protected_text.replace(citation, marker, 1)
            message_placeholders.append((marker, citation))
        placeholders.append(message_placeholders)
        protected_texts.append(protected_text)

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(model_name=GEMINI_MODEL)
        response = model.generate_content(
            f"Translate every string in this JSON array into {language}. "
            "Return only a JSON array with the same number of strings in the same order. "
            "Preserve each __MSGn_CITATIONn__ placeholder exactly. Do not omit or add text.\n\n"
            f"{json.dumps(protected_texts, ensure_ascii=False)}",
            generation_config=genai.types.GenerationConfig(
                temperature=0,
                response_mime_type="application/json",
                max_output_tokens=8192,
            ),
        )
    except Exception as error:
        logger.exception("Could not translate conversation into %s", language_code)
        raise RuntimeError(f"Translation service failed for {language}.") from error
    if not response or not response.text:
        raise RuntimeError(f"The translation service returned no text for {language}.")

    results = json.loads(response.text)
    if (
        not isinstance(results, list)
        or len(results) != len(protected_texts)
        or not all(isinstance(item, str) for item in results)
    ):
        raise ValueError("The translation service returned an invalid conversation translation.")

    restored = []
    for result, message_placeholders in zip(results, placeholders):
        for marker, citation in message_placeholders:
            if marker not in result:
                raise ValueError("The translation service changed a protected citation.")
            result = result.replace(marker, citation)
        restored.append(result)
    return restored
