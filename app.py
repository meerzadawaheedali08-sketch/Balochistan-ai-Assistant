import streamlit as st
from groq import Groq
import os
from datetime import datetime

# ============================================
# 1. SECURE API KEY LOADING
# ============================================
def load_api_key():
    """Load API key from multiple secure sources."""
    # Try 1: Colab Secrets (most secure for Colab)
    try:
        from google.colab import userdata
        key = userdata.get('GROQ_API_KEY')
        if key:
            return key
    except Exception:
        pass

    # Try 2: Streamlit Secrets (for Streamlit Cloud)
    try:
        if "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass

    # Try 3: Environment variable
    return os.environ.get('GROQ_API_KEY')

GROQ_API_KEY = load_api_key()

if not GROQ_API_KEY:
    st.error("🚨 **API Key not found!**")
    st.info("""
    **Kaise fix karo:**
    - **Colab**: Sidebar 🔑 → Add `GROQ_API_KEY` → Notebook access ON
    - **Streamlit Cloud**: App Settings → Secrets → Add `GROQ_API_KEY`
    - **Local**: `.streamlit/secrets.toml` file banao
    """)
    st.stop()

client = Groq(api_key=GROQ_API_KEY)

# ============================================
# 2. PAGE CONFIG
# ============================================
st.set_page_config(
    page_title="Balochistan AI Assistant",
    page_icon="🇵🇰",
    layout="centered",
    initial_sidebar_state="expanded"
)

