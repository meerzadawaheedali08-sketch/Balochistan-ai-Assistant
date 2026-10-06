import os
import io
import re
import json
import base64
import html as html_lib
from datetime import datetime
from typing import Optional
from xml.sax.saxutils import escape as xml_escape

import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
from PIL import Image, ImageOps, ImageDraw
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib.colors import HexColor, white
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    PageTemplate,
    Frame,
    FrameBreak,
    NextPageTemplate,
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from pypdf import PdfReader

try:  # optional: needed only for Urdu text inside PDF files
    import arabic_reshaper
    from bidi.algorithm import get_display
except Exception:  # pragma: no cover
    arabic_reshaper = None
    get_display = None


# ============================================================
# BALOCHISTAN AI ASSISTANT
# ============================================================

st.set_page_config(
    page_title="Balochistan AI Assistant",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# SETTINGS / MODELS
# ------------------------------------------------------------
# Groq retired llama-3.3-70b-versatile (16 Aug 2026) and
# llama-4-scout (17 Jul 2026). Current free models are below.
# You can override them without touching code by adding
# TEXT_MODELS / VISION_MODELS (comma separated) in Secrets.
# The app tries each model in order until one works.
# ============================================================

def get_setting(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, "")
        if value:
            return str(value).strip()
    except Exception:
        pass
    return os.getenv(name, "").strip() or default


def get_list(name: str, default: list) -> list:
    raw = get_setting(name)
    if not raw:
        return default
    items = [x.strip() for x in raw.split(",") if x.strip()]
    return items or default


API_KEY = get_setting("GROQ_API_KEY") or None
TEXT_MODELS = get_list("TEXT_MODELS", ["openai/gpt-oss-120b", "openai/gpt-oss-20b"])
VISION_MODELS = get_list("VISION_MODELS", ["qwen/qwen3.8-27b"])

MAX_ATTACHMENT_CHARS = 12000  # free tier allows ~8K tokens/minute

LANGUAGES = ["English", "اردو", "Roman Urdu"]
AR_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F]")


# ============================================================
# SERVICES
# ============================================================

ICON_PATHS = {
    "email": '<rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>',
    "cv": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    "kisan": '<path d="M7 20h10"/><path d="M10 20c5.5-2.5.8-6.4 3-10"/><path d="M9.5 9.4c1.1.8 1.8 2.2 2.3 3.7-2 .4-3.5.4-4.8-.3-1.2-.6-2.3-1.9-3-4.2 2.8-.5 4.4 0 5.5.8z"/><path d="M14.1 6a7 7 0 0 0-1.1 4c1.9-.1 3.3-.6 4.3-1.4 1-1 1.6-2.3 1.7-4.6-2.7.1-4 1-4.9 2z"/>',
    "health": '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/><path d="M3.22 12H9.5l.5-1 2 4.5 2-7 1.5 3.5h5.27"/>',
    "gov": '<line x1="3" x2="21" y1="22" y2="22"/><line x1="6" x2="6" y1="18" y2="11"/><line x1="10" x2="10" y1="18" y2="11"/><line x1="14" x2="14" y1="18" y2="11"/><line x1="18" x2="18" y1="18" y2="11"/><polygon points="12 2 20 7 4 7"/>',
    "general": '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/>',
    "improve": '<path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
    "student": '<path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/>',
}

SERVICES = {
    "email": {"title": "Email Writer", "short": "Professional, ready-to-send emails", "color": "#2563eb"},
    "cv": {"title": "CV Builder", "short": "Designed CVs with your photo", "color": "#7c3aed"},
    "kisan": {"title": "Kisan Advisor", "short": "Crop and farming guidance", "color": "#16a34a"},
    "health": {"title": "Health Information", "short": "Understand health topics", "color": "#e11d48"},
    "gov": {"title": "Government Schemes", "short": "Understand public programs", "color": "#d97706"},
    "general": {"title": "AI Assistant", "short": "Ask, plan and create", "color": "#0891b2"},
    "improve": {"title": "Text Improver", "short": "Make your writing better", "color": "#db2777"},
    "student": {"title": "Student Helper", "short": "Study and understand", "color": "#4f46e5"},
}


def icon_svg(key: str, size: int = 24, color: Optional[str] = None) -> str:
    color = color or SERVICES[key]["color"]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round">{ICON_PATHS[key]}</svg>'
    )


def icon_tile(key: str, size: int = 48) -> str:
    color = SERVICES[key]["color"]
    return (
        f'<div class="icon-tile" style="width:{size}px;height:{size}px;background:{color}1a;">'
        f'{icon_svg(key, int(size * 0.5), color)}</div>'
    )


SYSTEM_PROMPTS = {
    "email": """You are a professional email-writing assistant.
Create a ready-to-send email with a useful subject, greeting, clear body and sign-off.
Use only facts supplied by the user. Do not invent qualifications, dates, promises or facts.""",

    "kisan": """You provide general agricultural education relevant to Pakistan.
Help with crops, soil, irrigation, common symptoms and general farming practices.
Ask for crop, location and crop stage when important.
Do not give unsafe pesticide instructions or invented chemical doses.
For chemical decisions, advise following the product label and consulting local agriculture experts.""",

    "health": """You provide general health information, not diagnosis or treatment.
Explain health topics clearly and recommend qualified medical care for personal decisions.
For emergency symptoms such as severe breathing difficulty, chest pain, unconsciousness,
stroke signs or severe bleeding, advise immediate emergency medical care.
Do not prescribe medicines or dosages.""",

    "gov": """You help users understand public assistance programs in Pakistan.
Rules, eligibility and deadlines can change. Clearly separate general guidance from verified facts.
Do not claim a scheme is open or that a person is eligible unless the user provides verified evidence.
Recommend checking official government channels before submitting documents or paying anyone.""",

    "general": """You are a helpful, accurate general-purpose AI assistant.
Explain clearly, structure complex answers and state uncertainty instead of inventing facts.""",

    "improve": """You are an expert editor.
Improve the user's text while preserving its original meaning.
Make it clear, natural, grammatically correct and appropriate for the requested audience and tone.""",

    "student": """You are a friendly tutor.
Teach step by step at the user's level. Use simple explanations, examples, key points and
practice questions when useful. Help the learner understand instead of only memorizing.""",
}

CV_SYSTEM_PROMPT = """You are a senior CV writer. You turn a candidate's raw facts into polished CV content.
Rules:
- Use ONLY facts supplied by the candidate. Never invent employers, dates, degrees, grades, certificates, skills, numbers or achievements.
- If a section has no supplied facts, return an empty list or empty string for it.
- Rewrite supplied tasks into concise, strong, action-led bullet points (max 5 per role, max ~22 words each). Do not add metrics that were not given.
- Write a 2-3 sentence professional summary suited to the target role, using only supplied facts.
- Keep dates and names exactly as supplied.
- Write in clear professional English.
- Reply with ONE valid JSON object only. No markdown, no code fences, no commentary."""

CV_SCHEMA = """{
  "headline": "short professional headline, e.g. 'Computer Science Student | Python & Web Development'",
  "summary": "2-3 sentence professional summary",
  "experience": [{"title": "", "company": "", "period": "", "bullets": ["", ""]}],
  "education": [{"degree": "", "institution": "", "period": "", "details": ""}],
  "skills": ["", ""],
  "projects": [{"name": "", "description": ""}],
  "certifications": ["", ""],
  "languages": ["", ""]
}"""

