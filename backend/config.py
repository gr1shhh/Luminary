PROJECT_ID = "project-10881a8c-2364-4aa8-856"
LOCATION = "us-central1"

BASE_OUTPUT_DIR = "outputs"
LATEST_DIR = "outputs/latest"

STORY_MODEL_NAME = "gemini-2.5-flash"
IMAGE_MODEL_NAME = "imagen-3.0-generate-001"

VOICE_NAME = "en-US-Studio-O"
SPEAKING_RATE = 0.92

SCENE_DELAY = 61

# --- Fallback topic if user skips input ---
USER_TOPIC = "A NASA engineer watching the moon landing"

# --- Suggested prompts shown in CLI and frontend ---
SUGGESTED_TOPICS = [
    "A NASA engineer watching the moon landing",
    "A soldier writing his last letter home before battle",
    "A lighthouse keeper on the night a ship disappears",
]

# --- Agent settings ---
MIN_SCENES = 3
MAX_SCENES = 7
CRITIQUE_THRESHOLD = 7       # scenes scoring below this are auto-rewritten
MAX_CRITIQUE_RETRIES = 2     # max times a scene can be auto-improved