# ============================================
# 3. CUSTOM CSS — ATTRACTIVE + MOBILE FRIENDLY
# ============================================
st.markdown("""
<style>
    /* Import fonts */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
    }
    
    /* Main container */
    .main .block-container {
        padding: 1rem 0.8rem;
        max-width: 900px;
    }
    
    /* Hero header */
    .hero {
        background: linear-gradient(135deg, #01411C 0%, #046A38 50%, #0a8f4a 100%);
        padding: 2rem 1.2rem;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 25px rgba(1, 65, 28, 0.35);
        position: relative;
        overflow: hidden;
    }
    .hero::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
        animation: shimmer 3s infinite linear;
    }
    @keyframes shimmer {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    .hero h1 {
        color: white;
        font-size: 1.8rem;
        margin: 0;
        font-weight: 700;
        letter-spacing: -0.5px;
        position: relative;
        z-index: 1;
    }
    .hero p {
        color: #E8F5E9;
        font-size: 0.95rem;
        margin: 0.5rem 0 0 0;
        position: relative;
        z-index: 1;
    }
    
    /* Feature cards */
    .feature-card {
        background: white;
        border-left: 5px solid #046A38;
        padding: 1.1rem 1.2rem;
        border-radius: 12px;
        margin-bottom: 0.9rem;
        box-shadow: 0 3px 12px rgba(0,0,0,0.08);
        transition: all 0.3s ease;
        cursor: pointer;
    }
    .feature-card:hover {
        transform: translateX(6px);
        box-shadow: 0 6px 20px rgba(4, 106, 56, 0.2);
        border-left-color: #0a8f4a;
    }
    .feature-card h3 {
        margin: 0 0 0.3rem 0;
        color: #01411C;
        font-size: 1.1rem;
        font-weight: 600;
    }
    .feature-card p {
        margin: 0;
        color: #666;
        font-size: 0.85rem;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #046A38, #01411C);
        color: white !important;
        border: none;
        border-radius: 12px;
        padding: 0.8rem 1.5rem;
        font-weight: 600;
        width: 100%;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(4, 106, 56, 0.3);
        font-family: 'Poppins', sans-serif;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(4, 106, 56, 0.45);
        background: linear-gradient(135deg, #0a8f4a, #046A38);
    }
    .stButton > button:active {
        transform: translateY(0);
    }
    
    /* Inputs */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 12px;
        border: 2px solid #e0e0e0;
        font-size: 0.95rem;
        padding: 0.7rem;
        transition: all 0.2s;
        font-family: 'Poppins', sans-serif;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #046A38;
        box-shadow: 0 0 0 3px rgba(4, 106, 56, 0.15);
    }
    
    /* Selectbox */
    .stSelectbox > div > div {
        border-radius: 12px;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f9fa 0%, #e8f5e9 100%);
    }
    section[data-testid="stSidebar"] .stRadio > label {
        font-weight: 500;
        color: #01411C;
    }
    
    /* Success/Info/Warning boxes */
    .stSuccess, .stInfo, .stWarning {
        border-radius: 12px;
    }
    
    /* Download button */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #ffffff, #f0f0f0);
        color: #01411C !important;
        border: 2px solid #046A38;
        border-radius: 12px;
        font-weight: 600;
    }
    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #046A38, #01411C);
        color: white !important;
    }
    
    /* Divider */
    hr {
        margin: 1.5rem 0;
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #046A38, transparent);
    }
    
    /* Footer Hadith box */
    .hadith-box {
        background: linear-gradient(135deg, #f0f8f4 0%, #e8f5e9 100%);
        border: 2px solid #046A38;
        border-radius: 15px;
        padding: 1.5rem 1.2rem;
        text-align: center;
        margin-top: 2rem;
        box-shadow: 0 4px 15px rgba(4, 106, 56, 0.15);
    }
    .hadith-arabic {
        font-size: 1.4rem;
        color: #01411C;
        font-weight: 600;
        direction: rtl;
        margin-bottom: 0.8rem;
        line-height: 2;
    }
    .hadith-urdu {
        font-size: 0.95rem;
        color: #333;
        line-height: 1.7;
        margin-bottom: 0.7rem;
    }
    .hadith-ref {
        font-size: 0.8rem;
        color: #046A38;
        font-weight: 600;
        font-style: italic;
    }
    .credits {
        text-align: center;
        margin-top: 1.2rem;
        padding-top: 1rem;
        border-top: 1px dashed #046A38;
        color: #01411C;
        font-size: 0.9rem;
        font-weight: 600;
    }
    .credits span {
        color: #0a8f4a;
    }
    
    /* Mobile */
    @media (max-width: 768px) {
        .hero h1 { font-size: 1.4rem; }
        .hero p { font-size: 0.85rem; }
        .hero { padding: 1.5rem 1rem; }
        .feature-card h3 { font-size: 1rem; }
        .feature-card p { font-size: 0.8rem; }
        .stButton > button { padding: 0.9rem 1rem; font-size: 1rem; }
        .hadith-arabic { font-size: 1.2rem; }
    }
    
    /* Hide Streamlit default */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ============================================
# 4. SIDEBAR
# ============================================
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 1.2rem 0;">
        <div style="font-size: 3rem;">🇵🇰</div>
        <h3 style="color: #01411C; margin: 0.3rem 0; font-weight: 700;">Balochistan AI</h3>
        <p style="color: #666; font-size: 0.8rem; margin: 0;">Your Smart Assistant</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

feature = st.radio(
    "📌 **Choose Service:**",
    ["🏠 Home", "📧 Email Writer", "📄 CV Builder",
     "🌾 Kisan Advisor", "🏥 Health Info", "🏛️ Govt Schemes"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="text-align: center; font-size: 0.75rem; color: #666;">
    ⚡ Powered by <b>Groq</b><br>
    🧠 Model: <b>Llama 3.3 70B</b>
</div>
""", unsafe_allow_html=True)

