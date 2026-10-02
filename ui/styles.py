"""
ui/styles.py
─────────────
Custom CSS injected into Streamlit via st.markdown().
Implements the India-flag-inspired saffron/navy dark palette.
"""


def get_global_css() -> str:
    return """
    <style>
    /* ── Google Fonts ─────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Noto+Sans+Devanagari:wght@400;500;600;700&display=swap');

    /* ── Root Variables ──────────────────────────────────────── */
    :root {
      --saffron:    #FF6B00;
      --saffron-lt: #FF8C38;
      --navy:       #0D1117;
      --card-bg:    #161B22;
      --border:     #30363D;
      --text-primary:   #E6EDF3;
      --text-secondary: #8B949E;
      --green:      #3FB950;
      --red:        #F85149;
      --blue:       #58A6FF;
      --gold:       #D29922;
    }

    /* ── Global Reset ─────────────────────────────────────────── */
    html, body, [class*="css"] {
      font-family: 'Inter', 'Noto Sans Devanagari', sans-serif;
      background-color: var(--navy) !important;
      color: var(--text-primary) !important;
    }

    /* ── Scrollbar ────────────────────────────────────────────── */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: var(--navy); }
    ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

    /* ── Hero Section ─────────────────────────────────────────── */
    .hero-container {
      background: linear-gradient(135deg, #0D1117 0%, #1A2332 50%, #0D1117 100%);
      border: 1px solid var(--border);
      border-top: 3px solid var(--saffron);
      border-radius: 16px;
      padding: 32px 28px 24px;
      margin-bottom: 24px;
      position: relative;
      overflow: hidden;
    }
    .hero-container::before {
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 3px;
      background: linear-gradient(90deg, #FF9933, #FFFFFF, #138808);
    }
    .hero-title {
      font-size: 28px;
      font-weight: 700;
      background: linear-gradient(135deg, #FF6B00, #FF8C38);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 6px;
      line-height: 1.3;
    }
    .hero-tagline {
      font-size: 14px;
      color: var(--text-secondary);
      font-weight: 400;
    }
    .hero-badges {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 16px;
    }
    .hero-badge {
      font-size: 11px;
      font-weight: 600;
      padding: 3px 10px;
      border-radius: 20px;
      border: 1px solid;
      letter-spacing: 0.5px;
    }
    .badge-sebi   { color: #3FB950; border-color: #3FB950; background: rgba(63,185,80,0.1); }
    .badge-gemini { color: #58A6FF; border-color: #58A6FF; background: rgba(88,166,255,0.1); }
    .badge-voice  { color: #FF6B00; border-color: #FF6B00; background: rgba(255,107,0,0.1); }

    /* ── Cards ────────────────────────────────────────────────── */
    .card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 16px;
      transition: border-color 0.2s ease;
    }
    .card:hover { border-color: #484F58; }
    .card-header {
      font-size: 13px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: var(--text-secondary);
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    /* ── Answer Card ──────────────────────────────────────────── */
    .answer-card {
      background: linear-gradient(135deg, #0D1F0D 0%, #0F2415 100%);
      border: 1px solid rgba(63, 185, 80, 0.3);
      border-left: 4px solid var(--green);
      border-radius: 12px;
      padding: 20px;
      margin: 16px 0;
    }
    .answer-text {
      font-size: 15px;
      line-height: 1.8;
      color: var(--text-primary);
    }

    /* ── Refusal Card ─────────────────────────────────────────── */
    .refusal-card {
      background: linear-gradient(135deg, #1F0D0D 0%, #241515 100%);
      border: 1px solid rgba(248, 81, 73, 0.3);
      border-left: 4px solid var(--red);
      border-radius: 12px;
      padding: 20px;
      margin: 16px 0;
    }

    /* ── Citation Badges ──────────────────────────────────────── */
    .citations-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }
    .citation-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 11px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 20px;
    }
    .citation-pdf {
      background: rgba(88, 166, 255, 0.15);
      border: 1px solid rgba(88, 166, 255, 0.4);
      color: #58A6FF;
    }
    .citation-video {
      background: rgba(248, 81, 73, 0.12);
      border: 1px solid rgba(248, 81, 73, 0.35);
      color: #FF6B6B;
    }

    /* ── Quiz Card ────────────────────────────────────────────── */
    .quiz-card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-top: 3px solid var(--gold);
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 16px;
    }
    .quiz-question {
      font-size: 16px;
      font-weight: 500;
      color: var(--text-primary);
      line-height: 1.6;
      margin-bottom: 20px;
    }
    .quiz-option-correct {
      border-color: var(--green) !important;
      background: rgba(63, 185, 80, 0.1) !important;
      color: var(--green) !important;
    }
    .quiz-option-wrong {
      border-color: var(--red) !important;
      background: rgba(248, 81, 73, 0.1) !important;
      color: var(--red) !important;
    }

    /* ── Score Badge ──────────────────────────────────────────── */
    .score-badge {
      text-align: center;
      padding: 32px;
      background: linear-gradient(135deg, #1A1A2E 0%, #16213E 100%);
      border: 1px solid var(--gold);
      border-radius: 16px;
      margin: 16px 0;
    }
    .score-emoji { font-size: 64px; line-height: 1.2; }
    .score-title { font-size: 22px; font-weight: 700; color: var(--gold); margin: 8px 0 4px; }
    .score-desc  { font-size: 14px; color: var(--text-secondary); }
    .score-num   { font-size: 40px; font-weight: 700; color: var(--text-primary); margin: 12px 0; }
    .score-sub   { font-size: 12px; color: var(--text-secondary); letter-spacing: 1px; }

    /* ── Safety Footer ────────────────────────────────────────── */
    .safety-footer {
      background: rgba(255, 107, 0, 0.05);
      border: 1px solid rgba(255, 107, 0, 0.2);
      border-radius: 8px;
      padding: 12px 16px;
      font-size: 12px;
      color: var(--text-secondary);
      text-align: center;
      margin-top: 32px;
    }

    /* ── Status Indicator ─────────────────────────────────────── */
    .kb-status {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: var(--text-secondary);
      padding: 8px 0;
    }
    .status-dot {
      width: 8px; height: 8px;
      border-radius: 50%;
      display: inline-block;
    }
    .dot-green  { background: var(--green); box-shadow: 0 0 6px var(--green); }
    .dot-orange { background: var(--saffron); box-shadow: 0 0 6px var(--saffron); }
    .dot-red    { background: var(--red); box-shadow: 0 0 6px var(--red); }

    /* ── Streamlit Overrides ──────────────────────────────────── */
    .stButton > button {
      background: linear-gradient(135deg, var(--saffron), var(--saffron-lt)) !important;
      color: white !important;
      border: none !important;
      border-radius: 8px !important;
      font-weight: 600 !important;
      transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    }
    .stButton > button:hover {
      transform: translateY(-1px) !important;
      box-shadow: 0 4px 15px rgba(255, 107, 0, 0.4) !important;
    }
    .stTextInput > div > div > input {
      background: var(--card-bg) !important;
      border: 1px solid var(--border) !important;
      border-radius: 8px !important;
      color: var(--text-primary) !important;
    }
    .stTextInput > div > div > input:focus {
      border-color: var(--saffron) !important;
      box-shadow: 0 0 0 3px rgba(255, 107, 0, 0.15) !important;
    }
    .stSelectbox > div > div {
      background: var(--card-bg) !important;
      border-color: var(--border) !important;
    }
    .stProgress > div > div > div {
      background: linear-gradient(90deg, var(--saffron), var(--saffron-lt)) !important;
    }
    .stExpander {
      border: 1px solid var(--border) !important;
      border-radius: 8px !important;
      background: var(--card-bg) !important;
    }
    div[data-testid="stSidebar"] {
      background: var(--card-bg) !important;
      border-right: 1px solid var(--border) !important;
    }
    </style>
    """
