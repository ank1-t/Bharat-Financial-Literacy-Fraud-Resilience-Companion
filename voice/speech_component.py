"""
voice/speech_component.py
──────────────────────────
Web Speech API bridge for Streamlit.

Renders a JavaScript-powered voice capture button inside a Streamlit
component iframe. On recognition, the transcript is passed back to
the parent Streamlit app via the Streamlit component value mechanism.

Also provides text-to-speech (TTS) functionality for reading back
LLM answers aloud in Hindi or English.

Note: Web Speech API requires a modern browser (Chrome 33+, Edge 79+).
Firefox has limited support. Safari requires user gesture.
"""

import streamlit.components.v1 as components


def render_voice_input(language_code: str = "hi-IN", key: str = "voice_input") -> str | None:
    """
    Render a voice input button using the Web Speech API.

    The component listens for a single continuous utterance and returns
    the recognized transcript as a string via Streamlit component value.

    Args:
        language_code: BCP-47 code, e.g. "hi-IN" or "en-IN".
        key:           Unique Streamlit component key.

    Returns:
        Recognized transcript string, or None if not yet spoken.
    """
    is_hindi = language_code.startswith("hi")
    btn_label  = "🎤 बोलें (Speak)"     if is_hindi else "🎤 Speak"
    listening  = "🔴 सुन रहा हूँ..."    if is_hindi else "🔴 Listening..."
    done_label = "✅ सुन लिया"          if is_hindi else "✅ Got it!"
    error_msg  = "माइक्रोफ़ोन उपलब्ध नहीं" if is_hindi else "Microphone unavailable"

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {{
          margin: 0;
          padding: 4px;
          font-family: 'Segoe UI', sans-serif;
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
          margin-top: 8px;
          font-size: 12px;
          color: #8B949E;
          text-align: center;
        }}
        #transcript-display {{
          margin-top: 8px;
          font-size: 13px;
          color: #58A6FF;
          text-align: center;
          font-style: italic;
          min-height: 18px;
        }}
      </style>
    </head>
    <body>
      <button id="voiceBtn" onclick="startVoice()">{btn_label}</button>
      <div id="status"></div>
      <div id="transcript-display"></div>

      <script>
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const btn = document.getElementById('voiceBtn');
        const statusEl = document.getElementById('status');
        const transcriptEl = document.getElementById('transcript-display');

        if (!SpeechRecognition) {{
          btn.textContent = '❌ {error_msg}';
          btn.disabled = true;
          btn.style.background = '#444';
          btn.style.borderColor = '#444';
          statusEl.textContent = 'Please use Chrome or Edge browser.';
        }}

        let recognition;

        function startVoice() {{
          recognition = new SpeechRecognition();
          recognition.lang = '{language_code}';
          recognition.interimResults = true;
          recognition.maxAlternatives = 1;
          recognition.continuous = false;

          btn.textContent = '{listening}';
          btn.classList.add('listening');
          statusEl.textContent = '';
          transcriptEl.textContent = '';

          recognition.onresult = function(event) {{
            let interimTranscript = '';
            let finalTranscript   = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {{
              const t = event.results[i][0].transcript;
              if (event.results[i].isFinal) {{
                finalTranscript += t;
              }} else {{
                interimTranscript += t;
              }}
            }}

            transcriptEl.textContent = finalTranscript || interimTranscript;

            if (finalTranscript) {{
              // Send to Streamlit parent
              window.parent.postMessage({{
                isStreamlitMessage: true,
                type: 'streamlit:setComponentValue',
                value: finalTranscript
              }}, '*');
              btn.textContent = '{done_label}';
              btn.classList.remove('listening');
              setTimeout(() => {{
                btn.textContent = '{btn_label}';
              }}, 2000);
            }}
          }};

          recognition.onerror = function(event) {{
            btn.classList.remove('listening');
            btn.textContent = '{btn_label}';
            statusEl.textContent = 'Error: ' + event.error + '. Please try again.';
          }};

          recognition.onend = function() {{
            btn.classList.remove('listening');
            if (btn.textContent === '{listening}') {{
              btn.textContent = '{btn_label}';
            }}
          }};

          recognition.start();
        }}
      </script>
    </body>
    </html>
    """

    result = components.html(html_code, height=120)
    return result


def render_tts_player(text: str, language_code: str = "hi-IN", auto_play: bool = False) -> None:
    """
    Render a text-to-speech player using the Web Speech Synthesis API.
    Speaks the provided text in the given language.

    Args:
        text:          The text to read aloud.
        language_code: BCP-47 language code.
        auto_play:     If True, starts speaking immediately on render.
    """
    # Escape text for JS string safety
    safe_text = text.replace("'", "\\'").replace("\n", " ").replace('"', '\\"')
    is_hindi = language_code.startswith("hi")

    speak_label = "🔊 सुनें" if is_hindi else "🔊 Listen"
    stop_label  = "⏹ रोकें"  if is_hindi else "⏹ Stop"

    auto_js = "speakText();" if auto_play else ""

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {{ margin: 0; padding: 4px; background: transparent; font-family: 'Segoe UI', sans-serif; }}
        .tts-controls {{ display: flex; gap: 8px; }}
        .tts-btn {{
          padding: 6px 16px;
          border: 1px solid #30363D;
          border-radius: 20px;
          background: #161B22;
          color: #E6EDF3;
          font-size: 13px;
          cursor: pointer;
          transition: background 0.2s;
        }}
        .tts-btn:hover {{ background: #21262D; }}
      </style>
    </head>
    <body>
      <div class="tts-controls">
        <button class="tts-btn" onclick="speakText()">{speak_label}</button>
        <button class="tts-btn" onclick="stopText()">{stop_label}</button>
      </div>
      <script>
        const utterance = new SpeechSynthesisUtterance("{safe_text}");
        utterance.lang = '{language_code}';
        utterance.rate = 0.9;
        utterance.pitch = 1.0;

        function speakText() {{
          window.speechSynthesis.cancel();
          window.speechSynthesis.speak(utterance);
        }}

        function stopText() {{
          window.speechSynthesis.cancel();
        }}

        {auto_js}
      </script>
    </body>
    </html>
    """
    components.html(html_code, height=50)