# ============================================
# 5. SYSTEM PROMPTS
# ============================================
SYSTEM_PROMPTS = {
    "📧 Email Writer": """You are a professional email assistant for users in Balochistan, Pakistan.
Write clear, respectful, effective emails for jobs, business, or inquiries.
Tone: Professional, polite, direct.
If user writes in Urdu/Roman Urdu, respond in same language.
Structure: Subject line, greeting, body, closing.""",

    "📄 CV Builder": """You are a career assistant for Balochistan youth.
Create professional CVs from rough Urdu/Roman Urdu input.
Highlight skills relevant to Pakistani job market (NGOs, Govt, IT, Mining, Fisheries).
Format: Clean, ATS-friendly, ready to copy.
Include: Personal Info, Objective, Education, Experience, Skills, Languages.""",

    "🌾 Kisan Advisor": """You are an agriculture expert for Balochistan farmers.
Crops: Dates, Apples, Grapes, Wheat, Onions, Rice (in Khuzdar, Pishin, Mastung).
Give advice in simple Urdu/Roman Urdu.
Cover: crop diseases, weather, fertilizer, irrigation, government schemes.
Mention local pesticides available in Quetta/Kalat markets.""",

    "🏥 Health Info": """You are a basic health information assistant for Balochistan.
Common issues: Malaria, Typhoid, TB, Diarrhea, Heatstroke, Dengue.
Respond in Urdu/Roman Urdu.
ALWAYS add: 'Yeh medical advice nahi hai. Doctor se milna zaroori hai.'
Mention hospitals: Civil Hospital Quetta, BMC, DHQ hospitals.
For emergencies, advise immediate hospital visit.""",

    "🏛️ Govt Schemes": """You are a government scheme advisor for Balochistan.
Known schemes: BISP, Sehat Sahulat Card, Kamyab Jawan Loan, Zarai Taraqiati Bank loans, Ehsaas Program, Benazir Income Support.
For each scheme explain: Eligibility, Documents needed, Where to apply (Quetta office).
Respond in Urdu/Roman Urdu."""
}

# ============================================
# 6. GENERATE FUNCTION
# ============================================
def generate_response(system_prompt, user_prompt):
    """Call Groq API and display response with download option."""
    with st.spinner("✍️ Generating... Please wait..."):
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5,
                max_tokens=2500
            )
            result = completion.choices[0].message.content

            st.success("✅ **Done!** Neeche se copy karo:")
            st.text_area("Result", result, height=320, label_visibility="collapsed")

            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "📥 Download .txt",
                    result,
                    file_name=f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            with col2:
                if st.button("🔄 Naya Likho", use_container_width=True):
                    st.rerun()

        except Exception as e:
            st.error(f"❌ **Error:** {str(e)}")
            st.info("💡 Tip: Internet check karo, ya thori der baad try karo.")

