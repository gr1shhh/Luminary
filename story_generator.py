import json
import re
from google import genai
from config import PROJECT_ID, LOCATION, STORY_MODEL_NAME, MIN_SCENES, MAX_SCENES


def init_story_model():
    """
    Uses Google Gen AI SDK with Vertex AI backend.
    No API key needed — uses existing gcloud ADC credentials.
    """
    client = genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location=LOCATION,
    )
    return client


def _parse_json(text):
    """
    Robustly extracts and parses JSON from a Gemini response.
    Handles markdown code fences, trailing comments, and extra whitespace.
    """
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in response:\n{text}")
    return json.loads(match.group())


def _generate(client, prompt):
    """Single helper to call Gemini via Gen AI SDK."""
    response = client.models.generate_content(
        model=STORY_MODEL_NAME,
        contents=prompt
    )
    return response.text


def plan_story(client, topic):
    """
    Behavior 3: Agent decides scene count + structure based on topic complexity.
    Returns a plan dict: { scene_count, tone, art_style, scene_summaries }
    """
    prompt = f"""
    You are a creative director planning a cinematic story.
    The user wants a story about: "{topic}"

    Analyze the emotional and narrative complexity, then decide:
    - How many scenes are needed (between {MIN_SCENES} and {MAX_SCENES})
    - The overall tone
    - A one-line summary for each scene

    Also pick the most fitting image art style from this list:
    - "cartoon illustration"
    - "cinematic photorealistic"
    - "watercolor painting"
    - "comic book"
    - "dark fantasy digital art"

    Respond ONLY in valid JSON with no extra text or markdown:
    {{
    "scene_count": 4,
    "tone": "tense and triumphant",
    "art_style": "cinematic photorealistic",
    "scene_summaries": [
        "Scene 1 summary",
        "Scene 2 summary",
        "Scene 3 summary",
        "Scene 4 summary"
    ]
    }}
    """
    return _parse_json(_generate(client, prompt))


def generate_story(client, topic, plan, steering=None):
    """
    Behavior 2: Generates the full story using the plan.
    Accepts optional steering instructions from the user.
    """
    summaries_text = "\n".join(
        f"Scene {i+1}: {s}" for i, s in enumerate(plan["scene_summaries"])
    )
    steering_note = f"\n\nDirector's note (apply to whole story): {steering}" if steering else ""

    prompt = f"""
    You are writing a cinematic short story about: "{topic}"

    Tone: {plan["tone"]}
    Number of scenes: {plan["scene_count"]}

    Follow this scene-by-scene outline:
    {summaries_text}
    {steering_note}

    Rules:
    - Each scene must be exactly 3 sentences long.
    - Do NOT include illustration descriptions.
    - Do NOT include markdown formatting such as * or **.
    - Only write narration text.

    Format EXACTLY like this:

    Scene 1:
    <scene text>

    Scene 2:
    <scene text>

    ... and so on for all {plan["scene_count"]} scenes.
    """
    return _generate(client, prompt)


def regenerate_single_scene(client, scene_number, original_text, instruction, tone):
    """
    Behavior 1: Regenerates a single scene based on user feedback.
    """
    prompt = f"""
    Rewrite Scene {scene_number} of a cinematic story with tone "{tone}".

    User instruction: {instruction}

    Original scene:
    {original_text}

    Rules:
    - Keep it exactly 3 sentences long.
    - Do NOT include markdown formatting such as * or **.
    - Only write narration text.
    - Apply the user's instruction while keeping the story coherent.

    Respond with ONLY the rewritten scene text, nothing else.
    """
    return _generate(client, prompt).strip()


def critique_scene(client, scene_number, scene_text, tone):
    """
    Behavior 4: Self-critique. Scores the scene and rewrites if below threshold.
    Returns { score, rewritten } where rewritten is None if score is acceptable.
    """
    prompt = f"""
    You are a harsh but fair cinematic story editor.
    Rate this scene from a story with tone "{tone}".

    Scene {scene_number}:
    {scene_text}

    Score it 1-10 on overall quality (vividness, emotional impact, coherence).
    If score is below 7, rewrite it to be better.

    Respond ONLY in valid JSON with no extra text or markdown:
    {{
    "score": 8,
    "rewritten": null
    }}

    If rewriting, put the improved 3-sentence text in "rewritten". Otherwise keep "rewritten" as null.
    """
    return _parse_json(_generate(client, prompt))