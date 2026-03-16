# Luminary — AI Cinematic Story Engine

Turn any idea into a fully illustrated, narrated cinematic story using Gemini, Imagen 3, and Google Cloud TTS.

---

## Setup

**1. Clone the repo and activate your environment**
```bash
conda create -n luminary python=3.11
conda activate luminary
```

**2. Install Google Cloud CLI**
Download and install:\
https://cloud.google.com/sdk/docs/install

```bash
gcloud --version
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```


**3. Authenticate with Google Cloud**
```bash
gcloud auth application-default login
gcloud config set project project-10881a8c-2364-4aa8-856
```

---

## Run

**Frontend - Streamlit UI**
```bash
streamlit run app.py
```

**Backend - CLI**
```bash
python main.py
```

---

## Notes
- Generated stories saved to `outputs/latest/`
- Don't commit the `outputs/` folder
- Image generation has an 80s delay between scenes — don't kill the process