# ============================================
# 7. FOOTER — HADITH + CREDITS
# ============================================
def show_footer():
    """Display footer with Hadith and credits."""
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("""
    <div class="hadith-box">
        <div class="hadith-arabic">خَيْرُ النَّاسِ أَنْفَعُهُمْ لِلنَّاسِ</div>
        <div class="hadith-urdu">
            <b>Tarjuma:</b> "Logon mein sab se behtar woh hai jo logon ke liye sab se zyada nafa-bakhsh ho."
        </div>
        <div class="hadith-ref">
            📖 Reference: Sahih al-Jami' as-Saghir, Hadith No. 3289 — Imam al-Albani (Rahimahullah) ne ise Sahih kaha
        </div>
        <div class="credits">
            🌐 Website Designed by <span>Waheed Ali Hamouzai</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ============================================
# 8. PAGE RENDERING
# ============================================

if feature == "🏠 Home":
    st.markdown("""
    <div class="hero">
        <h1>🇵🇰 Balochistan AI Assistant</h1>
        <p>Aapka smart AI madadgar — har kaam ke liye</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### ✨ **Kya kya kar sakte ho?**")

    st.markdown("""
    <div class="feature-card">
        <h3>📧 Email Writer</h3>
        <p>Professional emails likho — job, business, ya inquiry ke liye. Urdu/Roman Urdu mein bhi.</p>
    </div>
    <div class="feature-card">
        <h3>📄 CV Builder</h3>
        <p>Rough info se professional CV banao — seconds mein. ATS-friendly format.</p>
    </div>
    <div class="feature-card">
        <h3>🌾 Kisan Advisor</h3>
        <p>Fasal, keet, mausam, aur khad ki salah — Urdu mein. Balochistan ke crops ke liye.</p>
    </div>
    <div class="feature-card">
        <h3>🏥 Health Info</h3>
        <p>Basic health guidance — doctor ke paas jaane se pehle. Emergency warnings ke saath.</p>
    </div>
    <div class="feature-card">
        <h3>🏛️ Govt Schemes</h3>
        <p>BISP, Sehat Card, Kamyab Jawan Loan, Zarai loans — sab ek jagah. Apply karne ka process bhi.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.info("👈 **Sidebar se service choose karo** — mobile pe top-left ☰ icon dabao")

    show_footer()

elif feature == "📧 Email Writer":
    st.markdown("""
    <div class="hero">
        <h1>📧 Email Writer</h1>
        <p>Professional email likho seconds mein</p>
    </div>
    """, unsafe_allow_html=True)

    sender = st.text_input("👤 **Aapka Naam**", placeholder="Ahmed Khan")
    recipient = st.text_input("🎯 **Kis ko bhejni hai?**", placeholder="Hiring Manager, ABC Company")
    purpose = st.text_area(
        "✍️ **Email ka maqsad**",
        height=130,
        placeholder="Job application for Software Developer position. I have 2 years experience in Python and Excel."
    )

    if st.button("🚀 **Generate Email**", use_container_width=True):
        if not purpose:
            st.warning("⚠️ Email ka maqsad likhna zaroori hai!")
        else:
            generate_response(
                SYSTEM_PROMPTS["📧 Email Writer"],
                f"Sender: {sender}\nRecipient: {recipient}\nPurpose: {purpose}\n\nWrite the email."
            )
    show_footer()

elif feature == "📄 CV Builder":
    st.markdown("""
    <div class="hero">
        <h1>📄 CV Builder</h1>
        <p>Rough info se professional CV banao</p>
    </div>
    """, unsafe_allow_html=True)

    user_input = st.text_area(
        "📝 **Apni tafseel likho** (Urdu / Roman Urdu / English)",
        height=180,
        placeholder="Mera naam Ahmed hai, Quetta se. 2 saal experience Excel aur data entry. B.Com degree. English aur Urdu bolta hoon."
    )

    if st.button("🚀 **Generate CV**", use_container_width=True):
        if not user_input:
            st.warning("⚠️ Apni info likhna zaroori hai!")
        else:
            generate_response(SYSTEM_PROMPTS["📄 CV Builder"], user_input)
    show_footer()

elif feature == "🌾 Kisan Advisor":
    st.markdown("""
    <div class="hero">
        <h1>🌾 Kisan Advisor</h1>
        <p>Fasal aur kheti ki salah — Urdu mein</p>
    </div>
    """, unsafe_allow_html=True)

    query = st.text_area(
        "❓ **Apna sawal likhein**",
        height=130,
        placeholder="Mere apple ke patte peele ho rahe hain, kya karun?"
    )

    if st.button("🚀 **Salah Lo**", use_container_width=True):
        if not query:
            st.warning("⚠️ Sawal likhna zaroori hai!")
        else:
            generate_response(SYSTEM_PROMPTS["🌾 Kisan Advisor"], query)
    show_footer()

elif feature == "🏥 Health Info":
    st.markdown("""
    <div class="hero">
        <h1>🏥 Health Info</h1>
        <p>Basic health guidance — doctor se pehle</p>
    </div>
    """, unsafe_allow_html=True)

    st.warning("⚠️ **Zaroori:** Ye medical advice nahi hai. Doctor se milna zaroori hai.")

    symptoms = st.text_area(
        "🩺 **Apni takleef batayein**",
        height=130,
        placeholder="Bukhar aur sir dard 3 din se hai, kamzori bhi hai"
    )

    if st.button("🚀 **Info Lo**", use_container_width=True):
        if not symptoms:
            st.warning("⚠️ Takleef likhna zaroori hai!")
        else:
            generate_response(SYSTEM_PROMPTS["🏥 Health Info"], symptoms)
    show_footer()

elif feature == "🏛️ Govt Schemes":
    st.markdown("""
    <div class="hero">
        <h1>🏛️ Govt Schemes</h1>
        <p>Apne liye schemes dhundho</p>
    </div>
    """, unsafe_allow_html=True)

    profile = st.selectbox(
        "👤 **Main kaun hoon?**",
        ["Kisan (Farmer)", "Student", "Job seeker", "Woman", "Senior citizen", "Other"]
    )

    details = st.text_area(
        "📋 **Thori tafseel (optional)**",
        height=100,
        placeholder="Meri umar 45 hai, income 20,000/month, 3 bache hain"
    )

    if st.button("🚀 **Schemes Dhundho**", use_container_width=True):
        generate_response(
            SYSTEM_PROMPTS["🏛️ Govt Schemes"],
            f"Profile: {profile}\nDetails: {details}\n\nRecommend relevant schemes."
        )
    show_footer()