PALETTES = {
    "Emerald": "#0b6b4a",
    "Navy": "#1e3a5f",
    "Charcoal": "#2b2f36",
    "Burgundy": "#7a1f3d",
    "Teal": "#0f766e",
    "Indigo": "#3730a3",
}
CV_TEMPLATES = ["Modern Sidebar", "Classic Header", "ATS Minimal"]


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_STATE = {
    "selected_service": None,
    "language": "English",
    "result": "",
    "result_lang": "English",
    "result_version": 0,
    "history": [],
    "cv_data": None,
    "cv_version": 0,
    "cv_photo_raw": None,
}
for _k, _v in DEFAULT_STATE.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ============================================================
# STYLE
# ============================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Naskh+Arabic:wght@400;600;700&display=swap');

    :root {
        --green: #087443;
        --dark: #063d2b;
        --border: #dce9e1;
        --text: #173328;
        --muted: #687a71;
    }

    .stApp, button, input, textarea, select {
        font-family: Inter, "Noto Naskh Arabic", system-ui, sans-serif;
    }
    .stApp { background: linear-gradient(180deg, #f8fbf9 0%, #f1f6f3 100%); }
    [data-testid="stHeader"] { background: transparent; }
    footer, #MainMenu { visibility: hidden; }

    .block-container {
        max-width: 1180px;
        padding-top: 1rem;
        padding-bottom: 2.5rem;
    }

    /* ---------- top bar ---------- */
    .brand { display:flex; align-items:center; gap:.75rem; padding:.2rem 0 .6rem; }
    .brand-logo {
        width:46px; height:46px; border-radius:14px; flex:none;
        display:flex; align-items:center; justify-content:center;
        background: linear-gradient(135deg, #063d2b, #0f9d5f);
        box-shadow: 0 8px 20px rgba(6,61,43,.18);
    }
    .brand-title { color:var(--dark); font-size:1.08rem; font-weight:800; line-height:1.1; }
    .brand-sub { color:var(--muted); font-size:.76rem; margin-top:.2rem; }

    /* ---------- hero ---------- */
    .hero {
        position:relative; overflow:hidden;
        background: linear-gradient(135deg, #063d2b 0%, #087443 58%, #12a063 100%);
        color:white; border-radius:26px;
        padding: clamp(1.4rem, 4vw, 2.4rem);
        margin: .2rem 0 1.3rem;
        box-shadow: 0 18px 45px rgba(6,61,43,.16);
    }
    .hero:after {
        content:""; position:absolute; right:-60px; top:-60px; width:220px; height:220px;
        border-radius:50%; background: rgba(255,255,255,.07);
    }
    .hero h1 { color:white; font-size:clamp(1.6rem,4vw,2.5rem); margin:0 0 .4rem; line-height:1.12; font-weight:800; }
    .hero p { color:#e3f6ec; margin:0; font-size:.98rem; }

    .section-title { color:var(--dark); font-size:1.15rem; font-weight:800; margin:.8rem 0 .8rem; }

    /* ---------- service cards ---------- */
    .icon-tile { border-radius:14px; display:flex; align-items:center; justify-content:center; }
    .svc-name { color:var(--text); font-size:1rem; font-weight:750; margin:.7rem 0 .2rem; }
    .svc-short { color:var(--muted); font-size:.8rem; line-height:1.4; min-height:2.2em; }

    .st-key-svcgrid [data-testid="stVerticalBlockBorderWrapper"] {
        background:white; border:1px solid var(--border) !important; border-radius:20px;
        box-shadow:0 8px 26px rgba(10,50,30,.05);
        transition: transform .15s ease, box-shadow .15s ease;
    }
    .st-key-svcgrid [data-testid="stVerticalBlockBorderWrapper"]:hover {
        transform: translateY(-2px); box-shadow:0 14px 32px rgba(10,50,30,.10);
    }

    /* ---------- workspace ---------- */
    .ws-head {
        display:flex; align-items:center; gap:.9rem;
        background:white; border:1px solid var(--border); border-radius:20px;
        padding:1rem 1.1rem; margin:.2rem 0 1rem;
        box-shadow:0 8px 26px rgba(10,50,30,.05);
    }
    .ws-title { color:var(--dark); font-size:1.3rem; font-weight:800; line-height:1.15; }
    .ws-sub { color:var(--muted); font-size:.84rem; margin-top:.15rem; }

    .rtl { direction:rtl; text-align:right; font-family:"Noto Naskh Arabic", Inter, serif; font-size:1.08rem; line-height:2; }

    /* ---------- buttons / inputs ---------- */
    .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
        width:100%; border-radius:12px; min-height:2.75rem; font-weight:650;
        border:1px solid #bcd7c7;
    }
    .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"],
    .stFormSubmitButton > button, .stDownloadButton > button[kind="primary"] {
        background: linear-gradient(120deg, #087443, #075a37); color:white; border-color:#087443;
    }
    .stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
        transform: translateY(-1px); box-shadow:0 7px 18px rgba(8,116,67,.14);
    }
    div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > div, div[data-baseweb="select"] > div {
        border-radius:12px;
    }
    [data-testid="stExpander"] { border-radius:14px; border:1px solid var(--border); background:white; }
    [data-testid="stForm"] { border-radius:18px; border:1px solid var(--border); background:white; }

    .footer { text-align:center; color:#728078; font-size:.8rem; padding:1.4rem .5rem .2rem; line-height:1.7; }
    .footer .quote { color:var(--dark); font-weight:700; }

    /* ---------- mobile ---------- */
    @media (max-width: 760px) {
        .block-container { padding: .6rem .75rem 2rem; }
        .hero { border-radius:20px; padding:1.25rem 1.05rem; }
        .st-key-svcgrid [data-testid="stHorizontalBlock"],
        .st-key-dlgrid [data-testid="stHorizontalBlock"] { flex-wrap:wrap !important; gap:.6rem !important; }
        .st-key-svcgrid [data-testid="stColumn"], .st-key-svcgrid [data-testid="column"],
        .st-key-dlgrid [data-testid="stColumn"], .st-key-dlgrid [data-testid="column"] {
            flex: 1 1 calc(50% - .6rem) !important;
            min-width: calc(50% - .6rem) !important;
            width: calc(50% - .6rem) !important;
        }
        .svc-short { display:none; }
        .svc-name { font-size:.92rem; }
        .ws-head { padding:.85rem .9rem; }
        .ws-title { font-size:1.1rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS: LANGUAGE + AI
# ============================================================

def language_rule(language: str) -> str:
    if language == "اردو":
        return "Respond in natural Urdu script. Do not use Hindi/Devanagari."
    if language == "Roman Urdu":
        return "Respond in natural Roman Urdu using Latin letters. Do not use Hindi/Devanagari."
    return "Respond in clear natural English."


def clean_ai_text(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    return text.strip()


def call_ai(system: str, user: str, models: list, image_uri: Optional[str] = None,
            temperature: float = 0.4, max_tokens: int = 3000) -> str:
    """Try each model in order. Raises the last error if all fail."""
    client = Groq(api_key=API_KEY)
    last_error: Optional[Exception] = None

    for model in models:
        try:
            if image_uri:
                content = [
                    {"type": "text", "text": user},
                    {"type": "image_url", "image_url": {"url": image_uri}},
                ]
            else:
                content = user

            kwargs = dict(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": content},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if model.startswith("openai/gpt-oss"):
                kwargs["extra_body"] = {"reasoning_effort": "low"}

            response = client.chat.completions.create(**kwargs)
            text = clean_ai_text(response.choices[0].message.content)
            if text:
                return text
            last_error = RuntimeError(f"{model} returned an empty answer.")
        except Exception as exc:  # try next model
            last_error = exc

    raise last_error or RuntimeError("No model could answer.")


def translate_text(text: str, target: str) -> str:
    system = (
        "You are a professional translator. Convert the user's text into the requested language. "
        "Keep the meaning, structure, markdown formatting, names, numbers and links unchanged. "
        "Output only the converted text, no commentary. " + language_rule(target)
    )
    return call_ai(system, text[:MAX_ATTACHMENT_CHARS], TEXT_MODELS, temperature=0.2, max_tokens=3500)


def show_ai_error(exc: Exception):
    message = str(exc).lower()
    if "429" in message or "rate_limit" in message or "rate limit" in message:
        st.error("Groq free-tier limit reached. Please wait a minute and try again.")
    elif "401" in message or "authentication" in message or "invalid_api_key" in message:
        st.error("Groq API key was rejected. Check GROQ_API_KEY in Streamlit Secrets.")
    elif "413" in message or "too large" in message or "reduce your message" in message:
        st.error("The input is too long for the free tier. Use shorter text or a smaller file.")
    elif "model" in message and ("not found" in message or "decommission" in message
                                  or "does not exist" in message or "no access" in message):
        st.error(
            "The AI model is unavailable. Groq changes models often. "
            "Set TEXT_MODELS / VISION_MODELS in Streamlit Secrets to current model names."
        )
    elif "400" in message or "bad request" in message:
        st.error("The AI request was rejected. Check the file type/size and try again.")
    else:
        st.error("The AI request could not be completed.")
    with st.expander("Technical details"):
        st.caption(str(exc))


def is_rtl_text(text: str) -> bool:
    letters = re.sub(r"\s", "", text)
    if not letters:
        return False
    return len(AR_RE.findall(letters)) > 0.3 * len(letters)


# ============================================================
# HELPERS: FILES / PHOTO
# ============================================================

def keyed_container(key: str):
    try:
        return st.container(key=key)
    except TypeError:  # older Streamlit
        return st.container()


def attachment_input(service_key: str, title: str, modes: Optional[list] = None):
    """Optional attachment. Camera opens only if the user picks it."""
    modes = modes or ["None", "Take Photo", "Image File", "PDF", "DOCX", "TXT"]
    selected, kind, extracted = None, None, ""

    with st.expander(f"Attach: {title}", expanded=False):
        mode = st.radio(
            "Add something",
            modes,
            horizontal=True,
            key=f"attachment_mode_{service_key}",
            label_visibility="collapsed",
        )

        if mode == "Take Photo":
            st.caption("Camera is requested only after you choose this option.")
            selected = st.camera_input("Take photo", key=f"camera_{service_key}")
            if selected is not None:
                kind = "image"

        elif mode == "Image File":
            selected = st.file_uploader(
                "Choose an image", type=["jpg", "jpeg", "png", "webp"],
                key=f"image_upload_{service_key}",
            )
            if selected is not None:
                kind = "image"
                st.image(selected, caption="Selected image", width=260)

        elif mode == "PDF":
            selected = st.file_uploader("Choose a PDF", type=["pdf"], key=f"pdf_upload_{service_key}")
            if selected is not None:
                kind = "document"
                try:
                    reader = PdfReader(selected)
                    pages = [(p.extract_text() or "") for p in reader.pages[:20]]
                    extracted = "\n\n".join(pages).strip()
                    if extracted:
                        st.success(f"PDF attached ({len(reader.pages)} page(s))")
                    else:
                        st.warning("This PDF looks scanned. Use Image File or Take Photo instead.")
                except Exception:
                    st.error("This PDF could not be read.")

        elif mode == "DOCX":
            selected = st.file_uploader("Choose a DOCX", type=["docx"], key=f"docx_upload_{service_key}")
            if selected is not None:
                kind = "document"
                try:
                    doc = Document(io.BytesIO(selected.getvalue()))
                    extracted = "\n".join(p.text for p in doc.paragraphs if p.text.strip()).strip()
                    st.success("DOCX attached.")
                except Exception:
                    st.error("This DOCX could not be read.")

        elif mode == "TXT":
            selected = st.file_uploader("Choose a TXT", type=["txt"], key=f"txt_upload_{service_key}")
            if selected is not None:
                kind = "document"
                try:
                    extracted = selected.getvalue().decode("utf-8", errors="replace").strip()
                    st.success("TXT attached.")
                except Exception:
                    st.error("This TXT could not be read.")

        if selected is not None and kind == "image":
            st.success("Image attached.")

    return selected, kind, extracted


def make_circle_photo(raw: bytes, size: int = 420) -> Optional[bytes]:
    """Centre-crop to a square (biased upward for faces) and mask to a circle."""
    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
        w, h = img.size
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 4 if h > w else 0
        img = img.crop((left, top, left + side, top + side)).resize((size, size), Image.LANCZOS)

        scale = 4
        mask = Image.new("L", (size * scale, size * scale), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size * scale - 1, size * scale - 1), fill=255)
        mask = mask.resize((size, size), Image.LANCZOS)

        img.putalpha(mask)
        out = io.BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()
    except Exception:
        return None


# ============================================================
# CV DATA
# ============================================================

def _s(value) -> str:
    return str(value).strip() if value is not None else ""


def _str_list(value) -> list:
    if isinstance(value, str):
        value = re.split(r"[\n;•]+|,\s*", value)
    if not isinstance(value, list):
        return []
    return [_s(v) for v in value if _s(v)]


def parse_json_object(text: str) -> dict:
    text = clean_ai_text(text)
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON found in the AI answer.")
    return json.loads(text[start:end + 1])


def normalize_cv(raw: dict, form: dict) -> dict:
    experience, education, projects = [], [], []

    for e in raw.get("experience") or []:
        if isinstance(e, dict):
            experience.append({
                "title": _s(e.get("title")),
                "company": _s(e.get("company")),
                "period": _s(e.get("period")),
                "bullets": _str_list(e.get("bullets")),
            })
    for e in raw.get("education") or []:
        if isinstance(e, dict):
            education.append({
                "degree": _s(e.get("degree")),
                "institution": _s(e.get("institution")),
                "period": _s(e.get("period")),
                "details": _s(e.get("details")),
            })
    for p in raw.get("projects") or []:
        if isinstance(p, dict):
            projects.append({"name": _s(p.get("name")), "description": _s(p.get("description"))})
        elif _s(p):
            projects.append({"name": "", "description": _s(p)})

    return {
        # Contact details always come from the form, never from the AI.
        "name": form["name"],
        "phone": form["phone"],
        "email": form["email"],
        "location": form["location"],
        "links": form["links"],
        "headline": _s(raw.get("headline")) or form["role"],
        "summary": _s(raw.get("summary")),
        "experience": experience,
        "education": education,
        "skills": _str_list(raw.get("skills")),
        "projects": projects,
        "certifications": _str_list(raw.get("certifications")),
        "languages": _str_list(raw.get("languages")),
    }


def cv_contact_parts(d: dict) -> list:
    return [x for x in [d["phone"], d["email"], d["location"], d["links"]] if x]


# ------------------------------------------------------------
# CV: HTML preview
# ------------------------------------------------------------

CV_CSS = """
*{box-sizing:border-box}
body{margin:0;background:#e9efec;font-family:Inter,'Segoe UI',Arial,sans-serif;color:#374151;padding:14px}
.page{max-width:840px;margin:0 auto;background:#fff;box-shadow:0 10px 30px rgba(0,0,0,.12);border-radius:8px;overflow:hidden}
h1{margin:0;font-size:30px;line-height:1.1;color:#111827}
.hl{color:__ACC__;font-weight:600;margin:6px 0 0;font-size:15px}
h3{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:__ACC__;margin:20px 0 8px;padding-bottom:5px;border-bottom:1.5px solid __ACC__}
p{margin:0 0 6px;font-size:13.5px;line-height:1.55}
.row{display:flex;justify-content:space-between;gap:10px;align-items:baseline}
.row b{color:#111827;font-size:14px}
.per{color:#6b7280;font-size:12px;white-space:nowrap}
.sub{color:#6b7280;font-size:13px;margin-bottom:3px}
ul{margin:4px 0 10px 18px;padding:0}
li{font-size:13.2px;line-height:1.5;margin-bottom:2px}
.item{margin-bottom:10px}
.sb{display:flex}
.sb aside{width:31%;background:__ACC__;color:#fff;padding:28px 20px}
.sb main{flex:1;padding:30px 28px}
.sb aside h3{color:#fff;border-bottom:1px solid rgba(255,255,255,.35);margin-top:22px}
.sb aside p,.sb aside li{color:#eef5f1;font-size:12.5px;word-break:break-word}
.sb aside small{display:block;opacity:.75;font-size:10.5px;text-transform:uppercase;letter-spacing:.08em}
.photo{width:128px;height:128px;border-radius:50%;border:4px solid #fff;display:block;margin:0 auto 6px;object-fit:cover}
.hd{background:__ACC__;color:#fff;padding:26px 30px;display:flex;justify-content:space-between;align-items:center;gap:16px}
.hd h1{color:#fff}
.hd .hl{color:#e8f0ec}
.hd .ct{margin-top:10px;font-size:12px;color:#e8f0ec;line-height:1.6}
.hd .photo{margin:0;width:104px;height:104px;flex:none}
.bd{padding:6px 30px 28px}
.ats{padding:30px 34px}
.ats .top{text-align:center}
.ats h3{color:#111827;border-bottom-color:#111827}
.ats .hl{color:#374151}
@media(max-width:620px){.sb{flex-direction:column}.sb aside{width:100%}.hd{flex-direction:column-reverse;align-items:flex-start}}
"""


def _e(value) -> str:
    return html_lib.escape(_s(value))


def _html_main_sections(d: dict, include_side: bool) -> str:
    out = []
    if d["summary"]:
        out.append(f"<h3>Profile</h3><p>{_e(d['summary'])}</p>")
    if d["experience"]:
        out.append("<h3>Experience</h3>")
        for x in d["experience"]:
            bullets = "".join(f"<li>{_e(b)}</li>" for b in x["bullets"])
            out.append(
                f'<div class="item"><div class="row"><b>{_e(x["title"])}</b><span class="per">{_e(x["period"])}</span></div>'
                f'<div class="sub">{_e(x["company"])}</div>{"<ul>" + bullets + "</ul>" if bullets else ""}</div>'
            )
    if d["education"]:
        out.append("<h3>Education</h3>")
        for x in d["education"]:
            out.append(
                f'<div class="item"><div class="row"><b>{_e(x["degree"])}</b><span class="per">{_e(x["period"])}</span></div>'
                f'<div class="sub">{_e(x["institution"])}</div>'
                f'{"<p>" + _e(x["details"]) + "</p>" if x["details"] else ""}</div>'
            )
    if include_side and d["skills"]:
        out.append(f"<h3>Skills</h3><p>{' &bull; '.join(_e(s) for s in d['skills'])}</p>")
    if d["projects"]:
        out.append("<h3>Projects</h3>")
        for x in d["projects"]:
            out.append(
                f'<div class="item">{"<b>" + _e(x["name"]) + "</b>" if x["name"] else ""}'
                f'<p>{_e(x["description"])}</p></div>'
            )
    if d["certifications"]:
        out.append("<h3>Certifications</h3><ul>" + "".join(f"<li>{_e(c)}</li>" for c in d["certifications"]) + "</ul>")
    if include_side and d["languages"]:
        out.append(f"<h3>Languages</h3><p>{' &bull; '.join(_e(s) for s in d['languages'])}</p>")
    return "".join(out)


def cv_html(d: dict, photo: Optional[bytes], template: str, accent: str) -> str:
    photo_tag = ""
    if photo:
        uri = "data:image/png;base64," + base64.b64encode(photo).decode()
        photo_tag = f'<img class="photo" src="{uri}" alt="photo">'

    css = CV_CSS.replace("__ACC__", accent)

    if template == "Modern Sidebar":
        side = [photo_tag, "<h3>Contact</h3>"]
        for label, val in [("Phone", d["phone"]), ("Email", d["email"]),
                           ("Location", d["location"]), ("Link", d["links"])]:
            if val:
                side.append(f"<p><small>{label}</small>{_e(val)}</p>")
        if d["skills"]:
            side.append("<h3>Skills</h3><ul>" + "".join(f"<li>{_e(s)}</li>" for s in d["skills"]) + "</ul>")
        if d["languages"]:
            side.append("<h3>Languages</h3><ul>" + "".join(f"<li>{_e(s)}</li>" for s in d["languages"]) + "</ul>")
        body = (
            f'<div class="page sb"><aside>{"".join(side)}</aside><main>'
            f'<h1>{_e(d["name"])}</h1><div class="hl">{_e(d["headline"])}</div>'
            f'{_html_main_sections(d, include_side=False)}</main></div>'
        )
    elif template == "Classic Header":
        contact = " &nbsp;|&nbsp; ".join(_e(x) for x in cv_contact_parts(d))
        body = (
            f'<div class="page"><div class="hd"><div><h1>{_e(d["name"])}</h1>'
            f'<div class="hl">{_e(d["headline"])}</div><div class="ct">{contact}</div></div>{photo_tag}</div>'
            f'<div class="bd">{_html_main_sections(d, include_side=True)}</div></div>'
        )
    else:
        contact = " &nbsp;|&nbsp; ".join(_e(x) for x in cv_contact_parts(d))
        body = (
            f'<div class="page ats"><div class="top"><h1>{_e(d["name"])}</h1>'
            f'<div class="hl">{_e(d["headline"])}</div><p style="margin-top:8px">{contact}</p></div>'
            f'{_html_main_sections(d, include_side=True)}</div>'
        )

    return f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><style>{css}</style></head><body>{body}</body></html>"


# ------------------------------------------------------------
# CV: PDF
# ------------------------------------------------------------

def _pdf_styles(accent: str) -> dict:
    ac = HexColor(accent)
    dark, grey, body_c = HexColor("#111827"), HexColor("#6b7280"), HexColor("#374151")
    S = {}
    S["name"] = ParagraphStyle("cv_name", fontName="Helvetica-Bold", fontSize=25, leading=28, textColor=dark)
    S["headline"] = ParagraphStyle("cv_headline", fontName="Helvetica", fontSize=11.5, leading=15, textColor=ac, spaceAfter=4)
    S["sec"] = ParagraphStyle("cv_sec", fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=ac, spaceBefore=11, spaceAfter=2)
    S["body"] = ParagraphStyle("cv_body", fontName="Helvetica", fontSize=9.6, leading=13.4, textColor=body_c)
    S["bullet"] = ParagraphStyle("cv_bullet", parent=S["body"], leftIndent=11, bulletIndent=0, spaceAfter=1.5)
    S["role"] = ParagraphStyle("cv_role", fontName="Helvetica-Bold", fontSize=10.4, leading=13, textColor=dark)
    S["meta"] = ParagraphStyle("cv_meta", fontName="Helvetica", fontSize=9.2, leading=12, textColor=grey, spaceAfter=2)
    S["per"] = ParagraphStyle("cv_per", fontName="Helvetica", fontSize=8.8, leading=12, textColor=grey, alignment=TA_RIGHT)
    S["center"] = ParagraphStyle("cv_center", fontName="Helvetica", fontSize=9.4, leading=13, textColor=body_c, alignment=TA_CENTER)
    S["center_name"] = ParagraphStyle("cv_cname", parent=S["name"], alignment=TA_CENTER, fontSize=23)
    S["center_head"] = ParagraphStyle("cv_chead", parent=S["headline"], alignment=TA_CENTER, textColor=body_c)
    S["sbh"] = ParagraphStyle("cv_sbh", fontName="Helvetica-Bold", fontSize=9.2, leading=12, textColor=white, spaceBefore=14, spaceAfter=5)
    S["sbt"] = ParagraphStyle("cv_sbt", fontName="Helvetica", fontSize=9, leading=12.4, textColor=HexColor("#eaf2ee"), spaceAfter=5, wordWrap="CJK")
    S["sbb"] = ParagraphStyle("cv_sbb", parent=S["sbt"], leftIndent=9, bulletIndent=0, spaceAfter=2.5)
    return S


def _esc(v) -> str:
    return xml_escape(_s(v))


def _sec_head(title: str, S: dict, accent: str) -> list:
    return [
        Paragraph(title.upper(), S["sec"]),
        HRFlowable(width="100%", thickness=0.8, color=HexColor(accent), spaceBefore=1, spaceAfter=5),
    ]


def _row(left: str, right: str, S: dict, width: float):
    table = Table([[Paragraph(left, S["role"]), Paragraph(right, S["per"])]], colWidths=[width * 0.72, width * 0.28])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return table


def _pdf_main_flow(d: dict, S: dict, accent: str, width: float, include_side: bool) -> list:
    flow = []
    if d["summary"]:
        flow += _sec_head("Profile", S, accent) + [Paragraph(_esc(d["summary"]), S["body"])]

    if d["experience"]:
        flow += _sec_head("Experience", S, accent)
        for x in d["experience"]:
            items = [_row(_esc(x["title"]), _esc(x["period"]), S, width)]
            if x["company"]:
                items.append(Paragraph(_esc(x["company"]), S["meta"]))
            for b in x["bullets"]:
                items.append(Paragraph(_esc(b), S["bullet"], bulletText="•"))
            items.append(Spacer(1, 5))
            flow.append(KeepTogether(items))

    if d["education"]:
        flow += _sec_head("Education", S, accent)
        for x in d["education"]:
            items = [_row(_esc(x["degree"]), _esc(x["period"]), S, width)]
            if x["institution"]:
                items.append(Paragraph(_esc(x["institution"]), S["meta"]))
            if x["details"]:
                items.append(Paragraph(_esc(x["details"]), S["body"]))
            items.append(Spacer(1, 5))
            flow.append(KeepTogether(items))

    if include_side and d["skills"]:
        flow += _sec_head("Skills", S, accent) + [Paragraph("  •  ".join(_esc(s) for s in d["skills"]), S["body"])]

    if d["projects"]:
        flow += _sec_head("Projects", S, accent)
        for x in d["projects"]:
            items = []
            if x["name"]:
                items.append(Paragraph(_esc(x["name"]), S["role"]))
            if x["description"]:
                items.append(Paragraph(_esc(x["description"]), S["body"]))
            items.append(Spacer(1, 5))
            flow.append(KeepTogether(items))

    if d["certifications"]:
        flow += _sec_head("Certifications", S, accent)
        for c in d["certifications"]:
            flow.append(Paragraph(_esc(c), S["bullet"], bulletText="•"))

    if include_side and d["languages"]:
        flow += _sec_head("Languages", S, accent) + [Paragraph("  •  ".join(_esc(s) for s in d["languages"]), S["body"])]

    return flow


def _draw_photo(c, photo: bytes, cx: float, cy: float, r: float):
    c.setFillColor(white)
    c.circle(cx, cy, r + 3, stroke=0, fill=1)
    c.drawImage(ImageReader(io.BytesIO(photo)), cx - r, cy - r, 2 * r, 2 * r, mask="auto")


def build_cv_pdf(d: dict, photo: Optional[bytes], template: str, accent: str) -> bytes:
    buf = io.BytesIO()
    W, H = A4
    S = _pdf_styles(accent)
    ac = HexColor(accent)

    doc = BaseDocTemplate(
        buf, pagesize=A4, leftMargin=0, rightMargin=0, topMargin=0, bottomMargin=0,
        title=f"{d['name']} - CV", author=d["name"],
    )

    def frame(x, y, w, h, fid):
        return Frame(x, y, w, h, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id=fid)

    if template == "Modern Sidebar":
        SB = 205
        r = 55
        top_offset = 40 + (2 * r + 26 if photo else 0)
        main_w = W - SB - 26 - 30

        def sidebar_band(c):
            c.setFillColor(ac)
            c.rect(0, 0, SB, H, stroke=0, fill=1)

        def on_first(c, _doc):
            c.saveState()
            sidebar_band(c)
            if photo:
                _draw_photo(c, photo, SB / 2, H - 36 - r, r)
            c.restoreState()

        def on_later(c, _doc):
            c.saveState()
            sidebar_band(c)
            c.restoreState()

        doc.addPageTemplates([
            PageTemplate("first", [frame(22, 30, SB - 44, H - 30 - top_offset, "side"),
                                   frame(SB + 26, 30, main_w, H - 30 - 38, "main1")], onPage=on_first),
            PageTemplate("later", [frame(SB + 26, 30, main_w, H - 60, "main2")], onPage=on_later),
        ])

        side = [Paragraph("CONTACT", S["sbh"])]
        for label, val in [("Phone", d["phone"]), ("Email", d["email"]),
                           ("Location", d["location"]), ("Link", d["links"])]:
            if val:
                side.append(Paragraph(f"<b>{label}</b><br/>{_esc(val)}", S["sbt"]))
        if d["skills"]:
            side.append(Paragraph("SKILLS", S["sbh"]))
            side += [Paragraph(_esc(s), S["sbb"], bulletText="•") for s in d["skills"]]
        if d["languages"]:
            side.append(Paragraph("LANGUAGES", S["sbh"]))
            side += [Paragraph(_esc(s), S["sbb"], bulletText="•") for s in d["languages"]]

        main = [
            Paragraph(_esc(d["name"]), S["name"]),
            Paragraph(_esc(d["headline"]), S["headline"]),
            HRFlowable(width="100%", thickness=1.6, color=ac, spaceBefore=2, spaceAfter=2),
        ] + _pdf_main_flow(d, S, accent, main_w, include_side=False)

        story = [NextPageTemplate("later")] + side + [FrameBreak()] + main

    elif template == "Classic Header":
        M = 40
        band_h = 128 if photo else 112
        content_w = W - 2 * M

        def on_first(c, _doc):
            c.saveState()
            c.setFillColor(ac)
            c.rect(0, H - band_h, W, band_h, stroke=0, fill=1)
            avail = content_w - (112 if photo else 0)

            size = 26
            while stringWidth(d["name"], "Helvetica-Bold", size) > avail and size > 14:
                size -= 1
            c.setFillColor(white)
            c.setFont("Helvetica-Bold", size)
            c.drawString(M, H - 52, d["name"])

            hsize = 11.5
            while stringWidth(d["headline"], "Helvetica", hsize) > avail and hsize > 8:
                hsize -= 0.5
            c.setFillColor(HexColor("#e8f0ec"))
            c.setFont("Helvetica", hsize)
            c.drawString(M, H - 72, d["headline"])

            c.setFont("Helvetica", 9)
            lines = simpleSplit("   |   ".join(cv_contact_parts(d)), "Helvetica", 9, avail)
            for i, line in enumerate(lines[:2]):
                c.drawString(M, H - 92 - i * 12, line)

            if photo:
                _draw_photo(c, photo, W - M - 42, H - band_h / 2, 40)
            c.restoreState()

        doc.addPageTemplates([
            PageTemplate("first", [frame(M, 30, content_w, H - 30 - band_h - 12, "c1")], onPage=on_first),
            PageTemplate("later", [frame(M, 30, content_w, H - 60, "c2")]),
        ])
        story = [NextPageTemplate("later")] + _pdf_main_flow(d, S, accent, content_w, include_side=True)

    else:  # ATS Minimal
        M = 44
        content_w = W - 2 * M
        doc.addPageTemplates([PageTemplate("only", [frame(M, 38, content_w, H - 76, "ats")])])
        story = [
            Paragraph(_esc(d["name"]), S["center_name"]),
            Paragraph(_esc(d["headline"]), S["center_head"]),
            Paragraph(" &nbsp;|&nbsp; ".join(_esc(x) for x in cv_contact_parts(d)), S["center"]),
            Spacer(1, 4),
        ] + _pdf_main_flow(d, S, "#111827", content_w, include_side=True)

    doc.build(story)
    return buf.getvalue()


# ------------------------------------------------------------
# CV: DOCX (editable)
# ------------------------------------------------------------

def _docx_bottom_border(paragraph, hex_color: str):
    pPr = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "8")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), hex_color.lstrip("#"))
    borders.append(bottom)
    pPr.append(borders)


def _rgb(hex_color: str) -> RGBColor:
    h = hex_color.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def build_cv_docx(d: dict, photo: Optional[bytes], template: str, accent: str) -> bytes:
    use_accent = "#111827" if template == "ATS Minimal" else accent
    document = Document()
    section = document.sections[0]
    section.left_margin = section.right_margin = Inches(0.8)
    section.top_margin = section.bottom_margin = Inches(0.7)

    normal = document.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)

    show_photo = bool(photo) and template != "ATS Minimal"

    table = document.add_table(rows=1, cols=2)
    table.autofit = False
    left, right = table.rows[0].cells
    left.width, right.width = Inches(5.0), Inches(1.9)

    p = left.paragraphs[0]
    run = p.add_run(d["name"])
    run.bold = True
    run.font.size = Pt(24)
    run.font.color.rgb = _rgb(use_accent)

    p2 = left.add_paragraph()
    r2 = p2.add_run(d["headline"])
    r2.font.size = Pt(12)
    r2.font.color.rgb = RGBColor(0x37, 0x41, 0x51)

    p3 = left.add_paragraph()
    r3 = p3.add_run("  |  ".join(cv_contact_parts(d)))
    r3.font.size = Pt(9.5)
    r3.font.color.rgb = RGBColor(0x6B, 0x72, 0x80)

    if show_photo:
        rp = right.paragraphs[0]
        rp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        rp.add_run().add_picture(io.BytesIO(photo), width=Inches(1.25))

    def heading(text: str):
        h = document.add_paragraph()
        _docx_bottom_border(h, use_accent)  # add border first to keep XML order valid
        h.paragraph_format.space_before = Pt(12)
        h.paragraph_format.space_after = Pt(4)
        rr = h.add_run(text.upper())
        rr.bold = True
        rr.font.size = Pt(10.5)
        rr.font.color.rgb = _rgb(use_accent)

    def bullet(text: str):
        bp = document.add_paragraph(style="List Bullet")
        bp.paragraph_format.space_after = Pt(1)
        bp.add_run(text)

    def title_line(title: str, period: str):
        tp = document.add_paragraph()
        tp.paragraph_format.space_after = Pt(0)
        a = tp.add_run(title)
        a.bold = True
        if period:
            b = tp.add_run(f"    {period}")
            b.font.size = Pt(9.5)
            b.font.color.rgb = RGBColor(0x6B, 0x72, 0x80)

    def sub_line(text: str):
        if text:
            sp = document.add_paragraph()
            sp.paragraph_format.space_after = Pt(2)
            sr = sp.add_run(text)
            sr.font.size = Pt(10)
            sr.font.color.rgb = RGBColor(0x6B, 0x72, 0x80)

    if d["summary"]:
        heading("Profile")
        document.add_paragraph(d["summary"])
    if d["experience"]:
        heading("Experience")
        for x in d["experience"]:
            title_line(x["title"], x["period"])
            sub_line(x["company"])
            for b in x["bullets"]:
                bullet(b)
    if d["education"]:
        heading("Education")
        for x in d["education"]:
            title_line(x["degree"], x["period"])
            sub_line(x["institution"])
            if x["details"]:
                document.add_paragraph(x["details"])
    if d["skills"]:
        heading("Skills")
        document.add_paragraph("  •  ".join(d["skills"]))
    if d["projects"]:
        heading("Projects")
        for x in d["projects"]:
            if x["name"]:
                title_line(x["name"], "")
            if x["description"]:
                document.add_paragraph(x["description"])
    if d["certifications"]:
        heading("Certifications")
        for c in d["certifications"]:
            bullet(c)
    if d["languages"]:
        heading("Languages")
        document.add_paragraph("  •  ".join(d["languages"]))

    out = io.BytesIO()
    document.save(out)
    return out.getvalue()


# ============================================================
# RESULT EXPORT (TXT / PDF / DOCX)
# ============================================================

_URDU_OK: Optional[bool] = None


def urdu_pdf_ready() -> bool:
    """Urdu in PDF needs a TTF font in ./fonts plus arabic-reshaper + python-bidi."""
    global _URDU_OK
    if _URDU_OK is not None:
        return _URDU_OK
    _URDU_OK = False
    if arabic_reshaper is None or get_display is None:
        return False
    base = os.path.dirname(os.path.abspath(__file__))
    for name in ["NotoNaskhArabic-Regular.ttf", "NotoNastaliqUrdu-Regular.ttf", "Amiri-Regular.ttf"]:
        path = os.path.join(base, "fonts", name)
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("UrduFont", path))
                _URDU_OK = True
                break
            except Exception:
                continue
    return _URDU_OK


def _strip_md(line: str) -> str:
    line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
    line = re.sub(r"`([^`]*)`", r"\1", line)
    return re.sub(r"^\s*(#{1,6}\s+|[-*•]\s+)", "", line)


def _md_inline(escaped: str) -> str:
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    return escaped.replace("`", "")


def build_text_pdf(title: str, text: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=48, leftMargin=48, topMargin=48, bottomMargin=48,
                            title=title)
    styles = getSampleStyleSheet()
    s_title = ParagraphStyle("t", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=17, leading=21,
                             alignment=TA_LEFT, textColor=HexColor("#063d2b"), spaceAfter=3)
    s_meta = ParagraphStyle("m", fontName="Helvetica", fontSize=8.5, leading=11, textColor=HexColor("#6b7280"), spaceAfter=10)
    s_body = ParagraphStyle("b", fontName="Helvetica", fontSize=10.3, leading=15, textColor=HexColor("#1f2937"), spaceAfter=4)
    s_head = ParagraphStyle("h", parent=s_body, fontName="Helvetica-Bold", fontSize=12.2, leading=16,
                            textColor=HexColor("#063d2b"), spaceBefore=8, spaceAfter=3)
    s_bul = ParagraphStyle("bl", parent=s_body, leftIndent=13, bulletIndent=2, spaceAfter=2)
    s_rtl = ParagraphStyle("r", parent=s_body, fontName="UrduFont" if urdu_pdf_ready() else "Helvetica",
                           alignment=TA_RIGHT, leading=20, fontSize=11.5)

    story = [
        Paragraph(xml_escape(title), s_title),
        HRFlowable(width="100%", thickness=1.2, color=HexColor("#087443"), spaceAfter=4),
        Paragraph("Balochistan AI Assistant · " + datetime.now().strftime("%d %b %Y, %I:%M %p"), s_meta),
    ]

    for raw in text.split("\n"):
        line = raw.rstrip()
        if not line.strip():
            story.append(Spacer(1, 5))
            continue

        if AR_RE.search(line) and urdu_pdf_ready():
            shaped = get_display(arabic_reshaper.reshape(_strip_md(line)))
            story.append(Paragraph(xml_escape(shaped), s_rtl))
            continue

        heading = re.match(r"^#{1,6}\s+(.*)", line)
        bullet = re.match(r"^\s*[-*•]\s+(.*)", line)
        if heading:
            story.append(Paragraph(_md_inline(xml_escape(heading.group(1))), s_head))
        elif bullet:
            story.append(Paragraph(_md_inline(xml_escape(bullet.group(1))), s_bul, bulletText="•"))
        else:
            story.append(Paragraph(_md_inline(xml_escape(line)), s_body))

    doc.build(story)
    return buf.getvalue()


def _docx_runs(paragraph, text: str):
    for i, part in enumerate(re.split(r"\*\*", text)):
        if part:
            run = paragraph.add_run(part.replace("`", ""))
            run.bold = (i % 2 == 1)


def build_text_docx(title: str, text: str) -> bytes:
    document = Document()
    document.add_heading(title, 0)
    meta = document.add_paragraph("Balochistan AI Assistant · " + datetime.now().strftime("%d %b %Y, %I:%M %p"))
    meta.runs[0].font.size = Pt(9)

    for raw in text.split("\n"):
        line = raw.rstrip()
        if not line.strip():
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)", line)
        bullet = re.match(r"^\s*[-*•]\s+(.*)", line)
        if heading:
            document.add_heading(heading.group(2).replace("**", ""), min(len(heading.group(1)), 3))
        elif bullet:
            p = document.add_paragraph(style="List Bullet")
            _docx_runs(p, bullet.group(1))
            if AR_RE.search(line):
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        else:
            p = document.add_paragraph()
            _docx_runs(p, line)
            if AR_RE.search(line):
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    out = io.BytesIO()
    document.save(out)
    return out.getvalue()


def safe_filename(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", text.lower()).strip("_") or "file"


# ============================================================
# TOP BAR
# ============================================================

top1, top2 = st.columns([4.2, 1.6])

with top1:
    st.markdown(
        f"""
        <div class="brand">
            <div class="brand-logo">{icon_svg("general", 24, "#ffffff")}</div>
            <div>
                <div class="brand-title">Balochistan AI Assistant</div>
                <div class="brand-sub">Learning • Work • Everyday Help</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with top2:
    st.selectbox("Language", LANGUAGES, key="language", label_visibility="collapsed")

language = st.session_state.language


# ============================================================
# HOME
# ============================================================

if st.session_state.selected_service is None:
    st.markdown(
        """
        <div class="hero">
            <h1>What do you need today?</h1>
            <p>Pick a tool. Everything works in English, اردو and Roman Urdu.</p>
        </div>
        <div class="section-title">Choose a service</div>
        """,
        unsafe_allow_html=True,
    )

    keys = list(SERVICES.keys())
    with keyed_container("svcgrid"):
        for start in range(0, len(keys), 4):
            cols = st.columns(4, gap="small")
            for col, key in zip(cols, keys[start:start + 4]):
                info = SERVICES[key]
                with col:
                    with st.container(border=True):
                        st.markdown(
                            f"""
                            {icon_tile(key, 48)}
                            <div class="svc-name">{info['title']}</div>
                            <div class="svc-short">{info['short']}</div>
                            """,
                            unsafe_allow_html=True,
                        )
                        if st.button("Open", key=f"open_{key}"):
                            st.session_state.selected_service = key
                            st.session_state.result = ""
                            st.rerun()

    if st.session_state.history:
        st.write("")
        with st.expander("Recent results"):
            labels = [f"{h['service']} · {h['time']}" for h in st.session_state.history]
            pick = st.selectbox("Previous results", labels, label_visibility="collapsed")
            st.markdown(st.session_state.history[labels.index(pick)]["result"])


# ============================================================
# SERVICE WORKSPACE
# ============================================================

else:
    service_key = st.session_state.selected_service
    service = SERVICES[service_key]

    back_col, _spacer = st.columns([1.3, 5])
    with back_col:
        if st.button("← All Services"):
            st.session_state.selected_service = None
            st.session_state.result = ""
            st.rerun()

    st.markdown(
        f"""
        <div class="ws-head">
            {icon_tile(service_key, 52)}
            <div>
                <div class="ws-title">{service['title']}</div>
                <div class="ws-sub">{service['short']}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # CV BUILDER (structured, designed, with photo)
    # --------------------------------------------------------
    if service_key == "cv":
        st.markdown("##### Profile photo")
        photo_mode = st.radio(
            "Photo", ["No photo", "Upload photo", "Take photo"], horizontal=True,
            label_visibility="collapsed", key="cv_photo_mode",
        )
        raw_photo = None
        if photo_mode == "Upload photo":
            up = st.file_uploader("Choose a photo", type=["jpg", "jpeg", "png", "webp"], key="cv_photo_upload")
            raw_photo = up.getvalue() if up is not None else None
        elif photo_mode == "Take photo":
            cam = st.camera_input("Take photo", key="cv_photo_camera")
            raw_photo = cam.getvalue() if cam is not None else None
        st.session_state.cv_photo_raw = raw_photo

        if raw_photo:
            preview = make_circle_photo(raw_photo, 240)
            if preview:
                st.image(preview, width=110)
            st.caption("Tip: a clear, front-facing photo with a plain background looks best.")

        _doc_file, _doc_kind, cv_doc_text = attachment_input(
            "cv", "existing CV or document (optional)", modes=["None", "PDF", "DOCX", "TXT"]
        )

        with st.form("cv_form"):
            c1, c2 = st.columns(2)
            with c1:
                full_name = st.text_input("Full name")
                phone = st.text_input("Phone")
                email = st.text_input("Email")
                city = st.text_input("City / Country")
            with c2:
                target_role = st.text_input("Target role", placeholder="e.g. Software Developer Intern")
                linkedin = st.text_input("LinkedIn / portfolio (optional)")
                languages_spoken = st.text_input("Languages", placeholder="Urdu, English, Balochi")
                certs = st.text_input("Certifications (optional)")

            education = st.text_area("Education", height=110,
                                     placeholder="Degree, university, years, CGPA (if you want it shown)")
            experience = st.text_area("Experience", height=120,
                                      placeholder="Company, role, dates and what you did. Leave empty if none.")
            skills = st.text_area("Skills", height=90, placeholder="Python, C++, HTML, CSS, SQL, communication...")
            projects = st.text_area("Projects / achievements", height=110,
                                    placeholder="Project name and what you built or achieved")
            notes = st.text_area("Anything else for the summary? (optional)", height=70)

            submitted = st.form_submit_button("Create my CV")

        if submitted:
            if not (full_name.strip() and (education + skills + experience + projects + target_role + cv_doc_text).strip()):
                st.warning("Please enter your name and at least some details (education, skills, role...).")
            elif not API_KEY:
                st.error("GROQ_API_KEY is not configured. Add it in Streamlit Cloud → Settings → Secrets.")
            else:
                user_prompt = (
                    f"TARGET ROLE: {target_role or 'Not specified'}\n\n"
                    f"EDUCATION (candidate facts):\n{education or '-'}\n\n"
                    f"EXPERIENCE (candidate facts):\n{experience or '-'}\n\n"
                    f"SKILLS (candidate facts):\n{skills or '-'}\n\n"
                    f"PROJECTS / ACHIEVEMENTS (candidate facts):\n{projects or '-'}\n\n"
                    f"CERTIFICATIONS: {certs or '-'}\n"
                    f"LANGUAGES: {languages_spoken or '-'}\n"
                    f"EXTRA NOTES: {notes or '-'}\n"
                )
                if cv_doc_text:
                    user_prompt += (
                        "\nEXISTING DOCUMENT TEXT (use its facts, ignore anything unrelated):\n"
                        + cv_doc_text[:MAX_ATTACHMENT_CHARS] + "\n"
                    )
                user_prompt += "\nReturn ONLY JSON matching this schema:\n" + CV_SCHEMA

                try:
                    with st.spinner("Designing your CV..."):
                        answer = call_ai(CV_SYSTEM_PROMPT, user_prompt, TEXT_MODELS, temperature=0.3, max_tokens=3000)
                        raw_cv = parse_json_object(answer)
                    form = {
                        "name": full_name.strip(), "phone": phone.strip(), "email": email.strip(),
                        "location": city.strip(), "links": linkedin.strip(), "role": target_role.strip(),
                    }
                    st.session_state.cv_data = normalize_cv(raw_cv, form)
                    st.session_state.cv_version += 1
                except json.JSONDecodeError as exc:
                    st.error("The AI answer was not valid. Please press Create my CV again.")
                    with st.expander("Technical details"):
                        st.caption(str(exc))
                except ValueError as exc:
                    st.error("The AI answer was not valid. Please press Create my CV again.")
                    with st.expander("Technical details"):
                        st.caption(str(exc))
                except Exception as exc:
                    show_ai_error(exc)

        # ----- CV studio: live design controls, preview, downloads -----
        cv = st.session_state.cv_data
        if cv:
            ver = st.session_state.cv_version
            st.markdown("---")
            st.markdown("### Your CV")
            st.caption("CVs are written in English, the standard for job applications.")

            d1, d2, d3 = st.columns(3)
            with d1:
                template = st.selectbox("Template", CV_TEMPLATES, key="cv_template")
            with d2:
                color_name = st.selectbox("Colour", list(PALETTES.keys()), key="cv_color")
            with d3:
                st.write("")
                show_photo = st.checkbox("Show photo", value=True, key="cv_show_photo")

            accent = PALETTES[color_name]
            photo_png = None
            if st.session_state.cv_photo_raw and show_photo and template != "ATS Minimal":
                photo_png = make_circle_photo(st.session_state.cv_photo_raw)

            if template == "ATS Minimal":
                st.caption("ATS Minimal has no photo or colour blocks, so recruiter software reads it cleanly.")
            elif not st.session_state.cv_photo_raw:
                st.caption("No photo added. Add one above and the CV updates instantly.")

            with st.expander("Fine-tune text"):
                cv["headline"] = st.text_input("Headline", cv["headline"], key=f"cv_head_{ver}")
                cv["summary"] = st.text_area("Summary", cv["summary"], height=110, key=f"cv_sum_{ver}")
                skills_edit = st.text_input("Skills (comma separated)", ", ".join(cv["skills"]), key=f"cv_skills_{ver}")
                cv["skills"] = [s.strip() for s in skills_edit.split(",") if s.strip()]

            components.html(cv_html(cv, photo_png, template, accent), height=900, scrolling=True)

            fname = safe_filename(cv["name"]) + "_cv"
            with keyed_container("dlgrid"):
                k1, k2, k3 = st.columns(3)
                with k1:
                    try:
                        st.download_button("Download PDF", build_cv_pdf(cv, photo_png, template, accent),
                                           file_name=f"{fname}.pdf", mime="application/pdf", key="cv_dl_pdf")
                    except Exception as exc:
                        st.error("PDF could not be created.")
                        st.caption(str(exc))
                with k2:
                    try:
                        st.download_button(
                            "Download DOCX", build_cv_docx(cv, photo_png, template, accent),
                            file_name=f"{fname}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key="cv_dl_docx",
                        )
                    except Exception as exc:
                        st.error("DOCX could not be created.")
                        st.caption(str(exc))
                with k3:
                    if st.button("Start over", key="cv_clear"):
                        st.session_state.cv_data = None
                        st.rerun()

    # --------------------------------------------------------
    # ALL OTHER SERVICES
    # --------------------------------------------------------
    else:
        image_file, image_kind, attachment_text = None, None, ""
        prompt, extra, go = "", "", False

        if service_key == "email":
            image_file, image_kind, attachment_text = attachment_input(
                service_key, "file or photo (optional)")

            with st.form("email_form"):
                name = st.text_input("Your name")
                recipient = st.text_input("Recipient / organization")
                purpose = st.text_area("What should the email say?", height=180,
                                       placeholder="Explain the purpose and important details.")
                tone = st.selectbox("Tone", ["Professional", "Formal", "Friendly", "Short and direct"])
                submitted = st.form_submit_button("Generate email")

            prompt = (
                f"Sender: {name or 'Not provided'}\n"
                f"Recipient: {recipient or 'Not provided'}\n"
                f"Purpose/details:\n{purpose}\n"
                f"Tone: {tone}\n"
                "Create a ready-to-send email."
            )
            extra = f"Use a {tone.lower()} tone."
            go = submitted and bool(purpose.strip() or image_file is not None or attachment_text)
            if submitted and not go:
                st.warning("Please enter the email details.")

        elif service_key == "kisan":
            image_file, image_kind, attachment_text = attachment_input(
                service_key, "crop photo or document (optional)")

            with st.form("kisan_form"):
                crop = st.text_input("Crop")
                location = st.text_input("District / province")
                stage = st.text_input("Crop stage")
                question = st.text_area("What do you want to know?", height=170,
                                        placeholder="Describe the problem, symptoms or farming question.")
                submitted = st.form_submit_button("Get guidance")

            prompt = (
                f"Crop: {crop}\nLocation: {location}\nCrop stage: {stage}\n"
                f"Question:\n{question}\n"
                "If an image is attached, use it as supporting visual evidence and clearly state uncertainty."
            )
            extra = "Give practical general guidance. Do not invent pesticide doses."
            go = submitted and bool(question.strip() or image_file is not None)
            if submitted and not go:
                st.warning("Write a question or attach an image.")

        elif service_key == "health":
            image_file, image_kind, attachment_text = attachment_input(
                service_key, "photo or document (optional)")
            st.info("General information only. This is not a diagnosis or a substitute for a doctor.")

            with st.form("health_form"):
                question = st.text_area("Health question", height=190,
                                        placeholder="Describe the general issue or topic. Avoid personal identifiers.")
                submitted = st.form_submit_button("Explain")

            prompt = (
                f"Health question:\n{question}\n"
                "If an image is attached, describe only visible features and explain uncertainty. "
                "Do not diagnose from the image."
            )
            extra = "Keep the response educational and include when professional care is appropriate."
            go = submitted and bool(question.strip() or image_file is not None)
            if submitted and not go:
                st.warning("Write a question or attach an image.")

        elif service_key == "gov":
            image_file, image_kind, attachment_text = attachment_input(
                service_key, "notice, form or document (optional)")

            with st.form("gov_form"):
                profile = st.selectbox("Your category",
                                       ["Student", "Job seeker", "Farmer", "Small business owner", "Other"])
                location = st.text_input("District / province")
                question = st.text_area("What do you want to know?", height=170,
                                        placeholder="Ask about a scheme, form, eligibility or application process.")
                submitted = st.form_submit_button("Explain")

            prompt = (
                f"Category: {profile}\nLocation: {location}\nQuestion:\n{question}\n"
                "If an image is attached, read visible information from it and explain what it means. "
                "Do not claim current eligibility or deadlines without verification."
            )
            extra = "Do not request CNIC, passwords, bank credentials or OTP codes."
            go = submitted and bool(question.strip() or image_file is not None)
            if submitted and not go:
                st.warning("Write a question or attach an image.")

        else:  # general / improve / student
            image_file, image_kind, attachment_text = attachment_input(
                service_key, "photo, screenshot or document (optional)")

            with st.form(f"{service_key}_form"):
                placeholder = {
                    "general": "Ask anything you want to understand, plan or create...",
                    "improve": "Paste the text you want improved, or explain what you want changed...",
                    "student": "Enter a topic, question, lecture text or assignment...",
                }[service_key]
                question = st.text_area("Your input", height=220, placeholder=placeholder)

                if service_key == "improve":
                    style = st.selectbox("Writing style", ["Clear and natural", "Professional", "Shorter",
                                                           "More persuasive", "Academic"])
                    extra = f"Use a {style.lower()} writing style."
                if service_key == "student":
                    level = st.selectbox("Learning level", ["Beginner", "Intermediate", "Advanced"])
                    extra = (f"Explain at {level.lower()} level. "
                             "Use examples and a few practice questions when useful.")
                submitted = st.form_submit_button("Generate")

            prompt = question
            go = submitted and bool(question.strip() or image_file is not None or attachment_text)
            if submitted and not go:
                st.warning("Write something or attach an image.")

        # ---------------- generation ----------------
        if go:
            if not API_KEY:
                st.error("GROQ_API_KEY is not configured. Add it in Streamlit Cloud → Settings → Secrets.")
            else:
                try:
                    with st.spinner("Generating..."):
                        image_uri = None
                        if image_file is not None and image_kind == "image":
                            mime = image_file.type or "image/jpeg"
                            image_uri = f"data:{mime};base64,{base64.b64encode(image_file.getvalue()).decode()}"

                        if attachment_text:
                            prompt = (prompt.strip() + "\n\nAttached document text:\n"
                                      + attachment_text[:MAX_ATTACHMENT_CHARS]).strip()
                        if image_uri and not prompt.strip():
                            prompt = ("Analyze the attached image and explain the important visible information. "
                                      "State uncertainty where necessary.")

                        system = SYSTEM_PROMPTS[service_key] + "\n\n" + language_rule(language) + "\n\n" + extra
                        models = VISION_MODELS if image_uri else TEXT_MODELS
                        result = call_ai(system, prompt.strip(), models, image_uri=image_uri,
                                         temperature=0.4, max_tokens=3000)

                    st.session_state.result = result
                    st.session_state.result_lang = language
                    st.session_state.result_version += 1
                    st.session_state.history.insert(0, {
                        "service": service["title"],
                        "time": datetime.now().strftime("%d %b, %I:%M %p"),
                        "result": result,
                    })
                    st.session_state.history = st.session_state.history[:6]
                except Exception as exc:
                    show_ai_error(exc)

        # ---------------- result ----------------
        if st.session_state.result:
            ver = st.session_state.result_version
            text = st.session_state.result

            st.markdown("---")
            st.markdown("### Result")

            l1, l2 = st.columns([3, 2])
            with l1:
                target = st.selectbox(
                    "Result language", LANGUAGES,
                    index=LANGUAGES.index(st.session_state.result_lang),
                    key=f"convert_lang_{ver}",
                )
            with l2:
                st.markdown("<div style='height:1.75rem'></div>", unsafe_allow_html=True)
                convert = st.button("Convert", key=f"convert_btn_{ver}")

            if convert:
                if target == st.session_state.result_lang:
                    st.info("The result is already in this language.")
                elif not API_KEY:
                    st.error("GROQ_API_KEY is not configured.")
                else:
                    try:
                        with st.spinner("Converting..."):
                            converted = translate_text(text, target)
                        st.session_state.result = converted
                        st.session_state.result_lang = target
                        st.session_state.result_version += 1
                        st.rerun()
                    except Exception as exc:
                        show_ai_error(exc)

            tab_read, tab_edit = st.tabs(["Read", "Copy / edit"])
            with tab_read:
                if is_rtl_text(text):
                    st.markdown(f'<div class="rtl">\n\n{text}\n\n</div>', unsafe_allow_html=True)
                else:
                    st.markdown(text)
            with tab_edit:
                final_text = st.text_area("Edit or copy", value=text, height=380,
                                          key=f"result_edit_{ver}", label_visibility="collapsed")

            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base = f"{safe_filename(service['title'])}_{stamp}"
            needs_urdu_font = bool(AR_RE.search(final_text)) and not urdu_pdf_ready()

            with keyed_container("dlgrid"):
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.download_button("TXT", final_text.encode("utf-8"), file_name=f"{base}.txt",
                                       mime="text/plain", key=f"dl_txt_{ver}")
                with c2:
                    pdf_bytes = None
                    if not needs_urdu_font:
                        try:
                            pdf_bytes = build_text_pdf(service["title"], final_text)
                        except Exception:
                            pdf_bytes = None
                    if pdf_bytes:
                        st.download_button("PDF", pdf_bytes, file_name=f"{base}.pdf",
                                           mime="application/pdf", key=f"dl_pdf_{ver}")
                    else:
                        st.button("PDF", disabled=True, key=f"dl_pdf_off_{ver}")
                with c3:
                    st.download_button(
                        "DOCX", build_text_docx(service["title"], final_text), file_name=f"{base}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"dl_docx_{ver}",
                    )
                with c4:
                    if st.button("Clear", key=f"clear_{ver}"):
                        st.session_state.result = ""
                        st.rerun()

            if needs_urdu_font:
                st.caption("Urdu PDF needs a font file (see README notes). DOCX and TXT work for Urdu right now.")


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")
st.markdown(
    """
    <div class="footer">
        <div class="quote">“Whoever follows a path in pursuit of knowledge, Allah will make easy for him a path to Paradise.”</div>
        <div>Sahih Muslim 2699a</div>
        <div style="margin-top:.55rem;">Designed by Waheed Ali Hamouzai</div>
    </div>
    """,
    unsafe_allow_html=True,
)
