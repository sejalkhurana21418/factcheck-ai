# factcheck-ai

# FactCheck AI — Automated Truth Layer

> Upload any PDF. Every factual claim is automatically extracted and verified against live web data.

---

## Live Demo

**Deployed App:** `https://factcheck-ai-sejal.streamlit.app/` 


---

## What It Does

FactCheck AI reads a PDF document, pulls out every specific verifiable claim (statistics, dates, financial figures, founding facts), searches the live web for each one, and returns one of three verdicts:

| Verdict | Meaning |
|---|---|
| ✓ **Verified** | Live web data confirms the claim is accurate |
| ⚠ **Inaccurate** | Evidence was found, but the stat/date/figure is wrong or outdated — real data shown |
| ✗ **False** | No credible evidence found anywhere that this claim exists |

---

## How It Works

```
PDF Upload
    │
    ▼
Text Extraction (pypdf)
    │  Pulls all readable text from the document
    ▼
Claim Extraction (Groq — Llama 3.3 70B)
    │  Identifies every specific, verifiable claim:
    │  stats, dates, financial figures, named facts
    ▼
Web Search (Tavily API)
    │  Each claim is searched against live web sources
    ▼
Verdict (Groq — Llama 3.3 70B)
    │  Reasons over search results and assigns verdict
    │  with explanation + real corrected data
    ▼
Report UI (Streamlit)
    │  Filterable by verdict
    │  Downloadable as JSON
```

---

# FactCheck AI — Automated Truth Layer

> Upload any PDF. Every factual claim is automatically extracted and verified against live web data.

---

## Live Demo

**Deployed App:** `https://your-app.streamlit.app` *(replace with your URL)*

**GitHub Repo:** `https://github.com/your-username/factcheck-ai` *(replace with your repo)*

---

## What It Does

FactCheck AI reads a PDF document, pulls out every specific verifiable claim (statistics, dates, financial figures, founding facts), searches the live web for each one, and returns one of three verdicts:

| Verdict | Meaning |
|---|---|
| ✓ **Verified** | Live web data confirms the claim is accurate |
| ⚠ **Inaccurate** | Evidence was found, but the stat/date/figure is wrong or outdated — real data shown |
| ✗ **False** | No credible evidence found anywhere that this claim exists |

---

## How It Works

```
PDF Upload
    │
    ▼
Text Extraction (pypdf)
    │  Pulls all readable text from the document
    ▼
Claim Extraction (Groq — Llama 3.3 70B)
    │  Identifies every specific, verifiable claim:
    │  stats, dates, financial figures, named facts
    ▼
Web Search (Tavily API)
    │  Each claim is searched against live web sources
    ▼
Verdict (Groq — Llama 3.3 70B)
    │  Reasons over search results and assigns verdict
    │  with explanation + real corrected data
    ▼
Report UI (Streamlit)
    │  Filterable by verdict
    │  Downloadable as JSON
```

---

## Tech Stack

| Component | Tool | 
|---|---|
| Frontend | Streamlit | 
| LLM | Groq (Llama 3.3 70B) | 
| Web Search | Tavily API | 
| PDF Parsing | pypdf | 
| Hosting | Streamlit Cloud | 



---

## Local Setup

### 1. Clone the repo

```bash
git clone https://github.com/your-username/factcheck-ai.git
cd factcheck-ai
pip install -r requirements.txt
```

### 2. Get your free API keys

- **Groq API key:** [console.groq.com](https://console.groq.com) → API Keys → Create
- **Tavily API key:** [tavily.com](https://tavily.com) → Sign up → Dashboard

### 3. Add keys to Streamlit secrets

```bash
mkdir -p .streamlit
```

Create `.streamlit/secrets.toml`:

```toml
GROQ_API_KEY = "gsk_your-key-here"
TAVILY_API_KEY = "tvly-your-key-here"
```

### 4. Run

```bash
streamlit run app.py
```

Visit `http://localhost:8501`

---

## Deployment (Streamlit Cloud)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Select your repo, set main file to `app.py`
4. Go to **Advanced settings → Secrets** and paste:

```toml
GROQ_API_KEY = "gsk_your-key-here"
TAVILY_API_KEY = "tvly-your-key-here"
```

5. Click **Deploy** → live URL in ~2 minutes

---

## File Structure

```
factcheck-ai/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── README.md              # This file
└── .streamlit/
    └── config.toml        # Theme configuration
```

---

## Evaluation — Trap Document Test

This app is specifically designed to catch:

- **Fabricated statistics** — e.g. wrong user counts, market sizes
- **Outdated figures** — e.g. stats that were true years ago but have since changed
- **Wrong dates** — e.g. incorrect founding years or launch dates
- **False attributions** — e.g. wrong person credited for an invention or company

To test it yourself, upload any document containing suspicious stats. The app will flag each claim individually with the correct real-world data cited.

---

## Requirements

```
groq>=0.9.0
requests>=2.31.0
pypdf>=4.0.0
streamlit>=1.32.0
```

---

## Limitations

- PDFs must be text-selectable (scanned image-only PDFs will not work)
- Tavily free tier allows 1000 searches per month
- Processing time is roughly 30-60 seconds depending on number of claims found


--- 

## File Structure

```
factcheck-ai/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── README.md              # This file
└── .streamlit/
    └── config.toml        # Theme configuration
```

---

## Evaluation — Trap Document Test

This app is specifically designed to catch:

- **Fabricated statistics** — e.g. wrong user counts, market sizes
- **Outdated figures** — e.g. stats that were true years ago but have since changed
- **Wrong dates** — e.g. incorrect founding years or launch dates
- **False attributions** — e.g. wrong person credited for an invention or company

To test it yourself, upload any document containing suspicious stats. The app will flag each claim individually with the correct real-world data cited.

---

## Requirements

```
groq>=0.9.0
requests>=2.31.0
pypdf>=4.0.0
streamlit>=1.32.0
```

---

## Limitations

- PDFs must be text-selectable (scanned image-only PDFs will not work)
- Tavily free tier allows 1000 searches per month
- Processing time is roughly 30-60 seconds depending on number of claims found
