"""
voice/speech_component.py
──────────────────────────
Web Speech API bridge for Streamlit.

Renders a JavaScript-powered voice capture button inside a Streamlit
component iframe. On recognition, the transcript is passed back to
the parent Streamlit app via the Streamlit component value mechanism.

Also provides text-to-speech (TTS) functionality for reading back
LLM answers aloud in the selected language.

Note: Web Speech API requires a modern browser (Chrome 33+, Edge 79+).
Firefox has limited support. Safari requires user gesture.
"""

import html
import json

import streamlit.components.v1 as components

from ui.localization import UI_TEXT


def render_voice_input(
    language_code: str = "hi-IN",
    key: str = "voice_input",
    translations: dict | None = None,
) -> str | None:
    """
    Render a voice input button using the Web Speech API.

    The component listens for a single continuous utterance and returns
    the recognized transcript as a string via Streamlit component value.

    Args:
        language_code: BCP-47 code, e.g. "hi-IN", "mr-IN", or "en-IN".
        key:           Unique Streamlit component key.

    Returns:
        Recognized transcript string, or None if not yet spoken.
    """
    ui_text = translations or UI_TEXT
    btn_label = f"🎤 {ui_text['speak']}"
    listening = f"🔴 {ui_text['listening']}"
    done_label = f"✅ {ui_text['got_it']}"
    voice_messages = {
        "speak": btn_label,
        "listening": listening,
        "got_it": done_label,
        "microphone_unavailable": ui_text["microphone_unavailable"],
        "speech_help": ui_text["speech_help"],
        "speech_retry": ui_text["speech_retry"],
        "speech_network_error": ui_text["speech_network_error"],
        "microphone_denied": ui_text["microphone_denied"],
        "no_speech": ui_text["no_speech"],
        "voice_error": ui_text["voice_error"],
        "speech_start_error": ui_text["speech_start_error"],
        "copy_transcript": ui_text["copy_transcript"],
        "copied": ui_text["copied"],
    }
    voice_messages_json = json.dumps(voice_messages, ensure_ascii=False)

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{
          margin: 0;
          padding: 4px;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          background: transparent;
        }}
        #voiceBtn {{
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 10px 20px;
          border: 2px solid #FF6B00;
          border-radius: 50px;
          background: linear-gradient(135deg, #FF6B00 0%, #FF8C38 100%);
          color: white;
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.25s ease;
          width: 100%;
          justify-content: center;
          box-shadow: 0 4px 15px rgba(255, 107, 0, 0.3);
        }}
        #voiceBtn:hover {{
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(255, 107, 0, 0.5);
        }}
        #voiceBtn.listening {{
          background: linear-gradient(135deg, #e53935 0%, #ef5350 100%);
          border-color: #e53935;
          animation: pulse 1.5s infinite;
        }}
        @keyframes pulse {{
          0%, 100% {{ box-shadow: 0 0 0 0 rgba(229, 57, 53, 0.4); }}
          50%        {{ box-shadow: 0 0 0 12px rgba(229, 57, 53, 0); }}
        }}
        #status {{
          margin-top: 6px;
          font-size: 12px;
          color: #8B949E;
          text-align: center;
        }}
        #transcript-display {{
          margin-top: 6px;
          font-size: 13px;
          color: #58A6FF;
          text-align: center;
          font-weight: 500;
          min-height: 18px;
          padding: 2px 8px;
          background: rgba(88, 166, 255, 0.08);
          border-radius: 6px;
        }}
        .copy-btn {{
          display: none;
          margin: 6px auto 0;
          padding: 4px 12px;
          font-size: 12px;
          background: #21262D;
          color: #E6EDF3;
          border: 1px solid #30363D;
          border-radius: 12px;
          cursor: pointer;
        }}
        .copy-btn:hover {{ background: #30363D; }}
      </style>
    </head>
    <body>
      <button id="voiceBtn" onclick="toggleVoice()">{html.escape(btn_label)}</button>
      <div id="status"></div>
      <div id="transcript-display"></div>
      <button id="copyBtn" class="copy-btn" onclick="copyTranscript()">📋 {html.escape(ui_text['copy_transcript'])}</button>

      <script>
        const messages = {voice_messages_json};
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const btn = document.getElementById('voiceBtn');
        const statusEl = document.getElementById('status');
        const transcriptEl = document.getElementById('transcript-display');
        const copyBtn = document.getElementById('copyBtn');

        let isListening = false;
        let recognition = null;
        let lastTranscript = '';

        if (!SpeechRecognition) {{
          btn.textContent = '❌ ' + messages.microphone_unavailable;
          btn.disabled = true;
          btn.style.background = '#444';
          btn.style.borderColor = '#444';
          statusEl.textContent = messages.speech_help;
        }}

        function toggleVoice() {{
          if (isListening) {{
            stopVoice();
          }} else {{
            startVoice();
          }}
        }}

        function stopVoice() {{
          if (recognition) {{
            try {{ recognition.stop(); }} catch(e) {{}}
          }}
          isListening = false;
          btn.classList.remove('listening');
          btn.textContent = messages.speak;
        }}

        function copyTranscript() {{
          if (lastTranscript) {{
            navigator.clipboard.writeText(lastTranscript).then(() => {{
              copyBtn.textContent = '✅ ' + messages.copied;
              setTimeout(() => {{ copyBtn.textContent = '📋 ' + messages.copy_transcript; }}, 2000);
            }});
          }}
        }}

        function fillParentInput(text) {{
          try {{
            // Attempt 1: Standard Streamlit component postMessage
            window.parent.postMessage({{
              isStreamlitMessage: true,
              type: 'streamlit:setComponentValue',
              value: text
            }}, '*');

            // Attempt 2: If same-origin (standard Streamlit embed), set input value directly
            const parentDoc = window.parent.document;
            const input = parentDoc.querySelector('input[data-testid="stTextInputRootElement"]') ||
                          parentDoc.querySelector('input[type="text"]');
            if (input) {{
              const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
              nativeSetter.call(input, text);
              input.dispatchEvent(new Event('input', {{ bubbles: true }}));
              input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
          }} catch (err) {{
            // Iframe sandbox or cross-origin restrictions
            console.log('Parent transfer notification:', err);
          }}
        }}

        function startVoice() {{
          try {{
            recognition = new SpeechRecognition();
          }} catch(e) {{
            statusEl.textContent = 'Speech recognition initialization failed.';
            return;
          }}

          // Primary language with fallback list
          const primaryLang = '{language_code}';
          const fallbackLang = primaryLang.split('-')[0];
          recognition.lang = primaryLang;
          recognition.interimResults = false;
          recognition.maxAlternatives = 1;
          recognition.continuous = false;

          btn.textContent = messages.listening;
          btn.classList.add('listening');
          statusEl.textContent = '';
          transcriptEl.textContent = '';
          copyBtn.style.display = 'none';
          isListening = true;

          recognition.onresult = function(event) {{
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {{
              const t = event.results[i][0].transcript;
              if (event.results[i].isFinal) {{
                finalTranscript += t;
              }} else {{
                interimTranscript += t;
              }}
            }}

            const current = finalTranscript || interimTranscript;
            transcriptEl.textContent = current;

            if (finalTranscript) {{
              lastTranscript = finalTranscript;
              copyBtn.style.display = 'block';
              fillParentInput(finalTranscript);

              btn.textContent = messages.got_it;
              btn.classList.remove('listening');
              isListening = false;
              setTimeout(() => {{
                if (!isListening) btn.textContent = messages.speak;
              }}, 3000);
            }}
          }};

          recognition.onerror = function(event) {{
            isListening = false;
            btn.classList.remove('listening');
            btn.textContent = messages.speak;
            
            if (event.error === 'network') {{
              // If network error occurred with localized BCP-47 tag, retry once with simpler tag if not retried yet
              if (recognition && recognition.lang !== fallbackLang) {{
                statusEl.textContent = '🔄 ' + messages.speech_retry;
                setTimeout(() => {{
                  try {{
                    recognition.lang = fallbackLang;
                    recognition.start();
                    isListening = true;
                    btn.classList.add('listening');
                    btn.textContent = messages.listening;
                    return;
                  }} catch(e) {{}}
                }}, 300);
                return;
              }}
              statusEl.textContent = '⚠️ ' + messages.speech_network_error;
            }} else if (event.error === 'not-allowed') {{
              statusEl.textContent = '⚠️ ' + messages.microphone_denied;
            }} else if (event.error === 'no-speech') {{
              statusEl.textContent = messages.no_speech;
            }} else {{
              statusEl.textContent = messages.voice_error;
            }}
          }};

          recognition.onend = function() {{
            isListening = false;
            btn.classList.remove('listening');
            if (btn.textContent === messages.listening) {{
              btn.textContent = messages.speak;
            }}
          }};

          try {{
            recognition.start();
          }} catch (err) {{
            statusEl.textContent = messages.speech_start_error;
            isListening = false;
            btn.classList.remove('listening');
            btn.textContent = messages.speak;
          }}
        }}
      </script>
    </body>
    </html>
    """

    result = components.html(html_code, height=140)
    return result


def render_tts_player(
    text: str,
    language_code: str = "hi-IN",
    auto_play: bool = False,
    translations: dict | None = None,
) -> None:
    """
    Render a text-to-speech player using the Web Speech Synthesis API.
    Speaks the provided text in the given language.

    Args:
        text:          The text to read aloud.
        language_code: BCP-47 language code.
        auto_play:     If True, starts speaking immediately on render.
    """
    import json
    import re

    # Strip citation brackets like [Source: ..., Pg 1] and markdown stars from spoken audio
    clean_text = re.sub(r'\[(?:Source|Video):[^\]]+\]', '', text)
    clean_text = re.sub(r'[*_#`]', '', clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()

    # Safely JSON serialize text to avoid any unescaped quotes or newlines breaking JS
    safe_text_json = json.dumps(clean_text)
    ui_text = translations or UI_TEXT
    speak_label = f"🔊 {ui_text['listen']}"
    stop_label = f"⏹ {ui_text['stop']}"
    tts_messages_json = json.dumps(
        {
            "unsupported": ui_text["tts_unsupported"],
            "playing": ui_text["playing"],
        },
        ensure_ascii=False,
    )

    auto_js = "speakText();" if auto_play else ""

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ margin: 0; padding: 4px; background: transparent; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        .tts-controls {{ display: flex; gap: 8px; align-items: center; }}
        .tts-btn {{
          padding: 6px 16px;
          border: 1px solid #30363D;
          border-radius: 20px;
          background: #161B22;
          color: #E6EDF3;
          font-size: 13px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
          display: inline-flex;
          align-items: center;
          gap: 6px;
        }}
        .tts-btn:hover {{
          background: #21262D;
          border-color: #58A6FF;
          color: #58A6FF;
        }}
        #tts-status {{
          font-size: 12px;
          color: #8B949E;
        }}
      </style>
    </head>
    <body>
      <div class="tts-controls">
        <button id="playBtn" class="tts-btn" onclick="speakText()">{html.escape(speak_label)}</button>
        <button id="stopBtn" class="tts-btn" onclick="stopText()">{html.escape(stop_label)}</button>
        <span id="tts-status"></span>
      </div>
      <script>
        const rawText = {safe_text_json};
        const lang = '{language_code}';
        const messages = {tts_messages_json};
        const statusEl = document.getElementById('tts-status');

        function speakText() {{
          if (!('speechSynthesis' in window)) {{
            statusEl.textContent = messages.unsupported;
            return;
          }}

          window.speechSynthesis.cancel();

          // Wait a fraction of time for cancellation to process
          setTimeout(() => {{
            const utterance = new SpeechSynthesisUtterance(rawText);
            utterance.lang = lang;
            utterance.rate = 0.95;
            utterance.pitch = 1.0;

            // Pick a matching voice if available
            const voices = window.speechSynthesis.getVoices();
            if (voices && voices.length > 0) {{
              const matched = voices.find(v => v.lang === lang || v.lang.startsWith(lang.split('-')[0]));
              if (matched) utterance.voice = matched;
            }}

            utterance.onstart = function() {{
              statusEl.textContent = '▶️ ' + messages.playing;
            }};
            utterance.onend = function() {{
              statusEl.textContent = '';
            }};
            utterance.onerror = function(e) {{
              statusEl.textContent = '';
              console.log('TTS error:', e);
            }};

            window.speechSynthesis.speak(utterance);
          }}, 50);
        }}

        function stopText() {{
          if ('speechSynthesis' in window) {{
            window.speechSynthesis.cancel();
            statusEl.textContent = '';
          }}
        }}

        // Populate voices asynchronously for Chrome
        if ('speechSynthesis' in window) {{
          window.speechSynthesis.onvoiceschanged = () => {{}};
        }}

        {auto_js}
      </script>
    </body>
    </html>
    """
    components.html(html_code, height=50)
