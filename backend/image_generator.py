from vertexai.preview.vision_models import ImageGenerationModel
from config import IMAGE_MODEL_NAME


def init_image_model():
    return ImageGenerationModel.from_pretrained(IMAGE_MODEL_NAME)


def generate_scene_image(model, scene_text, filename, art_style="cartoon illustration"):
    # Use only the first sentence to reduce chance of content filter
    first_sentence = scene_text.split(".")[0].strip()
    prompt = f"{first_sentence}, {art_style}, cinematic lighting"

    try:
        response = model.generate_images(
            prompt=prompt,
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