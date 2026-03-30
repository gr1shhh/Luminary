import os
import base64
import asyncio
import tempfile
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import Optional
import json

from story_generator import (
    init_story_model,
    plan_story,
    generate_story,
    critique_scene,
    regenerate_single_scene,
    extract_characters,
    _parse_json,
)
from scene_parser import extract_scenes, clean_scene_text
from image_generator import init_image_model, generate_scene_image
from audio_generator import init_tts, generate_scene_audio_with_timings
from run_manager import setup_run
from config import CRITIQUE_THRESHOLD, MAX_CRITIQUE_RETRIES, SCENE_DELAY

import time

app = FastAPI(title="Luminary API")

import os as _os
_sample_dir = _os.path.join(_os.path.dirname(__file__), "sample")
if _os.path.exists(_sample_dir):
    app.mount("/sample", StaticFiles(directory=_sample_dir), name="sample")

imagen_lock = asyncio.Lock()
last_imagen_time = 0.0

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    character_descriptions: Optional[str] = ""

class RegenerateImageRequest(BaseModel):
    scene_number: int
    scene_text: str
    art_style: str
    character_descriptions: Optional[str] = ""

class RegenerateSceneAssetsRequest(BaseModel):
    scene_number: int
    scene_text: str
    art_style: str
    tone: str
    instruction: str
    character_descriptions: Optional[str] = ""

class SingleSceneAssetsRequest(BaseModel):
    scene_number: int
    scene_text: str
    art_style: str
    character_descriptions: Optional[str] = ""

# class ExportVideoRequest(BaseModel):
#     scenes: list[dict]  # each: { scene_number, image_b64, audio_b64 }
#     topic: str
class ExportVideoRequest(BaseModel):
    scenes: list[dict]  # each: { scene_number, image_b64, audio_b64, word_timings, scene_text }
    topic: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/plan")
def plan(req: PlanRequest):
    try:
        result = plan_story(story_model, req.topic)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/story")
