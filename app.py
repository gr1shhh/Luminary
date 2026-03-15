import streamlit as st
from config import SUGGESTED_TOPICS

st.set_page_config(
    page_title="Luminary",
    page_icon="✦",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300&family=Syne:wght@400;500;600&display=swap');

* { box-sizing: border-box; }

html, body, [data-testid="stAppViewContainer"],
[data-testid="stMain"], .block-container {
    background: #0a0a0a !important;
}
.block-container {
    max-width: 620px !important;
    padding: 0 24px 60px !important;
}
#MainMenu, footer, header, [data-testid="stToolbar"] { display: none !important; }

/* Hero */
.hero {
    text-align: center;
    padding: 64px 0 44px;
}
.hero-eyebrow {
    font-family: 'Syne', sans-serif;
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.35em;
    color: #c9a96e;
    text-transform: uppercase;
    margin-bottom: 16px;
}
.hero-title {
    font-family: 'Cormorant Garamond', serif;
    font-size: 68px;
    font-weight: 300;
    color: #f5f0e8;
    line-height: 1;
    letter-spacing: -0.02em;
}
.hero-title span { font-style: italic; color: #c9a96e; }
.hero-sub {
    font-family: 'Cormorant Garamond', serif;
    font-size: 17px;
    font-style: italic;
    color: #555;
    margin-top: 10px;
}

/* Input row — text input + submit icon side by side */
.input-row {
    display: flex;
    align-items: stretch;
    gap: 0;
    border: 1px solid #252525;
    border-radius: 6px;
    overflow: hidden;
    transition: border-color 0.2s;
    background: #111;
}
.input-row:focus-within {
    border-color: #c9a96e;
}

[data-testid="stTextInput"] {
    flex: 1 !important;
}
[data-testid="stTextInput"] input {
    background: #111 !important;
    border: none !important;
    border-radius: 0 !important;
    color: #f5f0e8 !important;
    font-family: 'Cormorant Garamond', serif !important;
    font-size: 20px !important;
    padding: 16px 20px !important;
    caret-color: #c9a96e;
    box-shadow: none !important;
    outline: none !important;
}
[data-testid="stTextInput"] input::placeholder { color: #2a2a2a !important; }
[data-testid="stTextInput"] input:focus {
    box-shadow: none !important;
    border: none !important;
}

/* Submit arrow button */
.submit-btn > button {
    background: #c9a96e !important;
    border: none !important;
    border-radius: 0 !important;
    color: #0a0a0a !important;
    font-size: 18px !important;
    font-weight: 600 !important;
    padding: 0 20px !important;
    height: 100% !important;
    min-height: 56px !important;
    letter-spacing: 0 !important;
    text-transform: none !important;
    width: auto !important;
    transition: opacity 0.15s !important;
    cursor: pointer !important;
}
.submit-btn > button:hover { opacity: 0.82 !important; }

/* Divider */
.divider {
    display: flex;
    align-items: center;
    gap: 14px;
    margin: 24px 0 18px;
}
.divider-line { flex: 1; height: 1px; background: #1a1a1a; }
.divider-text {
    font-family: 'Syne', sans-serif;
    font-size: 10px;
    letter-spacing: 0.28em;
    color: #2e2e2e;
    text-transform: uppercase;
    white-space: nowrap;
}

/* Chips */
[data-testid="stHorizontalBlock"] .stButton > button {
    background: #0f0f0f !important;
    border: 1px solid #1e1e1e !important;
    border-radius: 100px !important;
    color: #555 !important;
    font-family: 'Cormorant Garamond', serif !important;
    font-size: 13px !important;
    font-style: italic !important;
    font-weight: 400 !important;
    letter-spacing: 0 !important;
    text-transform: none !important;
    padding: 6px 16px !important;
    width: auto !important;
    transition: all 0.15s !important;
    white-space: nowrap !important;
}
[data-testid="stHorizontalBlock"] .stButton > button:hover {
    border-color: #c9a96e !important;
    color: #c9a96e !important;
    opacity: 1 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Session state ──
if "topic" not in st.session_state:
    st.session_state.topic = ""
if "screen" not in st.session_state:
    st.session_state.screen = "landing"

def start_story(topic):
    st.session_state.topic = topic
    st.session_state.screen = "generating"

# ── Hero ──
st.markdown("""
<div class="hero">
    <div class="hero-eyebrow">AI Story Engine</div>
    <div class="hero-title">Lumi<span>nary</span></div>
    <div class="hero-sub">Turn any idea into a cinematic story</div>
</div>
""", unsafe_allow_html=True)

# ── Input + arrow button in one row ──
st.markdown('<div class="input-row">', unsafe_allow_html=True)
col_input, col_btn = st.columns([10, 1])
with col_input:
    topic_input = st.text_input(
        label="topic",
        label_visibility="collapsed",
        placeholder="Describe a moment, a person, a world...",
        key="topic_input_field"
    )
with col_btn:
    st.markdown('<div class="submit-btn">', unsafe_allow_html=True)
    submit = st.button("↑", key="submit_arrow")
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Trigger from arrow button or Enter (topic_input changes)
if submit and topic_input:
    start_story(topic_input)
    st.rerun()
elif topic_input and topic_input != st.session_state.get("last_input", ""):
    st.session_state["last_input"] = topic_input
    # Don't auto-start on every keystroke — only on Enter
    # Streamlit fires on Enter so this is fine

# ── Chips ──
st.markdown("""
<div class="divider">
    <div class="divider-line"></div>
    <div class="divider-text">or try one of these</div>
    <div class="divider-line"></div>
</div>
""", unsafe_allow_html=True)

cols = st.columns(len(SUGGESTED_TOPICS))
for i, suggestion in enumerate(SUGGESTED_TOPICS):
    with cols[i]:
        if st.button(suggestion, key=f"chip_{i}"):
            start_story(suggestion)
            st.rerun()

# ── Route to next screen ──
if st.session_state.screen == "generating":
    st.rerun()