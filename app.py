import streamlit as st
import google.generativeai as genai
import json
import re
import base64
from datetime import datetime
import os

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


def get_api_key():
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY")


def extract_claims(pdf_bytes: bytes) -> list:
    """Extract verifiable claims from PDF using Gemini Flash."""
    genai.configure(api_key=get_api_key())
    model = genai.GenerativeModel("gemini-1.5-flash")

    pdf_part = {
        "inline_data": {
            "mime_type": "application/pdf",
            "data": base64.b64encode(pdf_bytes).decode()
        }
    }

    prompt = """Analyze this PDF and extract ALL specific, verifiable claims such as:
- Statistics and percentages (e.g. "revenue grew 45%", "3 billion users")
- Dates and founding years
- Financial figures (valuations, revenue, market cap)
- Named facts attributed to studies or organizations
- Market size or population figures

Return ONLY a JSON array — no markdown fences, no explanation, just the raw array:
[
  {"claim": "exact claim text", "context": "brief surrounding context", "type": "statistic|date|financial|technical"},
  ...
]

Extract between 5 and 15 claims."""

    response = model.generate_content([pdf_part, prompt])
    raw = response.text.strip()
    raw = re.sub(r"```json\s*|```\s*", "", raw).strip()
    return json.loads(raw)


def verify_claim(claim_obj: dict) -> dict:
    """Verify a single claim using Gemini + Google Search grounding."""
    genai.configure(api_key=get_api_key())

    model = genai.GenerativeModel(
        "gemini-1.5-flash",
        tools="google_search_retrieval"
    )

    claim = claim_obj.get("claim", "")
    context = claim_obj.get("context", "")
    ctype = claim_obj.get("type", "statistic")

    prompt = f"""You are a professional fact-checker. Search the web and verify this claim:

CLAIM: "{claim}"
CONTEXT: "{context}"
TYPE: {ctype}

After searching, respond ONLY with this JSON object (no markdown, no fences):
{{
  "claim": "{claim}",
  "verdict": "VERIFIED|INACCURATE|FALSE|UNVERIFIABLE",
  "confidence": <integer 0-100>,
  "real_fact": "<the actual correct information you found>",
  "explanation": "<1-2 sentences explaining your finding>",
  "sources": ["<source 1>", "<source 2>"]
}}

Verdict definitions:
- VERIFIED: claim matches current web data within ~10%
- INACCURATE: claim is outdated or off by a significant margin (state the correct value in real_fact)
- FALSE: claim is demonstrably wrong or fabricated
- UNVERIFIABLE: no reliable sources found to confirm or deny"""

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
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
            "real_fact": "Could not retrieve information.",
            "explanation": f"Verification error: {str(e)[:120]}",
            "sources": [],
            "claim_type": ctype
        }


BADGE_MAP = {
    "VERIFIED":     ("badge-verified",     "✓ Verified"),
    "INACCURATE":   ("badge-inaccurate",   "⚠ Inaccurate"),
    "FALSE":        ("badge-false",        "✗ False"),
    "UNVERIFIABLE": ("badge-unverifiable", "? Unverifiable"),
}
CARD_MAP = {
    "VERIFIED":     "verdict-card verdict-verified",
    "INACCURATE":   "verdict-card verdict-inaccurate",
    "FALSE":        "verdict-card verdict-false",
    "UNVERIFIABLE": "verdict-card verdict-unverifiable",
}

def badge_html(verdict):
    cls, label = BADGE_MAP.get(verdict, ("badge-unverifiable", verdict))
    return f'<span class="badge {cls}">{label}</span>'


# ── UI ─────────────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">FactCheck AI</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">// Automated Truth Layer — Powered by Gemini + Google Search (Free)</div>', unsafe_allow_html=True)

api_key = get_api_key()
if not api_key:
    st.error("⚠️ No Gemini API key found. Please add GEMINI_API_KEY to your Streamlit secrets.")
    st.stop()

col1, col2 = st.columns([1.2, 1])

with col1:
    st.markdown("**Upload a PDF** to extract and verify every factual claim against live Google Search data.")
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
            <div><b style="color:#e5e7eb;">Extract</b><br><span style="color:#6b7280;font-size:0.85rem;">Gemini reads your PDF and isolates every specific, verifiable claim.</span></div>
        </div>
        <div style="display:flex;gap:12px;align-items:flex-start;margin-bottom:1rem;">
            <span style="background:#1a1025;color:#a78bfa;border-radius:6px;padding:4px 10px;font-weight:700;font-size:0.85rem;flex-shrink:0;">02</span>
            <div><b style="color:#e5e7eb;">Verify</b><br><span style="color:#6b7280;font-size:0.85rem;">Each claim is cross-referenced live using Google Search grounding.</span></div>
        </div>
        <div style="display:flex;gap:12px;align-items:flex-start;">
            <span style="background:#1a1025;color:#a78bfa;border-radius:6px;padding:4px 10px;font-weight:700;font-size:0.85rem;flex-shrink:0;">03</span>
            <div><b style="color:#e5e7eb;">Report</b><br><span style="color:#6b7280;font-size:0.85rem;">Every claim is flagged Verified / Inaccurate / False with real data.</span></div>
        </div>
    </div>""", unsafe_allow_html=True)

st.divider()

# ── Run pipeline ───────────────────────────────────────────────────────────────
if run_btn and uploaded_file:
    pdf_bytes = uploaded_file.read()
    prog = st.progress(0)
    status = st.empty()

    try:
        status.markdown("*⚙️ Step 1 — Reading PDF and extracting claims...*")
        prog.progress(15)

        claims_raw = extract_claims(pdf_bytes)
        total_claims = len(claims_raw)
        status.markdown(f"*✅ Found {total_claims} verifiable claims. Now checking each one...*")

        results = []
        for i, c in enumerate(claims_raw):
            pct = 15 + int(80 * (i + 1) / total_claims)
            claim_preview = c['claim'][:55]
            status.markdown(f"*🔎 Verifying {i+1}/{total_claims}: '{claim_preview}...'*")
            prog.progress(pct)
            results.append(verify_claim(c))

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
            "total_claims": total_claims,
            "summary": counts,
            "results": results
        }

    except Exception as e:
        prog.empty()
        status.empty()
        st.error(f"❌ Error: {str(e)}")

# ── Report display ─────────────────────────────────────────────────────────────
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
    m4.metric("✗ False", s.get("FALSE", 0))
    m5.metric("Trust Score", f"{trust}%")

    st.markdown("---")
    filter_sel = st.radio("Filter by verdict:", ["All", "VERIFIED", "INACCURATE", "FALSE", "UNVERIFIABLE"], horizontal=True)
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
