# Luminary — AI Cinematic Story Engine

Turn any idea into a fully illustrated, narrated cinematic story using Gemini 2.5 Flash, Imagen 3, and Google Cloud TTS.

🌐 **Live Demo:** https://luminary-omega-one.vercel.app
---

## Setup

**1. Clone the repo and activate your environment**
```bash
conda create -n luminary python=3.11
conda activate luminary
```

**2. Install Google Cloud CLI**
Download and install:
https://cloud.google.com/sdk/docs/install

```bash
gcloud --version
```

**3. Install backend dependencies**
```bash
cd backend
pip install -r requirements.txt
```

**4. Authenticate with Google Cloud**
```bash
gcloud auth application-default login
gcloud config set project project-10881a8c-2364-4aa8-856
```

**5. Install frontend dependencies**
```bash
cd frontend
npm install
```

---

## Run

**Backend**
```bash
cd backend
uvicorn api:app --reload
```
Runs at `http://localhost:8000` — test at `/health`

**Frontend**
```bash
cd frontend
npm start
```
Runs at `http://localhost:3000`

Create `frontend/.env`:
```
REACT_APP_API_URL=http://localhost:8000
REACT_APP_MOCK=false
```

---

## Notes
- Generated assets saved to `backend/outputs/latest/`
- Image generation has a ~60s cooldown between scenes (so it doesn hit the free quota limit)
- To test UI without the backend: set `REACT_APP_MOCK=true` in `frontend/.env`