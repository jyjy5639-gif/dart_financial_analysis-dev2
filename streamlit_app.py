# streamlit_app.py (프로젝트 루트)
import subprocess
import sys
from pathlib import Path

# Streamlit 앱 실행
frontend_path = Path(__file__).parent / "frontend" / "app.py"

subprocess.run([
    sys.executable,
    "-m",
    "streamlit",
    "run",
    str(frontend_path)
])