def story(req: StoryRequest):
    try:
        story_text = generate_story(story_model, req.topic, req.plan, req.steering)
        scenes = extract_scenes(story_text, req.plan["scene_count"])
        scenes = [clean_scene_text(s) for s in scenes]
        character_descriptions = extract_characters(story_model, scenes)
        print(f"  Characters extracted: {character_descriptions[:100] if character_descriptions else 'none'}")
        return {
            "scenes": scenes,
            "character_descriptions": character_descriptions,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/critique")
def critique(req: CritiqueRequest):
    try:
        result = critique_scene(story_model, req.scene_number, req.scene_text, req.tone)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/regenerate")
def regenerate(req: RegenerateRequest):
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
    output_dir = setup_run()
    results = []

    for i, scene_text in enumerate(req.scenes, start=1):
        image_file = os.path.join(output_dir, f"scene_{i}.png")
        image_saved = generate_scene_image(
            image_model, scene_text, image_file, req.art_style,
            story_model, req.character_descriptions
        )
        audio_b64, word_timings = generate_scene_audio_with_timings(tts_client, scene_text)
        image_b64 = None
        if image_saved and os.path.exists(image_file):
            with open(image_file, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")
        results.append({
            "scene_number": i,
            "scene_text": scene_text,
            "image_b64": image_b64,
            "audio_b64": audio_b64,
            "word_timings": word_timings,
        })
        if i < len(req.scenes):
            time.sleep(SCENE_DELAY)

    return {"scenes": results}


@app.post("/generate-assets/stream")
async def generate_assets_stream(req: GenerateAssetsRequest):
    output_dir = setup_run()

    async def event_generator():
        for i, scene_text in enumerate(req.scenes, start=1):
            yield f"data: {json.dumps({'type': 'progress', 'scene': i, 'total': len(req.scenes), 'status': 'generating'})}\n\n"

            image_file = os.path.join(output_dir, f"scene_{i}.png")
            loop = asyncio.get_event_loop()

            audio_b64, word_timings = await loop.run_in_executor(
                None, generate_scene_audio_with_timings, tts_client, scene_text
            )

            async with imagen_lock:
                global last_imagen_time
                elapsed = time.time() - last_imagen_time
                if elapsed < SCENE_DELAY:
                    wait = SCENE_DELAY - elapsed
                    print(f"  Waiting {wait:.1f}s before Imagen call for scene {i}...")
                    await asyncio.sleep(wait)
                image_saved = await loop.run_in_executor(
                    None, generate_scene_image,
                    image_model, scene_text, image_file, req.art_style,
                    story_model, req.character_descriptions
                )
                last_imagen_time = time.time()

            image_b64 = None
            if image_saved and os.path.exists(image_file):
                with open(image_file, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode("utf-8")

            yield f"data: {json.dumps({'type': 'scene', 'scene_number': i, 'scene_text': scene_text, 'image_b64': image_b64, 'audio_b64': audio_b64, 'word_timings': word_timings})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@app.post("/regenerate-image")
def regenerate_image_endpoint(req: RegenerateImageRequest):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            image_file = os.path.join(tmpdir, f"scene_{req.scene_number}.png")
            image_saved = generate_scene_image(
                image_model, req.scene_text, image_file, req.art_style,
                story_model, req.character_descriptions
            )
            image_b64 = None
            if image_saved and os.path.exists(image_file):
                with open(image_file, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode("utf-8")
            return {"scene_number": req.scene_number, "image_b64": image_b64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/regenerate-scene-assets")
def regenerate_scene_assets(req: RegenerateSceneAssetsRequest):
    try:
        new_text = regenerate_single_scene(
            story_model, req.scene_number, req.scene_text, req.instruction, req.tone,
        )
        new_text = clean_scene_text(new_text)

        with tempfile.TemporaryDirectory() as tmpdir:
            image_file = os.path.join(tmpdir, f"scene_{req.scene_number}.png")
            image_saved = generate_scene_image(
                image_model, new_text, image_file, req.art_style,
                story_model, req.character_descriptions
            )
            audio_b64, word_timings = generate_scene_audio_with_timings(tts_client, new_text)
            image_b64 = None
            if image_saved and os.path.exists(image_file):
                with open(image_file, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode("utf-8")
            return {
                "scene_number": req.scene_number,
                "scene_text": new_text,
                "image_b64": image_b64,
                "audio_b64": audio_b64,
                "word_timings": word_timings,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-single-scene-assets")
async def generate_single_scene_assets(req: SingleSceneAssetsRequest):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            image_file = os.path.join(tmpdir, f"scene_{req.scene_number}.png")
            loop = asyncio.get_event_loop()

            audio_b64, word_timings = await loop.run_in_executor(
                None, generate_scene_audio_with_timings, tts_client, req.scene_text
            )

            async with imagen_lock:
                global last_imagen_time
                elapsed = time.time() - last_imagen_time
                if elapsed < SCENE_DELAY:
                    wait = SCENE_DELAY - elapsed
                    print(f"  Waiting {wait:.1f}s before Imagen call for scene {req.scene_number}...")
                    await asyncio.sleep(wait)
                image_saved = await loop.run_in_executor(
                    None, generate_scene_image,
                    image_model, req.scene_text, image_file, req.art_style,
                    story_model, req.character_descriptions
                )
                last_imagen_time = time.time()

            image_b64 = None
            if image_saved and os.path.exists(image_file):
                with open(image_file, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode("utf-8")

            return {
                "scene_number": req.scene_number,
                "image_b64": image_b64,
                "audio_b64": audio_b64,
                "word_timings": word_timings,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/export-video")
def export_video(req: ExportVideoRequest):
    try:
        from PIL import Image
        import io
        import subprocess
        import imageio_ffmpeg

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

        def build_srt(word_timings, scene_text, duration, offset=0.0):
            if not word_timings:
                return []
            original_words = scene_text.strip().split()
            chunk_size = 6
            phrases = []
            for i in range(0, len(word_timings), chunk_size):
                chunk = word_timings[i:i + chunk_size]
                display_words = " ".join(original_words[i:i + chunk_size])
                start = chunk[0]["time"] + offset
                if i + chunk_size < len(word_timings):
                    end = word_timings[i + chunk_size]["time"] + offset - 0.1
                else:
                    end = duration + offset
                phrases.append({"text": display_words, "start": start, "end": end})
            return phrases

        def seconds_to_srt_time(s):
            h = int(s // 3600)
            m = int((s % 3600) // 60)
            sec = int(s % 60)
            ms = int((s - int(s)) * 1000)
            return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"

        with tempfile.TemporaryDirectory() as tmpdir:
            scene_videos = []
            cumulative_duration = 0.0

            for scene in req.scenes:
                scene_num = scene["scene_number"]
                image_b64 = scene.get("image_b64")
                audio_b64 = scene.get("audio_b64")
                word_timings = scene.get("word_timings", [])
                scene_text = scene.get("scene_text", "")

                if not image_b64 or not audio_b64:
                    print(f"  Scene {scene_num} missing assets, skipping.")
                    continue

                print(f"  Processing scene {scene_num}...")

                # Save image
                img = Image.open(io.BytesIO(base64.b64decode(image_b64))).convert("RGB")
                w, h = img.size
                if w % 2 != 0: w -= 1
                if h % 2 != 0: h -= 1
                img = img.resize((w, h))
                image_file = os.path.join(tmpdir, f"scene_{scene_num}.png")
                img.save(image_file)

                # Save audio
                audio_file = os.path.join(tmpdir, f"scene_{scene_num}.mp3")
                with open(audio_file, "wb") as f:
                    f.write(base64.b64decode(audio_b64))

                # Get audio duration
                result = subprocess.run([ffmpeg, "-i", audio_file], capture_output=True, text=True)
                duration = 0.0
                for line in result.stderr.split("\n"):
                    if "Duration" in line:
                        parts = line.strip().split("Duration:")[1].split(",")[0].strip()
                        h_p, m_p, s_p = parts.split(":")
                        duration = int(h_p)*3600 + int(m_p)*60 + float(s_p)
                        break
                if duration == 0:
                    duration = 20.0
                print(f"  Duration: {duration:.1f}s")

                # Build SRT file
                phrases = build_srt(word_timings, scene_text, duration)
                print(f"  Phrases: {len(phrases)}")
                for p in phrases:
                    print(f"    {p['start']:.1f} -> {p['end']:.1f}: {p['text']}")
                    
                srt_file = os.path.join(tmpdir, f"scene_{scene_num}.srt")
                with open(srt_file, "w", encoding="utf-8") as f:
                    for idx, phrase in enumerate(phrases, 1):
                        f.write(f"{idx}\n")
                        f.write(f"{seconds_to_srt_time(phrase['start'])} --> {seconds_to_srt_time(phrase['end'])}\n")
                        f.write(f"{phrase['text']}\n\n")

                # Build scene video: image + audio + burned subtitles
                scene_video = os.path.join(tmpdir, f"scene_{scene_num}.mp4")
                
                # Build drawtext filter from phrases
                vf_parts = []
                for phrase in phrases:
                    start_t = phrase["start"]
                    end_t = phrase["end"]

                    text = (phrase["text"]
                        .replace("'", "'")
                        .replace("'", "'")
                        .replace("\\", "\\\\")
                        .replace(".", "\\.")
                        .replace(":", "\\:")
                        .replace(",", "\\,")
                        .replace("[", "\\[")
                        .replace("]", "\\]")
                    )
                    vf_parts.append(
                        f"drawtext=text='{text}'"
                        f":fontsize=36"
                        f":fontcolor=white"
                        f":borderw=2"
                        f":bordercolor=black"
                        f":shadowx=1"
                        f":shadowy=1"
                        f":shadowcolor=black"
                        f":x=(w-text_w)/2"
                        f":y=h-text_h-50"
                        f":enable=between(t\\,{start_t}\\,{end_t})"
                    )
                
                filter_file = os.path.join(tmpdir, f"filter_{scene_num}.txt")
                if vf_parts:
                    with open(filter_file, "w", encoding="utf-8") as ff:
                        ff.write(",".join(vf_parts))
                    vf_arg = ["-filter_script:v", filter_file]
                else:
                    vf_arg = ["-vf", "null"]

                cmd = [
                    ffmpeg, "-y",
                    "-loop", "1",
                    "-i", image_file,
                    "-i", audio_file,
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-t", str(duration),
                    "-pix_fmt", "yuv420p",
                    "-shortest",
                ] + vf_arg + [scene_video]
                
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                print(f"  ffmpeg stderr: {result.stderr[-800:]}")
                if result.returncode != 0:
                    raise Exception(f"Scene {scene_num} video creation failed")
                print(f"  Scene {scene_num} video done.")
                
                scene_videos.append(scene_video)
                cumulative_duration += duration

            if not scene_videos:
                raise HTTPException(status_code=400, detail="No valid scenes to export")

            # Concatenate all scenes
            print(f"  Concatenating {len(scene_videos)} scenes...")
            concat_list = os.path.join(tmpdir, "concat.txt")
            with open(concat_list, "w") as f:
                for v in scene_videos:
                    f.write(f"file '{v}'\n")

            output_file = os.path.join(tmpdir, "luminary_story.mp4")
            subprocess.run([
                ffmpeg, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list,
                "-c", "copy",
                output_file
            ], check=True, capture_output=True)

            with open(output_file, "rb") as f:
                video_b64 = base64.b64encode(f.read()).decode("utf-8")

            print(f"  Done! Video size: {len(video_b64) // 1024}KB")
            return {"video_b64": video_b64}

    except Exception as e:
        print(f"EXPORT ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))