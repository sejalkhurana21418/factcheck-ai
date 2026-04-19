import streamlit as st
from groq import Groq
import requests
import json
import re
import base64
from datetime import datetime
import os
import time

st.set_page_config(
    page_title="FactCheck AI — Truth Layer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');

html, body, [class*="css"] { font-family: 'Syne', sans-serif; }
.main { background: #0a0a0f; }
.block-container { padding: 2rem 3rem; max-width: 1100px; }

.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: 3.2rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, #e8e0ff 0%, #a78bfa 50%, #7c3aed 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.25rem;
    line-height: 1.1;
}
.hero-sub {
    font-family: 'DM Mono', monospace;
    font-size: 0.85rem;
    color: #6b7280;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 2.5rem;
}
.verdict-card {
    background: #111118;
    border: 1px solid #1e1e2e;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin: 0.75rem 0;
}
.verdict-verified   { border-left: 4px solid #10b981; }
.verdict-inaccurate { border-left: 4px solid #f59e0b; }
.verdict-false      { border-left: 4px solid #ef4444; }
.verdict-unverifiable { border-left: 4px solid #6b7280; }

.badge { display:inline-block; font-family:'DM Mono',monospace; font-size:0.7rem;
         font-weight:500; letter-spacing:0.08em; text-transform:uppercase;
         padding:3px 10px; border-radius:4px; margin-bottom:0.5rem; }
.badge-verified     { background:#064e3b; color:#6ee7b7; }
.badge-inaccurate   { background:#451a03; color:#fcd34d; }
.badge-false        { background:#450a0a; color:#fca5a5; }
.badge-unverifiable { background:#1f2937; color:#9ca3af; }

.claim-text    { font-size:1rem; color:#e5e7eb; font-weight:500; margin-bottom:0.4rem; }
.evidence-text { font-family:'DM Mono',monospace; font-size:0.8rem; color:#6b7280; line-height:1.6; }
.real-fact     { font-family:'DM Mono',monospace; font-size:0.8rem; color:#a78bfa; margin-top:0.3rem; }

.stButton > button {
    background: linear-gradient(135deg,#7c3aed,#4f46e5) !important;
    color: white !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.65rem 2rem !important;
    font-size: 0.95rem !important;
    width: 100% !important;
}
.stProgress > div > div { background: linear-gradient(90deg,#7c3aed,#4f46e5) !important; }
footer{display:none;} #MainMenu{visibility:hidden;} header{visibility:hidden;}
</style>
""", unsafe_allow_html=True)


# ── API Keys ───────────────────────────────────────────────────────────────────
def get_secret(key):
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key)


# ── Step 1: Extract text from PDF using Groq ───────────────────────────────────
def extract_claims_from_pdf(pdf_bytes: bytes) -> list:
    client = Groq(api_key=get_secret("GROQ_API_KEY"))

    # Encode PDF as base64 and send as a document message
    pdf_b64 = base64.b64encode(pdf_bytes).decode()

    prompt = """You are an expert fact-checker. I will give you text extracted from a PDF document.

Extract ALL specific, verifiable claims such as:
- Statistics and percentages (e.g. "revenue grew 45%", "3 billion users")
- Dates and founding years (e.g. "founded in 2005")
- Financial figures (valuations, revenue, market cap)
- Named facts attributed to studies or organizations
- Market size or population figures
- Named record-breaking claims

Return ONLY a raw JSON array — no markdown, no explanation:
[
  {"claim": "exact claim text from document", "context": "brief surrounding context", "type": "statistic|date|financial|technical"},
  ...
]

Extract between 5 and 15 claims."""

    # Use Groq's document understanding via base64 in user message
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Here is the PDF content (base64 encoded for reference). Please analyze the following extracted text and {prompt}"
                    }
                ]
            }
        ],
        temperature=0.1,
        max_tokens=2000
    )

    # Groq doesn't do PDF natively — we need to extract text first
    # This will be handled by the caller who passes extracted text
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"```json\s*|```\s*", "", raw).strip()
    return json.loads(raw)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract raw text from PDF using pypdf."""
    try:
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        return f"Error extracting PDF text: {str(e)}"


def extract_claims(pdf_text: str) -> list:
    """Use Groq/Llama to extract verifiable claims from text."""
    client = Groq(api_key=get_secret("GROQ_API_KEY"))

    prompt = f"""You are an expert fact-checker. Analyze the following document text and extract ALL specific, verifiable claims such as:
- Statistics and percentages (e.g. "revenue grew 45%", "3 billion users")
- Dates and founding years (e.g. "founded in 2005")
- Financial figures (valuations, revenue, market cap)
- Named facts attributed to studies or organizations
- Market size or population figures

DOCUMENT TEXT:
{pdf_text[:6000]}

Return ONLY a raw JSON array — no markdown fences, no explanation, just the array:
[
  {{"claim": "exact claim text", "context": "brief surrounding context", "type": "statistic|date|financial|technical"}},
  ...
]

Extract between 5 and 15 of the most specific, verifiable claims."""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=2000
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"```json\s*|```\s*", "", raw).strip()
    return json.loads(raw)


def search_web(query: str) -> str:
    """Search the web using Tavily API and return summarised results."""
    tavily_key = get_secret("TAVILY_API_KEY")
    if not tavily_key:
        return "No search results available (missing Tavily key)."

    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": tavily_key,
                "query": query,
                "search_depth": "basic",
                "max_results": 4,
                "include_answer": True
            },
            timeout=10
        )
        data = response.json()

        parts = []
        if data.get("answer"):
            parts.append(f"Summary: {data['answer']}")
        for r in data.get("results", [])[:3]:
            parts.append(f"- {r.get('title','')}: {r.get('content','')[:200]}")
        return "\n".join(parts) if parts else "No results found."

    except Exception as e:
        return f"Search failed: {str(e)}"


def verify_claim(claim_obj: dict) -> dict:
    """Verify a single claim using web search + Groq reasoning."""
    client = Groq(api_key=get_secret("GROQ_API_KEY"))

    claim = claim_obj.get("claim", "")
    context = claim_obj.get("context", "")
    ctype = claim_obj.get("type", "statistic")

    # Step A: search the web
    search_results = search_web(f"fact check: {claim}")

    # Step B: ask Groq to reason about it
    prompt = f"""You are a professional fact-checker. Analyze this claim against the web search results below.

CLAIM: "{claim}"
CONTEXT: "{context}"
TYPE: {ctype}

LIVE WEB SEARCH RESULTS:
{search_results}

Use EXACTLY these three verdict definitions — they are precise, not general:

- VERIFIED: The search results confirm the claim is accurate (within ~10% for numbers, correct for facts/dates).
- INACCURATE: The search results FOUND evidence related to this claim, but the numbers are wrong, outdated, or off by a significant margin. Use this when real data EXISTS but contradicts the claim.
- FALSE: The search results found NO credible evidence that this claim exists or ever happened. The claim appears to be completely fabricated with zero supporting sources.

Decision rules:
- Found evidence that contradicts the numbers → INACCURATE (state the real number)
- Found evidence that contradicts the date/name/fact → INACCURATE (state the real detail)
- Found ZERO evidence this claim exists anywhere → FALSE
- Claim matches evidence → VERIFIED

Respond ONLY with this JSON (no markdown, no fences):
{{
  "claim": "{claim}",
  "verdict": "VERIFIED|INACCURATE|FALSE",
  "confidence": <integer 0-100>,
  "real_fact": "<the actual correct figure/date/fact from search results, or 'No evidence found' if FALSE>",
  "explanation": "<1-2 sentences explaining what you found vs what the claim states>",
  "sources": ["<source 1>", "<source 2>"]
}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=600
        )

        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"```json\s*|```\s*", "", raw).strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        result = json.loads(match.group() if match else raw)
        result["claim_type"] = ctype
        return result

    except Exception as e:
        return {
            "claim": claim,
            "verdict": "UNVERIFIABLE",
            "confidence": 0,
            "real_fact": "Could not process.",
            "explanation": f"Error: {str(e)[:120]}",
            "sources": [],
            "claim_type": ctype
        }


# ── UI helpers ─────────────────────────────────────────────────────────────────
BADGE_MAP = {
    "VERIFIED":   ("badge-verified",   "✓ Verified"),
    "INACCURATE": ("badge-inaccurate", "⚠ Inaccurate"),
    "FALSE":      ("badge-false",      "✗ False — No Evidence Found"),
}
CARD_MAP = {
    "VERIFIED":   "verdict-card verdict-verified",
    "INACCURATE": "verdict-card verdict-inaccurate",
    "FALSE":      "verdict-card verdict-false",
}

def badge_html(verdict):
    cls, label = BADGE_MAP.get(verdict, ("badge-unverifiable", verdict))
    return f'<span class="badge {cls}">{label}</span>'


# ── Page ───────────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">FactCheck AI</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">// Automated Truth Layer — Powered by Groq + Tavily </div>', unsafe_allow_html=True)

# Key checks
groq_key = get_secret("GROQ_API_KEY")
tavily_key = get_secret("TAVILY_API_KEY")

if not groq_key:
    st.error("⚠️ Missing GROQ_API_KEY in Streamlit secrets.")
    st.stop()
if not tavily_key:
    st.warning("⚠️ Missing TAVILY_API_KEY — web search disabled. Add it to Streamlit secrets for full fact-checking.")

col1, col2 = st.columns([1.2, 1])

with col1:
    st.markdown("**Upload a PDF** to extract and verify every factual claim against live web data.")
    uploaded_file = st.file_uploader("Drop your PDF here", type=["pdf"], label_visibility="collapsed")

    if uploaded_file:
        st.success(f"📄 **{uploaded_file.name}** ({uploaded_file.size/1024:.1f} KB)")
        run_btn = st.button("🔍 Run Fact-Check", use_container_width=True)
    else:
        st.markdown("""
        <div style="border:2px dashed #2d2d3d;border-radius:16px;padding:3rem;text-align:center;background:#111118;margin:1rem 0;">
            <p style="color:#6b7280;font-family:'DM Mono',monospace;font-size:0.85rem;">
                PDF files up to 20MB<br>Marketing copy · Reports · Press releases · White papers
            </p>
        </div>""", unsafe_allow_html=True)
        run_btn = False

with col2:
    st.markdown("""
    <div style="background:#111118;border:1px solid #1e1e2e;border-radius:12px;padding:1.5rem;">
        <p style="font-family:'DM Mono',monospace;font-size:0.75rem;color:#7c3aed;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:1rem;">How it works</p>
        <div style="display:flex;gap:12px;align-items:flex-start;margin-bottom:1rem;">
            <span style="background:#1a1025;color:#a78bfa;border-radius:6px;padding:4px 10px;font-weight:700;font-size:0.85rem;flex-shrink:0;">01</span>
            <div><b style="color:#e5e7eb;">Extract</b><br><span style="color:#6b7280;font-size:0.85rem;">Llama 3.3 reads your PDF and pulls every specific verifiable claim.</span></div>
        </div>
        <div style="display:flex;gap:12px;align-items:flex-start;margin-bottom:1rem;">
            <span style="background:#1a1025;color:#a78bfa;border-radius:6px;padding:4px 10px;font-weight:700;font-size:0.85rem;flex-shrink:0;">02</span>
            <div><b style="color:#e5e7eb;">Search</b><br><span style="color:#6b7280;font-size:0.85rem;">Each claim is searched live via Tavily web search.</span></div>
        </div>
        <div style="display:flex;gap:12px;align-items:flex-start;">
            <span style="background:#1a1025;color:#a78bfa;border-radius:6px;padding:4px 10px;font-weight:700;font-size:0.85rem;flex-shrink:0;">03</span>
            <div><b style="color:#e5e7eb;">Verdict</b><br><span style="color:#6b7280;font-size:0.85rem;">Llama reasons over results and flags each claim with real data.</span></div>
        </div>
    </div>""", unsafe_allow_html=True)

st.divider()

# ── Pipeline ───────────────────────────────────────────────────────────────────
if run_btn and uploaded_file:
    pdf_bytes = uploaded_file.read()
    prog = st.progress(0)
    status = st.empty()

    try:
        status.markdown("*📄 Step 1 — Extracting text from PDF...*")
        prog.progress(10)
        pdf_text = extract_text_from_pdf(pdf_bytes)

        if not pdf_text or len(pdf_text) < 50:
            st.error("Could not extract text from this PDF. Make sure it's not a scanned image-only PDF.")
            st.stop()

        status.markdown("*🧠 Step 2 — Identifying verifiable claims...*")
        prog.progress(20)
        claims_raw = extract_claims(pdf_text)
        total = len(claims_raw)

        results = []
        for i, c in enumerate(claims_raw):
            pct = 20 + int(75 * (i + 1) / total)
            claim_preview = c['claim'][:55]
            status.markdown(f"*🔎 Verifying {i+1}/{total}: '{claim_preview}...'*")
            prog.progress(pct)
            results.append(verify_claim(c))
            time.sleep(1)  # avoid rate limit

        counts = {"VERIFIED": 0, "INACCURATE": 0, "FALSE": 0, "UNVERIFIABLE": 0}
        for r in results:
            v = r.get("verdict", "UNVERIFIABLE")
            counts[v] = counts.get(v, 0) + 1

        prog.progress(100)
        status.empty()
        prog.empty()

        st.session_state["report"] = {
            "filename": uploaded_file.name,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
            "total_claims": total,
            "summary": counts,
            "results": results
        }

    except Exception as e:
        prog.empty()
        status.empty()
        st.error(f"❌ Error: {str(e)}")

# ── Report ─────────────────────────────────────────────────────────────────────
if "report" in st.session_state:
    report = st.session_state["report"]
    s = report["summary"]
    results = report["results"]
    total = report["total_claims"]
    trust = int(s.get("VERIFIED", 0) / total * 100) if total else 0

    st.markdown(f"""
    <div style="margin-bottom:1rem;">
        <span style="font-family:'DM Mono',monospace;font-size:0.75rem;color:#6b7280;text-transform:uppercase;">{report['timestamp']}</span>
        <h2 style="margin:0;color:#e5e7eb;font-size:1.4rem;font-weight:700;">{report['filename']}</h2>
    </div>""", unsafe_allow_html=True)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Claims", total)
    m2.metric("✓ Verified", s.get("VERIFIED", 0))
    m3.metric("⚠ Inaccurate", s.get("INACCURATE", 0))
    m4.metric("✗ False / No Evidence", s.get("FALSE", 0))
    m5.metric("Trust Score", f"{trust}%")

    st.markdown("---")
    filter_sel = st.radio("Filter by verdict:", ["All", "VERIFIED", "INACCURATE", "FALSE"], horizontal=True)
    filtered = results if filter_sel == "All" else [r for r in results if r.get("verdict") == filter_sel]

    for res in filtered:
        verdict = res.get("verdict", "UNVERIFIABLE")
        real_html = ""
        if verdict != "VERIFIED":
            real_html = f'<p class="real-fact">→ Real data: {res.get("real_fact", "")}</p>'

        st.markdown(f"""
        <div class="{CARD_MAP.get(verdict, 'verdict-card verdict-unverifiable')}">
            {badge_html(verdict)}
            <span style="font-family:'DM Mono',monospace;font-size:0.65rem;color:#374151;margin-left:8px;">confidence: {res.get('confidence', 0)}%</span>
            <p class="claim-text">"{res.get('claim', '')}"</p>
            <p class="evidence-text">{res.get('explanation', '')}</p>
            {real_html}
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.download_button(
        "⬇ Download Full Report (JSON)",
        data=json.dumps(report, indent=2),
        file_name=f"factcheck_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
        mime="application/json"
    )
