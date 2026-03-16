import os
import time

from config import SCENE_DELAY, USER_TOPIC, SUGGESTED_TOPICS, CRITIQUE_THRESHOLD, MAX_CRITIQUE_RETRIES
from run_manager import setup_run
from story_generator import (
    init_story_model,
    plan_story,
    generate_story,
    critique_scene,
    regenerate_single_scene,
    _parse_json,
)
from scene_parser import extract_scenes, clean_scene_text
from image_generator import init_image_model, generate_scene_image
from audio_generator import init_tts, generate_scene_audio


def generate_scene_assets(image_model, tts_client, output_dir, scene_number, scene_text, art_style="cartoon illustration"):
    """Generates and saves image + audio for a single scene."""
    image_file = os.path.join(output_dir, f"scene_{scene_number}.png")
    audio_file = os.path.join(output_dir, f"scene_{scene_number}.mp3")

    print("  Generating image...")
    image_saved = generate_scene_image(image_model, scene_text, image_file, art_style)

    print("  Generating narration...")
    generate_scene_audio(tts_client, scene_text, audio_file)

    if image_saved:
        print(f"  Saved scene_{scene_number}.png and scene_{scene_number}.mp3")
    else:
        print(f"  Saved scene_{scene_number}.mp3 (no image generated)")


