import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# icon_path 정의
icon_path = Path(__file__).parent / "static" / "fine.png"

st.set_page_config(
    page_title="화인 DART 재무정보 분석기",
    page_icon=str(icon_path) if icon_path.exists() else "🎯",
    layout="wide"
)

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "https://dart-financial-analysis-dev-backend.onrender.com"
)

if "backend_url" not in st.session_state:
    st.session_state.backend_url = BACKEND_URL

pages = [
    st.Page("page_modules/home.py", title="Home", icon="🏠"),
    st.Page("page_modules/01_analysis.py", title="AI재무정보조회", icon="📊")
]
pg = st.navigation(pages)
pg.run()