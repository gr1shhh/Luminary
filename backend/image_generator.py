from vertexai.preview.vision_models import ImageGenerationModel
from config import IMAGE_MODEL_NAME


def init_image_model():
    return ImageGenerationModel.from_pretrained(IMAGE_MODEL_NAME)


def _build_image_prompt(scene_text, art_style, story_client, character_descriptions=""):
    """Ask Gemini to write only the scene composition, then prepend character descriptions."""
    try:
        char_note = f"\n\nCharacters in this story (keep these consistent):\n{character_descriptions}" if character_descriptions else ""

        prompt = f"""You are a cinematographer writing image generation prompts for Imagen.

        Convert this scene into a visual image prompt. Focus on:
        - The PRIMARY location and environment (indoor/outdoor, time of day)
        - Key objects and atmosphere
        - Camera angle and lighting
        - Do NOT focus on abstract emotions
        - Do NOT mention consoles, screens, or equipment unless they are central to the scene
        - Keep it under 50 words
        - End with: {art_style}{char_note}

        Scene: {scene_text}

        Respond with ONLY the image prompt, nothing else."""

        response = story_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        scene_composition = response.text.strip()

        # Prepend character descriptions verbatim if available
        if character_descriptions:
            full_prompt = f"{character_descriptions}. {scene_composition}, {art_style}"
        else:
            full_prompt = f"{scene_composition}, {art_style}"

        return full_prompt

    except Exception as e:
        print(f"  Warning: prompt conversion failed ({e}), using fallback.")
        first_sentence = scene_text.split(".")[0].strip()
        return f"{first_sentence}, {art_style}, cinematic lighting"


def generate_scene_image(model, scene_text, filename, art_style="cartoon illustration", story_client=None, character_descriptions=""):
    # Build image prompt using Gemini if client is available
    if story_client:
        image_prompt = _build_image_prompt(scene_text, art_style, story_client, character_descriptions)
    else:
        first_sentence = scene_text.split(".")[0].strip()
        image_prompt = f"{first_sentence}, {art_style}, cinematic lighting"

    print(f"  Image prompt: {image_prompt[:150]}...")

    try:
        response = model.generate_images(
            prompt=image_prompt,
            number_of_images=1,
        )

        images = response.images

        if not images:
            print(f"  Warning: image filtered, retrying with safer prompt...")
            fallback_prompt = f"Dramatic cinematic scene, {art_style}, atmospheric lighting, no characters"
            response = model.generate_images(
                prompt=fallback_prompt,
                number_of_images=1,
            )
            images = response.images

        if images:
            images[0].save(filename)
            return True
        else:
            print(f"  Warning: image could not be generated, skipping.")
            return False

    except Exception as e:
        print(f"  Warning: image generation failed ({e}), skipping.")
        return False