def main():
    output_dir = setup_run()

    story_model = init_story_model()
    image_model = init_image_model()
    tts_client = init_tts()

    print("\nNeed inspiration? Here are some ideas:")
    for i, suggestion in enumerate(SUGGESTED_TOPICS, 1):
        print(f"  {i}. {suggestion}")

    raw_input = input("\nWhat story should I create? (type your own, enter a number 1-3, or press Enter for random): ").strip()

    if not raw_input:
        import random
        topic = random.choice(SUGGESTED_TOPICS)
        print(f"Using: {topic}")
    elif raw_input.isdigit() and 1 <= int(raw_input) <= len(SUGGESTED_TOPICS):
        topic = SUGGESTED_TOPICS[int(raw_input) - 1]
        print(f"Using: {topic}")
    else:
        topic = raw_input
    print(f"Topic: {topic}")

    # ------------------------------------------------------------------
    # BEHAVIOR 3: Planner decides scene count + structure
    # ------------------------------------------------------------------
    print("\nPlanning story structure...")
    plan = plan_story(story_model, topic)

    print(f"\nPlan: {plan['scene_count']} scenes | Tone: {plan['tone']}")
    print("Scene outline:")
    for i, summary in enumerate(plan["scene_summaries"], 1):
        print(f"  Scene {i}: {summary}")

    # ------------------------------------------------------------------
    # Art style: planner suggestion + user override
    # ------------------------------------------------------------------
    suggested_style = plan.get("art_style", "cartoon illustration")
    print(f"\nSuggested art style: {suggested_style}")
    print("Available styles: cartoon illustration, cinematic photorealistic, watercolor painting, comic book, dark fantasy digital art")
    style_input = input(f"Art style (press Enter to use '{suggested_style}'): ").strip()
    art_style = style_input if style_input else suggested_style
    print(f"Using style: {art_style}")

    # ------------------------------------------------------------------
    # BEHAVIOR 2: User steers before generation
    # ------------------------------------------------------------------
    steering = input("\nAny other steering? (tone, genre changes — or press Enter to skip): ").strip()

    # ------------------------------------------------------------------
    # Generate full story from plan (+ optional steering)
    # ------------------------------------------------------------------
    print("\nGenerating story...")
    story_text = generate_story(story_model, topic, plan, steering or None)
    scenes = extract_scenes(story_text, plan["scene_count"])
    scenes = [clean_scene_text(s) for s in scenes]

    # ------------------------------------------------------------------
    # BEHAVIOR 4: Self-critique — auto-improve weak scenes before assets
    # ------------------------------------------------------------------
    print("\nCritiquing scenes...")
    for i, scene_text in enumerate(scenes):
        retries = 0
        while retries < MAX_CRITIQUE_RETRIES:
            result = critique_scene(story_model, i + 1, scene_text, plan["tone"])
            score = result.get("score", 10)
            if score < CRITIQUE_THRESHOLD and result.get("rewritten"):
                print(f"  Scene {i+1} scored {score}/10 — auto-improving (attempt {retries+1})")
                scenes[i] = clean_scene_text(result["rewritten"])
                scene_text = scenes[i]
                retries += 1
            else:
                print(f"  Scene {i+1} scored {score}/10 — accepted")
                break

    # ------------------------------------------------------------------
    # Show all scenes and ask for confirmation before generating assets
    # ------------------------------------------------------------------
    while True:
        print("\n--- Here are your scenes ---")
        for i, scene_text in enumerate(scenes, start=1):
            print(f"\nScene {i}:")
            print(f"  {scene_text}")

        print("\nOptions:")
        print("  press Enter          — looks good, generate images + audio")
        print("  'redo N <instruction>' — rewrite a specific scene (e.g. 'redo 2 make it sadder')")
        print("  'restart'            — start over with a new topic")

        confirm = input("\nYour choice: ").strip().lower()

        if not confirm:
            break  # user approved, proceed to asset generation

        elif confirm == "restart":
            print("Restarting...")
            main()
            return

        elif confirm.startswith("redo"):
            parts = confirm.split(maxsplit=2)
            if len(parts) < 2 or not parts[1].isdigit():
                print("  Format: 'redo <scene number> <instruction>'  e.g. 'redo 2 make it darker'")
                continue
            scene_idx = int(parts[1]) - 1
            if scene_idx < 0 or scene_idx >= len(scenes):
                print(f"  Scene number must be between 1 and {len(scenes)}")
                continue
            instruction = parts[2] if len(parts) > 2 else "improve this scene"
            print(f"  Rewriting scene {scene_idx + 1}...")
            new_text = regenerate_single_scene(
                story_model, scene_idx + 1, scenes[scene_idx], instruction, plan["tone"]
            )
            scenes[scene_idx] = clean_scene_text(new_text)
            print(f"  Done — scroll up to review all scenes again.")

        else:
            print("  Didn't catch that. Press Enter to approve, or type 'redo N instruction' / 'restart'.")

    # ------------------------------------------------------------------
    # Generate assets for all scenes
    # ------------------------------------------------------------------
    print("\nGenerating assets for all scenes...")
    for i, scene_text in enumerate(scenes, start=1):
        print(f"\nScene {i}:")
        print(f"  {scene_text}")
        generate_scene_assets(image_model, tts_client, output_dir, i, scene_text, art_style)
        if i < len(scenes):
            time.sleep(SCENE_DELAY)

    # ------------------------------------------------------------------
    # BEHAVIOR 1: User feedback loop — selective scene regeneration
    # ------------------------------------------------------------------
    print("\n--- Story complete! ---")
    print("You can now give feedback to regenerate individual scenes.")
    print("Examples: 'redo scene 2 with more tension'  |  'make scene 4 hopeful'  |  type 'done' to finish\n")

    while True:
        feedback = input("Feedback: ").strip()

        if not feedback or feedback.lower() == "done":
            print("Finalizing story. Goodbye!")
            break

        # Ask Gemini to parse which scene and what change
        parse_prompt = f"""
        The user gave this feedback about a {len(scenes)}-scene story: "{feedback}"

        Identify the scene number they want changed and what the change is.
        Respond ONLY in valid JSON with no extra text:
        {{"scene_number": 2, "instruction": "add more tension"}}

        If you cannot determine the scene number, use 1.
        """
        raw = story_model.generate_content(parse_prompt).text
        parsed = _parse_json(raw)

        scene_idx = parsed["scene_number"] - 1
        if scene_idx < 0 or scene_idx >= len(scenes):
            print(f"  Couldn't find that scene. You have {len(scenes)} scenes.")
            continue

        print(f"  Regenerating scene {parsed['scene_number']} with: \"{parsed['instruction']}\"...")
        new_text = regenerate_single_scene(
            story_model,
            parsed["scene_number"],
            scenes[scene_idx],
            parsed["instruction"],
            plan["tone"]
        )
        new_text = clean_scene_text(new_text)
        scenes[scene_idx] = new_text

        print(f"  New scene {parsed['scene_number']}:")
        print(f"  {new_text}")
        print(f"  Regenerating assets...")
        generate_scene_assets(image_model, tts_client, output_dir, parsed["scene_number"], new_text, art_style)
        print(f"  Done! Give more feedback or type 'done'.")


if __name__ == "__main__":
    main()