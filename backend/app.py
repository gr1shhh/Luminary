import streamlit as st
from config import SUGGESTED_TOPICS

st.set_page_config(
    page_title="Luminary",
    page_icon="✦",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ============================================================
# CSS
# ============================================================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300&family=Syne:wght@400;500;600&display=swap');

/* ── Reset & Base ── */
* { box-sizing: border-box; }

/* ── Background ── */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.block-container,
.stApp { background: #0a0a0a !important; }

/* ── Layout ── */
.block-container {
    max-width: 780px !important;
    padding: 0 24px 60px !important;
}
[data-testid="stHorizontalBlock"] {
    gap: 8px !important;
    align-items: center !important;
}
[data-testid="stHorizontalBlock"] > div {
    margin-bottom: 0 !important;
    padding-bottom: 0 !important;
}
[data-testid="stTextInput"] {
    margin-bottom: 0 !important;
    padding-bottom: 0 !important;
}
div[data-testid="stAppViewBlockContainer"] {
    padding-top: 0 !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu                        { display: none !important; }
footer                           { display: none !important; }
header                           { display: none !important; }
[data-testid="stToolbar"]        { display: none !important; }
[data-testid="stDecoration"]     { display: none !important; }
[data-testid="stHeader"]         { display: none !important; }
[data-testid="stSeparator"]      { display: none !important; }
[data-testid="stSidebar"]        { display: none !important; }
.stApp > header                  { display: none !important; }
hr                               { display: none !important; }

/* ── Hero ── */
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
.hero-title span {
    font-style: italic;
    color: #c9a96e;
}
.hero-sub {
    font-family: 'Cormorant Garamond', serif;
    font-size: 17px;
    font-style: italic;
    color: #555;
    margin-top: 10px;
}

/* ── Input ── */
[data-testid="stTextInput"] input {
    background: #111 !important;
    border: 1px solid #252525 !important;
    border-radius: 8px !important;
    color: #f5f0e8 !important;
    font-family: 'Cormorant Garamond', serif !important;
    font-size: 20px !important;
    padding: 18px 20px !important;
    caret-color: #c9a96e;
    transition: border-color 0.2s;
    box-shadow: none !important;
    width: 100% !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #c9a96e !important;
    box-shadow: none !important;
    outline: none !important;
}
[data-testid="stTextInput"] input::placeholder {
    color: #2a2a2a !important;
}

/* ── Submit arrow ── */
.submit-btn > button {
    background: #c9a96e !important;
    border: none !important;
    border-radius: 8px !important;
    color: #0a0a0a !important;
    font-size: 18px !important;
    font-weight: 700 !important;
    padding: 0 16px !important;
    min-height: 59px !important;
    height: 59px !important;
    width: 100% !important;
    line-height: 1 !important;
    letter-spacing: 0 !important;
    text-transform: none !important;
    transition: opacity 0.15s !important;
    cursor: pointer !important;
    border-top-left-radius: 8px !important;
    border-top-right-radius: 8px !important;
    border-bottom-left-radius: 8px !important;
    border-bottom-right-radius: 8px !important;
}
.submit-btn > button:hover {
    opacity: 0.82 !important;
}

/* ── Chips ── */
.stButton > button {
    background: #0f0f0f !important;
    border: 1px solid #1e1e1e !important;
    border-radius: 100px !important;
    color: #555 !important;
    font-family: 'Cormorant Garamond', serif !important;
    font-size: 14px !important;
    font-style: italic !important;
    font-weight: 400 !important;
    letter-spacing: 0 !important;
    text-transform: none !important;
    padding: 10px 24px !important;
    width: 100% !important;
    transition: all 0.15s !important;
    margin-bottom: 6px !important;
    text-align: center !important;
}
.stButton > button:hover {
    border-color: #c9a96e !important;
    color: #c9a96e !important;
    opacity: 1 !important;
}

/* ── Force rectangular submit button ── */
div.submit-btn button,
div.submit-btn > button,
section div.submit-btn button {
    border-radius: 8px !important;
    -webkit-border-radius: 8px !important;
    -moz-border-radius: 8px !important;
}

/* ── Approve button ── */
div[data-testid="stButton"] > button[kind="primary"],
div[data-testid="stButton"]:has(#approve_btn) > button {
    background: #c9a96e !important;
    color: #0a0a0a !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Syne', sans-serif !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.2em !important;
    text-transform: uppercase !important;
    padding: 14px !important;
    transition: opacity 0.15s !important;
}

/* ── Restart button ── */
div[data-testid="stButton"]:has(#restart_btn) > button {
    background: transparent !important;
    color: #444 !important;
    border: 1px solid #1e1e1e !important;
    border-radius: 8px !important;
    font-family: 'Syne', sans-serif !important;
    font-size: 11px !important;
    letter-spacing: 0.2em !important;
    text-transform: uppercase !important;
    padding: 14px !important;
    transition: all 0.15s !important;
}
div[data-testid="stButton"]:has(#restart_btn) > button:hover {
    border-color: #444 !important;
    color: #888 !important;
}

/* ── Suggestions label ── */
.suggestions-label {
    text-align: center;
    font-family: 'Syne', sans-serif;
    font-size: 10px;
    letter-spacing: 0.28em;
    color: #2e2e2e;
    text-transform: uppercase;
    margin: 24px 0 16px;
}
</style>
"""

# ============================================================
# HTML blocks
# ============================================================
HTML_HERO = """
<div class="hero">
    <div class="hero-eyebrow">AI Story Engine</div>
    <div class="hero-title">Lumi<span>nary</span></div>
    <div class="hero-sub">Turn any idea into a cinematic story</div>
</div>
"""

HTML_SUGGESTIONS_LABEL = """
<div class="suggestions-label">or try one of these</div>
"""

# ============================================================
# Session state
# ============================================================
if "topic" not in st.session_state:
    st.session_state.topic = ""
if "screen" not in st.session_state:
    st.session_state.screen = "landing"

def start_story(topic):
    st.session_state.topic = topic
    st.session_state.screen = "generating"

# ============================================================
# Render
# ============================================================
st.markdown(CSS, unsafe_allow_html=True)
st.markdown(HTML_HERO, unsafe_allow_html=True)

# Input + arrow button as one unified row
col_input, col_btn = st.columns([11, 1])
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

# Trigger on arrow click
if submit and topic_input:
    start_story(topic_input)
    st.rerun()

# Suggestion chips
st.markdown(HTML_SUGGESTIONS_LABEL, unsafe_allow_html=True)
for i, suggestion in enumerate(SUGGESTED_TOPICS):
    col1, col2, col3 = st.columns([0.5, 3, 0.5])
    with col2:
        if st.button(suggestion, key=f"chip_{i}", use_container_width=True):
            start_story(suggestion)
            st.rerun()

# ============================================================
# SCREEN 2 — Generation + Scene Review
# ============================================================
def screen_generating():
    from run_manager import setup_run
    from story_generator import init_story_model, plan_story, generate_story, critique_scene, regenerate_single_scene, _parse_json
    from scene_parser import extract_scenes, clean_scene_text
    from image_generator import init_image_model, generate_scene_image
    from audio_generator import init_tts, generate_scene_audio
    from config import CRITIQUE_THRESHOLD, MAX_CRITIQUE_RETRIES, SCENE_DELAY
    import os, time

    topic = st.session_state.topic

    # ── Header ──
    st.markdown(f"""
    <div style="text-align:center; padding: 48px 0 32px;">
        <div style="font-family:'Syne',sans-serif; font-size:10px; letter-spacing:0.3em; color:#c9a96e; text-transform:uppercase; margin-bottom:12px;">Creating your story</div>
        <div style="font-family:'Cormorant Garamond',serif; font-size:28px; font-weight:300; color:#f5f0e8; font-style:italic;">"{topic}"</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Only run generation once ──
    if "plan" not in st.session_state:
        story_model = init_story_model()

        status = st.empty()

        status.markdown("<p style='text-align:center; font-family:Syne,sans-serif; font-size:11px; letter-spacing:0.2em; color:#555; text-transform:uppercase;'>Planning story structure...</p>", unsafe_allow_html=True)
        plan = plan_story(story_model, topic)
        st.session_state.plan = plan
        st.session_state.story_model = story_model

        status.markdown("<p style='text-align:center; font-family:Syne,sans-serif; font-size:11px; letter-spacing:0.2em; color:#555; text-transform:uppercase;'>Generating scenes...</p>", unsafe_allow_html=True)
        story_text = generate_story(story_model, topic, plan)
        scenes = extract_scenes(story_text, plan["scene_count"])
        scenes = [clean_scene_text(s) for s in scenes]

        status.markdown("<p style='text-align:center; font-family:Syne,sans-serif; font-size:11px; letter-spacing:0.2em; color:#555; text-transform:uppercase;'>Critiquing and refining...</p>", unsafe_allow_html=True)
        for i, scene_text in enumerate(scenes):
            retries = 0
            while retries < MAX_CRITIQUE_RETRIES:
                result = critique_scene(story_model, i + 1, scene_text, plan["tone"])
                score = result.get("score", 10)
                if score < CRITIQUE_THRESHOLD and result.get("rewritten"):
                    scenes[i] = clean_scene_text(result["rewritten"])
                    scene_text = scenes[i]
                    retries += 1
                else:
                    break

        st.session_state.scenes = scenes
        st.session_state.art_style = plan.get("art_style", "cartoon illustration")
        status.empty()

    plan = st.session_state.plan
    scenes = st.session_state.scenes
    story_model = st.session_state.story_model

    # ── Plan summary ──
    st.markdown(f"""
    <div style="display:flex; gap:24px; justify-content:center; margin-bottom:32px;">
        <div style="font-family:'Syne',sans-serif; font-size:10px; letter-spacing:0.2em; color:#444; text-transform:uppercase;">{plan['scene_count']} scenes</div>
        <div style="font-family:'Syne',sans-serif; font-size:10px; letter-spacing:0.2em; color:#444; text-transform:uppercase;">·</div>
        <div style="font-family:'Syne',sans-serif; font-size:10px; letter-spacing:0.2em; color:#444; text-transform:uppercase;">{plan['tone']}</div>
        <div style="font-family:'Syne',sans-serif; font-size:10px; letter-spacing:0.2em; color:#444; text-transform:uppercase;">·</div>
        <div style="font-family:'Syne',sans-serif; font-size:10px; letter-spacing:0.2em; color:#c9a96e; text-transform:uppercase;">{plan.get('art_style','')}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Scene review ──
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    for i, scene_text in enumerate(scenes):
        st.markdown(f"""
        <div style="border:1px solid #1e1e1e; border-radius:8px; padding:24px 28px; margin-bottom:12px; background:#0f0f0f;">
            <div style="font-family:'Syne',sans-serif; font-size:10px; letter-spacing:0.25em; color:#c9a96e; text-transform:uppercase; margin-bottom:12px;">Scene {i+1}</div>
            <div style="font-family:'Cormorant Garamond',serif; font-size:17px; color:#888; font-style:italic; line-height:1.7;">{scene_text}</div>
        </div>
        """, unsafe_allow_html=True)

        redo_input = st.text_input(
            label=f"redo_{i}",
            label_visibility="collapsed",
            placeholder=f"Rewrite scene {i+1} with a different direction... (or leave empty)",
            key=f"redo_input_{i}"
        )
        if redo_input:
            if st.button(f"Rewrite scene {i+1}", key=f"redo_btn_{i}"):
                with st.spinner(f"Rewriting scene {i+1}..."):
                    new_text = regenerate_single_scene(story_model, i+1, scenes[i], redo_input, plan["tone"])
                    st.session_state.scenes[i] = clean_scene_text(new_text)
                st.rerun()

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── Action buttons ──
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("✦  Approve — generate images & audio", key="approve_btn", use_container_width=True):
            st.session_state.screen = "assets"
            st.rerun()
    with col2:
        if st.button("Restart", key="restart_btn", use_container_width=True):
            for key in ["plan", "scenes", "story_model", "art_style", "topic"]:
                st.session_state.pop(key, None)
            st.session_state.screen = "landing"
            st.rerun()


# Route to next screen
if st.session_state.screen == "generating":
    screen_generating()