import os
import base64
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json

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
from run_manager import setup_run
from config import CRITIQUE_THRESHOLD, MAX_CRITIQUE_RETRIES, SCENE_DELAY

import time

app = FastAPI(title="Luminary API")

# Serve sample assets for mock/demo mode
import os as _os
_sample_dir = _os.path.join(_os.path.dirname(__file__), "sample")
if _os.path.exists(_sample_dir):
    app.mount("/sample", StaticFiles(directory=_sample_dir), name="sample")

# Global lock — ensures only one Imagen call runs at a time (rate limit: 1/min)
imagen_lock = asyncio.Lock()
last_imagen_time = 0.0

# ── CORS — allow Vercel frontend ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten to your Vercel URL after deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Initialize models once on startup ──
story_model = None
image_model = None
tts_client = None

@app.on_event("startup")
def startup():
    global story_model, image_model, tts_client
    story_model = init_story_model()
    image_model = init_image_model()
    tts_client = init_tts()
    print("Models initialized")


# ============================================================
# Request / Response models
# ============================================================

class PlanRequest(BaseModel):
    topic: str

class StoryRequest(BaseModel):
    topic: str
    plan: dict
    steering: Optional[str] = None

class CritiqueRequest(BaseModel):
    scene_number: int
    scene_text: str
    tone: str

class RegenerateRequest(BaseModel):
    scene_number: int
    original_text: str
    instruction: str
    tone: str

class GenerateAssetsRequest(BaseModel):
    scenes: list[str]
    art_style: str


# ============================================================
# Endpoints
# ============================================================

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/plan")
def plan(req: PlanRequest):
    """Step 1 — Planner decides scene count, tone, art style."""
    try:
        plan = plan_story(story_model, req.topic)
        return plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/story")
