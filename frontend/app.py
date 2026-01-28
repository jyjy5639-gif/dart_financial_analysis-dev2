import streamlit as st
from dotenv import load_dotenv

load_dotenv()

pages = [
    st.Page("pages/home.py", title="Home", icon="🏠"),
    st.Page("pages/01_analysis.py", title="AI재무정보조회", icon="📊")
]
pg = st.navigation(pages)
pg.run()