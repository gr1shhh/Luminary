import re


def extract_scenes(story_text, scene_count):
    """
    Extracts scenes from story text.
    scene_count is provided by the planner so we don't hardcap at 4.
    """
    scenes = re.findall(
        r"Scene\s\d+:\s*(.*?)(?=Scene\s\d+:|$)",
        story_text,
        re.DOTALL
    )
    return scenes[:scene_count]


def clean_scene_text(text):
    text = re.sub(r"\*\(Illustration:.*?\)\*", "", text, flags=re.DOTALL)
    text = text.replace("*", "")
    return text.strip()