def story(req: StoryRequest):
    """Step 2 — Generate full story text from plan."""
    try:
        story_text = generate_story(story_model, req.topic, req.plan, req.steering)
        scenes = extract_scenes(story_text, req.plan["scene_count"])
        scenes = [clean_scene_text(s) for s in scenes]
        return {"scenes": scenes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/critique")
def critique(req: CritiqueRequest):
    """Step 3 — Critique a single scene, auto-rewrite if weak."""
    try:
        result = critique_scene(story_model, req.scene_number, req.scene_text, req.tone)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/regenerate")
def regenerate(req: RegenerateRequest):
    """Regenerate a single scene based on user feedback."""
    try:
        new_text = regenerate_single_scene(
            story_model,
            req.scene_number,
            req.original_text,
            req.instruction,
            req.tone
        )
        return {"scene_text": clean_scene_text(new_text)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-assets")
def generate_assets(req: GenerateAssetsRequest):
    """
    Generate images + audio for all scenes.
    Returns base64 encoded image and audio per scene.
    """
    output_dir = setup_run()
    results = []

    for i, scene_text in enumerate(req.scenes, start=1):
        image_file = os.path.join(output_dir, f"scene_{i}.png")
        audio_file = os.path.join(output_dir, f"scene_{i}.mp3")

        # Generate image
        image_saved = generate_scene_image(
            image_model, scene_text, image_file, req.art_style
        )

        # Generate audio
        generate_scene_audio(tts_client, scene_text, audio_file)

        # Read files and encode as base64
        image_b64 = None
        if image_saved and os.path.exists(image_file):
            with open(image_file, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")

        audio_b64 = None
        if os.path.exists(audio_file):
            with open(audio_file, "rb") as f:
                audio_b64 = base64.b64encode(f.read()).decode("utf-8")

        results.append({
            "scene_number": i,
            "scene_text": scene_text,
            "image_b64": image_b64,
            "audio_b64": audio_b64,
        })

        # Rate limit delay between scenes (skip after last scene)
        if i < len(req.scenes):
            time.sleep(SCENE_DELAY)

    return {"scenes": results}


@app.post("/generate-assets/stream")
async def generate_assets_stream(req: GenerateAssetsRequest):
    """
    Streaming version — sends each scene as it's generated
    so the frontend can show progress in real time.
    """
    output_dir = setup_run()

    async def event_generator():
        for i, scene_text in enumerate(req.scenes, start=1):
            # Notify frontend this scene is starting
            yield f"data: {json.dumps({'type': 'progress', 'scene': i, 'total': len(req.scenes), 'status': 'generating'})}\n\n"

            image_file = os.path.join(output_dir, f"scene_{i}.png")
            audio_file = os.path.join(output_dir, f"scene_{i}.mp3")

            # Run blocking calls in thread pool
            loop = asyncio.get_event_loop()

            # Audio first — fast, no rate limit
            await loop.run_in_executor(
                None, generate_scene_audio, tts_client, scene_text, audio_file
            )

            # Imagen — use global lock to prevent concurrent calls
            async with imagen_lock:
                global last_imagen_time
                elapsed = time.time() - last_imagen_time
                if elapsed < SCENE_DELAY:
                    wait = SCENE_DELAY - elapsed
                    print(f"  Waiting {wait:.1f}s before Imagen call for scene {i}...")
                    await asyncio.sleep(wait)
                image_saved = await loop.run_in_executor(
                    None, generate_scene_image, image_model, scene_text, image_file, req.art_style
                )
                last_imagen_time = time.time()

            image_b64 = None
            if image_saved and os.path.exists(image_file):
                with open(image_file, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode("utf-8")

            audio_b64 = None
            if os.path.exists(audio_file):
                with open(audio_file, "rb") as f:
                    audio_b64 = base64.b64encode(f.read()).decode("utf-8")

            # Send completed scene to frontend
            yield f"data: {json.dumps({'type': 'scene', 'scene_number': i, 'scene_text': scene_text, 'image_b64': image_b64, 'audio_b64': audio_b64})}\n\n"

            # Delay now handled by imagen_lock

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


# ============================================================
# New request models
# ============================================================

class RegenerateImageRequest(BaseModel):
    scene_number: int
    scene_text: str
    art_style: str

class RegenerateSceneAssetsRequest(BaseModel):
    scene_number: int
    scene_text: str
    art_style: str
    tone: str
    instruction: str


# ============================================================
# New endpoints
# ============================================================

@app.post("/regenerate-image")
def regenerate_image(req: RegenerateImageRequest):
    """Regenerate just the image for a scene — keep text, new image."""
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            image_file = os.path.join(tmpdir, f"scene_{req.scene_number}.png")
            image_saved = generate_scene_image(
                image_model, req.scene_text, image_file, req.art_style
            )
            image_b64 = None
            if image_saved and os.path.exists(image_file):
                with open(image_file, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode("utf-8")
            return {
                "scene_number": req.scene_number,
                "image_b64": image_b64,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/regenerate-scene-assets")
def regenerate_scene_assets(req: RegenerateSceneAssetsRequest):
    """
    Rewrite a scene from user feedback then regenerate its image + audio.
    This is the post-generation feedback loop from Story Viewer.
    """
    try:
        # Rewrite scene text
        new_text = regenerate_single_scene(
            story_model,
            req.scene_number,
            req.scene_text,
            req.instruction,
            req.tone,
        )
        new_text = clean_scene_text(new_text)

        # Generate new image + audio
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            image_file = os.path.join(tmpdir, f"scene_{req.scene_number}.png")
            audio_file = os.path.join(tmpdir, f"scene_{req.scene_number}.mp3")

            image_saved = generate_scene_image(
                image_model, new_text, image_file, req.art_style
            )
            generate_scene_audio(tts_client, new_text, audio_file)

            image_b64 = None
            if image_saved and os.path.exists(image_file):
                with open(image_file, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode("utf-8")

            audio_b64 = None
            if os.path.exists(audio_file):
                with open(audio_file, "rb") as f:
                    audio_b64 = base64.b64encode(f.read()).decode("utf-8")

            return {
                "scene_number": req.scene_number,
                "scene_text": new_text,
                "image_b64": image_b64,
                "audio_b64": audio_b64,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SingleSceneAssetsRequest(BaseModel):
    scene_number: int
    scene_text: str
    art_style: str


@app.post("/generate-single-scene-assets")
def generate_single_scene_assets(req: SingleSceneAssetsRequest):
    """Generate image + audio for a single scene — used for background generation during review."""
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            image_file = os.path.join(tmpdir, f"scene_{req.scene_number}.png")
            audio_file = os.path.join(tmpdir, f"scene_{req.scene_number}.mp3")

            image_saved = generate_scene_image(image_model, req.scene_text, image_file, req.art_style)
            generate_scene_audio(tts_client, req.scene_text, audio_file)

            image_b64 = None
            if image_saved and os.path.exists(image_file):
                with open(image_file, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode("utf-8")

            audio_b64 = None
            if os.path.exists(audio_file):
                with open(audio_file, "rb") as f:
                    audio_b64 = base64.b64encode(f.read()).decode("utf-8")

            return {
                "scene_number": req.scene_number,
                "image_b64": image_b64,
                "audio_b64": audio_b64,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SingleSceneAssetsRequest(BaseModel):
    scene_number: int
    scene_text: str
    art_style: str