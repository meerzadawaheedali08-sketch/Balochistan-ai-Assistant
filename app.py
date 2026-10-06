import os
from datetime import datetime
from typing import Optional

import streamlit as st
from groq import Groq
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from docx import Document

# ============================================================
# BALOCHISTAN AI ASSISTANT — GitHub / Streamlit Cloud ready
# ============================================================

st.set_page_config(
    page_title="Balochistan AI Assistant",
    page_icon="🇵🇰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Secure configuration ----------
def get_api_key() -> Optional[str]:
    """Read the Groq key from Streamlit Secrets or environment variables."""
    try:
        key = st.secrets.get("GROQ_API_KEY", "")
        if key:
            return str(key).strip()
    except Exception:
        pass
    return os.getenv("GROQ_API_KEY", "").strip() or None


API_KEY = get_api_key()

# ---------- UI styling ----------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Nastaliq+Urdu&display=swap');

    :root { --green: #087443; --deep: #063d2b; --mint: #eaf7ef; }
    .stApp { background: linear-gradient(180deg, #f7fbf8 0%, #f3f7f5 100%); }
    [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    .block-container { max-width: 1120px; padding-top: 1.2rem; padding-bottom: 2.5rem; }
    html, body, [class*="css"] { font-family: Inter, sans-serif; }
    .hero {
        background: radial-gradient(circle at top right, rgba(255,255,255,.18), transparent 35%),
                    linear-gradient(130deg, #063d2b 0%, #087443 58%, #11a365 100%);
        border: 1px solid rgba(255,255,255,.18); border-radius: 26px;
        padding: clamp(1.4rem, 4vw, 2.7rem); color: white; margin-bottom: 1.25rem;
        box-shadow: 0 18px 45px rgba(6,61,43,.16);
    }
    .hero h1 { color: white; font-size: clamp(1.65rem, 4vw, 2.65rem); line-height: 1.15; margin: .35rem 0 .65rem; font-weight: 800; }
    .hero p { color: #e3f7eb; margin: 0; font-size: clamp(.92rem, 2vw, 1.08rem); }
    .eyebrow { display:inline-block; border:1px solid rgba(255,255,255,.3); border-radius:999px; padding:.32rem .7rem; font-size:.78rem; letter-spacing:.04em; }
    .feature {
        background: white; border: 1px solid #e2ece6; border-radius: 18px; padding: 1rem 1.05rem;
        min-height: 118px; box-shadow: 0 5px 18px rgba(10,50,30,.045);
    }
    .feature .emoji { font-size: 1.55rem; }
    .feature h3 { font-size: 1rem; color: #123c2b; margin: .45rem 0 .25rem; }
    .feature p { color: #617268; font-size: .86rem; margin: 0; line-height: 1.5; }
    .section-label { color:#174b35; font-weight:750; font-size:1.05rem; margin:.5rem 0 .8rem; }
    .stButton > button, .stDownloadButton > button {
        border-radius: 12px; min-height: 2.85rem; font-weight: 650; border: 1px solid #087443;
        transition: transform .15s ease, box-shadow .15s ease;
    }
    .stButton > button[kind="primary"] { background: linear-gradient(120deg,#087443,#075a37); color:white; }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 7px 18px rgba(8,116,67,.13); }
    div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > div,
    div[data-baseweb="select"] > div { border-radius: 12px; }
    section[data-testid="stSidebar"] { background: #f0f7f2; border-right: 1px solid #e0ece4; }
    .sidebar-brand { text-align:center; padding:.6rem 0 1rem; }
    .sidebar-brand .flag { font-size:2.5rem; }
    .sidebar-brand h2 { color:#063d2b; font-size:1.15rem; margin:.25rem 0; }
    .sidebar-brand p { color:#65766c; font-size:.8rem; margin:0; }
    .result-box { background:white; border:1px solid #dcebe1; border-radius:16px; padding:1rem; }
    .footer { text-align:center; color:#718078; font-size:.8rem; padding:1.4rem .5rem .3rem; }
    .urdu { font-family: 'Noto Nastaliq Urdu', serif; direction: rtl; text-align: right; line-height: 2.1; }
    @media(max-width: 640px) {
        .block-container { padding: .7rem .8rem 2rem; }
        .hero { border-radius: 19px; padding: 1.35rem 1.1rem; }
        .feature { min-height: auto; }
        [data-testid="stSidebar"] { min-width: 80vw; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Language strings ----------
LANGUAGES = ["English", "اردو", "Roman Urdu"]
COPY = {
    "English": {
        "tagline": "A practical AI helper for learning, work, and everyday life.",
        "choose": "Choose a service",
        "language": "Response language",
        "home": "Home",
        "email": "Email Writer",
        "cv": "CV Builder",
        "kisan": "Kisan Advisor",
        "health": "Health Information",
        "gov": "Government Schemes",
        "general": "AI Assistant",
        "improve": "Text Improver",
        "student": "Student Helper",
        "input": "Your details / question",
        "generate": "Generate response",
        "clear": "Clear result",
        "recent": "Recent results",
        "ready": "Your result will appear here.",
        "missing": "Please enter some details first.",
        "key_missing": "Groq API key is not configured. Add GROQ_API_KEY in Streamlit Cloud → App → Settings → Secrets.",
        "key_help": "For local development, add GROQ_API_KEY to your environment or .streamlit/secrets.toml. Never commit your key to GitHub.",
        "disclaimer": "AI can make mistakes. Verify important information, especially health, legal, financial, and government-program details.",
    },
    "اردو": {
        "tagline": "تعلیم، کام اور روزمرہ زندگی کے لیے آپ کا عملی اے آئی مددگار۔",
        "choose": "سروس منتخب کریں",
        "language": "جواب کی زبان",
        "home": "ہوم",
        "email": "ای میل رائٹر",
        "cv": "سی وی بلڈر",
        "kisan": "کسان رہنما",
        "health": "صحت کی معلومات",
        "gov": "سرکاری اسکیمیں",
        "general": "اے آئی اسسٹنٹ",
        "improve": "تحریر بہتر کریں",
        "student": "طلبہ کی مدد",
        "input": "اپنی تفصیل یا سوال لکھیں",
        "generate": "جواب تیار کریں",
        "clear": "نتیجہ صاف کریں",
        "recent": "حالیہ نتائج",
        "ready": "آپ کا جواب یہاں ظاہر ہوگا۔",
        "missing": "براہِ کرم پہلے کچھ تفصیل لکھیں۔",
        "key_missing": "Groq API key موجود نہیں۔ Streamlit Cloud کی App Settings → Secrets میں GROQ_API_KEY شامل کریں۔",
        "key_help": "اپنی API key کو کبھی GitHub پر اپ لوڈ نہ کریں۔",
        "disclaimer": "اے آئی سے غلطی ہو سکتی ہے۔ صحت، قانونی، مالی اور سرکاری معلومات کی تصدیق ضرور کریں۔",
    },
    "Roman Urdu": {
        "tagline": "Parhai, kaam aur rozmarrah zindagi ke liye aap ka smart AI helper.",
        "choose": "Service choose karein",
        "language": "Jawab ki language",
        "home": "Home",
        "email": "Email Writer",
        "cv": "CV Builder",
        "kisan": "Kisan Advisor",
        "health": "Health Info",
        "gov": "Government Schemes",
        "general": "AI Assistant",
        "improve": "Text Improver",
        "student": "Student Helper",
        "input": "Apni details ya sawal likhein",
        "generate": "Jawab Generate Karein",
        "clear": "Result Clear Karein",
        "recent": "Recent Results",
        "ready": "Aap ka result yahan show hoga.",
        "missing": "Pehle kuch details ya sawal likhein.",
        "key_missing": "Groq API key set nahi hai. Streamlit Cloud → App Settings → Secrets mein GROQ_API_KEY add karein.",
        "key_help": "API key ko kabhi GitHub par upload na karein.",
        "disclaimer": "AI ghalti kar sakta hai. Health, legal, financial aur government info ko verify zaroor karein.",
    },
}

SERVICE_LABEL_KEYS = ["email", "cv", "kisan", "health", "gov", "general", "improve", "student"]
SERVICE_ICONS = {
    "email": "✉️", "cv": "📄", "kisan": "🌾", "health": "🩺",
    "gov": "🏛️", "general": "✨", "improve": "✍️", "student": "🎓",
}
SERVICE_DESCRIPTIONS = {
    "email": "Write polished emails for jobs, university, and business.",
    "cv": "Create a clear, ATS-friendly CV from your rough notes.",
    "kisan": "Get general crop, irrigation, and farming guidance.",
    "health": "Understand health topics and when to seek professional care.",
    "gov": "Understand possible public schemes and application steps.",
    "general": "Ask questions, brainstorm, plan, or learn a topic.",
    "improve": "Rewrite text to make it clearer, more professional, or concise.",
    "student": "Explain concepts, make study plans, quizzes, and summaries.",
}

SYSTEM_PROMPTS = {
    "email": """You are a professional email-writing assistant for people in Pakistan.
Create a ready-to-send email with a useful subject, greeting, body, and sign-off.
Do not invent qualifications, dates, promises, or facts. Ask for missing details only if essential.""",
    "cv": """You are a professional CV and career-writing assistant.
Create a clean, ATS-friendly CV using only the user's supplied facts. Never invent degrees,
experience, dates, certifications, or skills. Use placeholders for missing contact details.
Include a concise objective, education, experience, skills, and languages when relevant.""",
    "kisan": """You provide general agricultural education relevant to Pakistan, including crops,
soil, irrigation, pests, and fertilizer. Ask for location, crop, crop stage, and symptoms when
needed. Do not guess pesticide doses or recommend hazardous chemical use; advise consulting
local agriculture extension experts and following product labels.""",
    "health": """You provide general health information, not diagnosis or treatment.
Encourage a qualified clinician for personal medical decisions. For emergency symptoms
such as severe breathing difficulty, chest pain, unconsciousness, stroke signs, or severe bleeding,
tell the user to seek emergency medical help immediately. Do not prescribe medicines or dosages.""",
    "gov": """You help users understand public assistance programs in Pakistan.
Program rules, deadlines, and eligibility can change. Clearly distinguish general guidance from
verified current facts; never claim a user is eligible or that a scheme is currently open without
evidence. Recommend checking official government sources and avoid requesting sensitive IDs.""",
    "general": """You are a helpful, accurate, respectful general-purpose AI assistant.
Explain clearly, structure complex answers, and state uncertainty. Do not fabricate sources or facts.""",
    "improve": """You are an expert editor. Improve the user's text according to their intended
tone and purpose while preserving meaning. If no style is specified, make it clear, natural,
grammatically correct, and concise. Return the revised text first, then brief notes if useful.""",
    "student": """You are a friendly tutor. Explain concepts step by step at the learner's level.
For study requests, use simple explanations, examples, key points, and a short practice quiz when
useful. Help the learner understand rather than merely memorize. Do not pretend to know their syllabus.""",
}

def language_instruction(language: str) -> str:
    if language == "اردو":
        return "Respond in natural Urdu script (اردو), not Hindi. Keep technical terms in English where helpful."
    if language == "Roman Urdu":
        return "Respond in natural Roman Urdu using Latin letters. Do not use Hindi/Devanagari script."
    return "Respond in clear, natural English."

def get_client() -> Groq:
    return Groq(api_key=API_KEY)


def file_to_data_uri(uploaded_file):
    """Convert an uploaded image to a data URI for Groq vision input."""
    if not uploaded_file:
        return None

    data = uploaded_file.getvalue()
    mime = uploaded_file.type or "image/jpeg"
    encoded = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def build_pdf(text: str) -> bytes:
    """Create a simple Unicode-friendly PDF using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45,
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "AIResult",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        spaceAfter=8,
        alignment=TA_LEFT,
    )
    title = ParagraphStyle(
        "AITitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        spaceAfter=15,
    )

    story = [
        Paragraph("Balochistan AI Assistant", title),
        Paragraph(
            "Generated: " + datetime.now().strftime("%d %b %Y, %I:%M %p"),
            body,
        ),
    ]

    for paragraph in text.split("\n"):
        safe = paragraph.strip()
        if not safe:
            story.append(Spacer(1, 6))
            continue
        safe = (
            safe.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
        )
        story.append(Paragraph(safe, body))

    doc.build(story)
    return buffer.getvalue()


def build_docx(text: str) -> bytes:
    """Create a DOCX document."""
    document = Document()
    document.add_heading("Balochistan AI Assistant", 0)
    document.add_paragraph(
        "Generated: " + datetime.now().strftime("%d %b %Y, %I:%M %p")
    )

    for paragraph in text.split("\n"):
        document.add_paragraph(paragraph)

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def generate_multimodal_response(
    service_key: str,
    prompt: str,
    language: str,
    extra_instructions: str = "",
    image_data_uri: str = None,
) -> str:
    """
    Generate a response from text alone or text + image.
    Image is sent directly to Groq; it is not stored by this app.
    """
    system = (
        SYSTEM_PROMPTS[service_key]
        + "\n\nResponse language: " + language_instruction(language)
        + (
            "\n\nAdditional instructions: " + extra_instructions
            if extra_instructions else ""
        )
    )

    if not image_data_uri:
        return run_ai(service_key, prompt, language, extra_instructions)

    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": image_data_uri},
                },
            ],
        },
    ]

    response = get_client().chat.completions.create(
        model=VISION_MODEL,
        messages=messages,
        temperature=0.35,
        max_tokens=3000,
    )
    return (response.choices[0].message.content or "").strip()


def render_attachments(label="📷 Add a photo / screenshot / document image"):
    """
    Camera works on supported mobile/browser devices.
    File uploader accepts common image formats.
    """
    st.markdown("### 📷 Add an image if needed")
    st.caption(
        "Take a photo with your camera, upload a screenshot/photo, "
        "and optionally write a question about it."
    )

    camera_photo = st.camera_input(
        "Take a photo",
        key=f"camera_{label}",
    )

    uploaded_photo = st.file_uploader(
        "Or upload an image",
        type=["jpg", "jpeg", "png", "webp"],
        key=f"upload_{label}",
    )

    selected = camera_photo or uploaded_photo

    if selected:
        st.image(selected, caption="Selected image", use_container_width=True)

    return selected


def render_downloads(result: str, prefix="balochistan_ai"):
    """Offer multiple useful output formats."""
    if not result:
        return

    safe_prefix = re.sub(r"[^a-zA-Z0-9_-]+", "_", prefix).strip("_") or "ai_result"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    txt_name = f"{safe_prefix}_{stamp}.txt"
    pdf_name = f"{safe_prefix}_{stamp}.pdf"
    docx_name = f"{safe_prefix}_{stamp}.docx"

    pdf_bytes = build_pdf(result)
    docx_bytes = build_docx(result)

    st.markdown("### 📥 Download result")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.download_button(
            "📄 TXT",
            data=result.encode("utf-8"),
            file_name=txt_name,
            mime="text/plain",
            use_container_width=True,
        )

    with c2:
        st.download_button(
            "📕 PDF",
            data=pdf_bytes,
            file_name=pdf_name,
            mime="application/pdf",
            use_container_width=True,
        )

    with c3:
        st.download_button(
            "📝 DOCX",
            data=docx_bytes,
            file_name=docx_name,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )


def run_ai(service_key: str, prompt: str, language: str, extra_instructions: str = "") -> str:
    system = (
        SYSTEM_PROMPTS[service_key]
        + "\n\nResponse language: " + language_instruction(language)
        + ("\n\nAdditional instructions: " + extra_instructions if extra_instructions else "")
    )
    response = get_client().chat.completions.create(
        model=st.session_state.get("model", "llama-3.3-70b-versatile"),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.45,
        max_tokens=3000,
    )
    return (response.choices[0].message.content or "").strip()

# ---------- Session state ----------
if "history" not in st.session_state:
    st.session_state.history = []
if "result" not in st.session_state:
    st.session_state.result = ""
if "last_service" not in st.session_state:
    st.session_state.last_service = ""

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown(
        '<div class="sidebar-brand"><div class="flag">🇵🇰</div>'
        '<h2>Balochistan AI</h2><p>Your smart everyday assistant</p></div>',
        unsafe_allow_html=True,
    )
    language = st.selectbox("🌐 " + "Language / زبان", LANGUAGES, index=2)
    t = COPY[language]
    st.markdown("---")
    page = st.radio(
        t["choose"],
        [t["home"]] + [SERVICE_ICONS[k] + "  " + t[k] for k in SERVICE_LABEL_KEYS],
        label_visibility="visible",
    )
    with st.expander("⚙️ Settings"):
        st.selectbox(
            "AI model",
            ["llama-3.3-70b-versatile"],
            key="model",
            help="The model must be available to your Groq account.",
        )
        if st.button("🧹 Clear session history", use_container_width=True):
            st.session_state.history = []
            st.session_state.result = ""
            st.rerun()
    st.markdown("---")
    st.caption("⚡ Powered by Groq")
    st.caption("🔒 API key is read server-side")

# ---------- Hero ----------
st.markdown(
    f"""
    <div class="hero">
      <span class="eyebrow">🇵🇰 MADE FOR EVERYDAY LEARNING</span>
      <h1>Balochistan AI Assistant</h1>
      <p>{t["tagline"]}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(
    "📷 You can now take a photo with your camera or upload an image, "
    "then write a question about it. The AI can use both together."
)

if not API_KEY:
    st.error(t["key_missing"])
    st.info(t["key_help"])
    st.stop()

# ---------- Home ----------
if page == t["home"]:
    st.markdown(f'<div class="section-label">✨ {t["choose"]}</div>', unsafe_allow_html=True)
    cols = st.columns(2, gap="medium")
    for i, key in enumerate(SERVICE_LABEL_KEYS):
        with cols[i % 2]:
            st.markdown(
                f'<div class="feature"><div class="emoji">{SERVICE_ICONS[key]}</div>'
                f'<h3>{t[key]}</h3><p>{SERVICE_DESCRIPTIONS[key]}</p></div>',
                unsafe_allow_html=True,
            )
            if st.button("Open " + t[key], key=f"open_{key}", use_container_width=True):
                st.session_state["selected_service"] = key
                # Change the radio selection on the next rerun using a query-independent state.
                st.session_state["home_open_service"] = key
                st.rerun()

    selected = st.session_state.get("home_open_service")
    if selected:
        st.info(f"Selected: {t[selected]}. Choose it from the sidebar to open the service.")
    st.markdown("---")
    st.markdown(f"**{t['disclaimer']}**")
    st.markdown(
        '<div class="footer">Designed with care • Balochistan AI Assistant<br>'
        'AI-generated content may require independent verification.</div>',
        unsafe_allow_html=True,
    )

else:
    # Map translated sidebar label back to internal service key.
    service_key = next(
        (k for k in SERVICE_LABEL_KEYS if page == SERVICE_ICONS[k] + "  " + t[k]),
        "general",
    )
    st.markdown(f"## {SERVICE_ICONS[service_key]} {t[service_key]}")
    st.caption(SERVICE_DESCRIPTIONS[service_key])

    # Service-specific structured inputs
    if service_key == "email":
        with st.form("email_form"):
            name = st.text_input("Your name", placeholder="e.g., Ali Ahmed")
            recipient = st.text_input("Recipient", placeholder="e.g., Hiring Manager")
            purpose = st.text_area("Purpose and key details", height=150,
                                   placeholder="Job application, inquiry, university request...")
            tone = st.selectbox("Tone", ["Professional", "Friendly", "Formal", "Short and direct"])
            submitted = st.form_submit_button(t["generate"], type="primary", use_container_width=True)
        user_prompt = f"Sender name: {name or 'Not provided'}\nRecipient: {recipient or 'Not provided'}\nPurpose/details: {purpose}\nTone: {tone}\nWrite the email."
        can_generate = submitted and bool(purpose.strip())
        if submitted and not purpose.strip():
            st.warning(t["missing"])
        extra = f"Use a {tone.lower()} tone."
    elif service_key == "cv":
        with st.form("cv_form"):
            cv_details = st.text_area(t["input"], height=230,
                placeholder="Name (optional), education, experience, skills, projects, languages...")
            cv_target = st.selectbox("Target role", ["General", "Internship", "Entry-level job", "Experienced role"])
            submitted = st.form_submit_button(t["generate"], type="primary", use_container_width=True)
        user_prompt = f"Create a CV for this target: {cv_target}\nUser details:\n{cv_details}"
        can_generate = submitted and bool(cv_details.strip())
        if submitted and not cv_details.strip():
            st.warning(t["missing"])
        extra = "Use clean headings and bullet points. Do not invent facts."
    elif service_key == "gov":
        with st.form("gov_form"):
            profile = st.selectbox("I am a...", ["Student", "Job seeker", "Farmer", "Woman", "Senior citizen", "Small business owner", "Other"])
            location = st.text_input("District / province (optional)", placeholder="e.g., Nasirabad, Balochistan")
            details = st.text_area(t["input"], height=130, placeholder="Share only non-sensitive details relevant to your question.")
            submitted = st.form_submit_button(t["generate"], type="primary", use_container_width=True)
        user_prompt = f"Profile: {profile}\nLocation: {location}\nDetails/question: {details}\nExplain potentially relevant programs, likely documents, and how to verify through official channels. Do not claim current availability without verification."
        can_generate = submitted and bool((details + location).strip())
        if submitted and not (details + location).strip():
            st.warning(t["missing"])
        extra = "Never ask for CNIC, bank account, passwords, or one-time codes."
    else:
        placeholders = {
            "kisan": "Crop, district, crop stage, symptoms, irrigation, or farming question...",
            "health": "Describe the general health topic or question. Avoid sharing identifying information.",
            "general": "Ask anything you want to understand, plan, or create...",
            "improve": "Paste the text you want improved. Mention tone or audience if relevant...",
            "student": "Topic, class/semester, what confuses you, or a subject to revise...",
        }

        # Image input is available for every general-purpose service.
        image_file = render_attachments(service_key)

        with st.form(f"{service_key}_form"):
            user_prompt = st.text_area(
                t["input"],
                height=210,
                placeholder=placeholders.get(service_key, "Type here..."),
            )

            extra = ""

            if service_key == "improve":
                extra = st.selectbox(
                    "Writing style",
                    [
                        "Clear and natural",
                        "Professional",
                        "Shorter",
                        "More persuasive",
                        "Academic",
                    ],
                )

            elif service_key == "student":
                level = st.selectbox(
                    "Learning level",
                    ["Beginner", "Intermediate", "Advanced"],
                )
                extra = (
                    f"Explain at {level.lower()} level. "
                    "Include an example and a few practice questions when useful."
                )

            if image_file:
                st.caption(
                    "🖼️ Image attached. Your text question will be used together "
                    "with the image."
                )

            submitted = st.form_submit_button(
                t["generate"],
                type="primary",
                use_container_width=True,
            )

        can_generate = submitted and bool(user_prompt.strip() or image_file)

        if submitted and not (user_prompt.strip() or image_file):
            st.warning(
                "Please write a question or attach an image first."
            )


    if service_key == "health":
        st.warning("Health information is educational only, not a diagnosis. Seek professional care for personal medical concerns. For emergencies, contact local emergency services or go to the nearest emergency department.")
    elif service_key == "gov":
        st.info("Government scheme eligibility, deadlines, and application procedures can change. Verify through official sources before sharing documents or paying anyone.")
    elif service_key == "kisan":
        st.info("For crop-specific chemical or pesticide decisions, consult a local agriculture extension officer and follow the product label.")

    if can_generate:
        try:
            with st.spinner("✨ Preparing your response..."):
                image_data_uri = file_to_data_uri(image_file) if image_file else None
                final_prompt = user_prompt.strip()

                if image_data_uri and not final_prompt:
                    final_prompt = (
                        "Analyze the attached image and explain what is visible. "
                        "Point out useful details and tell me what I should know."
                    )

                result = generate_multimodal_response(
                    service_key,
                    final_prompt,
                    language,
                    extra,
                    image_data_uri=image_data_uri,
                )
            st.session_state.result = result
            st.session_state.last_service = service_key
            st.session_state.history.insert(0, {
                "service": t[service_key],
                "time": datetime.now().strftime("%d %b %Y, %I:%M %p"),
                "prompt": user_prompt[:180],
                "result": result,
            })
            st.session_state.history = st.session_state.history[:8]
        except Exception as exc:
            # Avoid displaying raw request details or secrets to the user.
            message = str(exc).lower()
            if "rate_limit" in message or "429" in message:
                st.error("Groq rate limit reached. Please wait a little and try again.")
            elif "authentication" in message or "401" in message or "invalid_api_key" in message:
                st.error("Groq rejected the API key. Check GROQ_API_KEY in Streamlit Secrets.")
            elif "model" in message and ("not found" in message or "decommission" in message):
                st.error("The configured Groq model may be unavailable. Update the model name in app.py.")
            else:
                st.error("Something went wrong while contacting the AI service. Please try again.")
            with st.expander("Technical details"):
                st.caption("For debugging, check the app logs in Streamlit Cloud. Do not share your API key.")

    if st.session_state.result:
        st.markdown("---")
        st.markdown("### ✅ Result")
        st.text_area(
            "Generated response",
            value=st.session_state.result,
            height=360,
            key="display_result",
        )

        render_downloads(
            st.session_state.result,
            prefix=st.session_state.last_service or "balochistan_ai",
        )

        if st.button("🧹 Clear result", use_container_width=True):
            st.session_state.result = ""
            st.rerun()

    with st.expander("🕘 Recent results"):
        if not st.session_state.history:
            st.caption("Your recent results in this session will appear here.")
        else:
            for idx, item in enumerate(st.session_state.history):
                st.markdown(f"**{item['service']}** · {item['time']}")
                st.caption(item["prompt"])
                with st.expander(f"View result #{idx + 1}"):
                    st.text_area("Result", value=item["result"], height=220, key=f"history_{idx}")
                    st.download_button(
                        "Download this result",
                        data=item["result"],
                        file_name=f"result_{idx + 1}.txt",
                        mime="text/plain",
                        key=f"download_history_{idx}",
                    )

    st.markdown("---")
    st.caption(t["disclaimer"])

st.markdown(
    '<div class="footer">Balochistan AI Assistant • Built for learning and everyday productivity</div>',
    unsafe_allow_html=True,
)
