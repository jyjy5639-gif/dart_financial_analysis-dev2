#!/usr/bin/env python
"""
DART 재무정보 분석기 - 프론트엔드 실행 스크립트
루트 디렉토리에서 실행: python run_frontend.py
"""

import sys
import os
from pathlib import Path
import subprocess

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 환경 변수 로드
from dotenv import load_dotenv
load_dotenv()

if __name__ == "__main__":
    # 환경변수에서 설정 읽기
    frontend_host = os.getenv('FRONTEND_HOST', '0.0.0.0')
    frontend_port = int(os.getenv('FRONTEND_PORT', '8501'))
    
    print("=" * 60)
    print("DART 재무정보 분석기 - 프론트엔드 시작")
    print("=" * 60)
    print(f"프로젝트 루트: {project_root}")
    print(f"호스트: {frontend_host}")
    print(f"포트: {frontend_port}")
    print(f"Streamlit URL: http://localhost:{frontend_port}")
    print("=" * 60)
    print()
    
    # Streamlit 앱 실행
    frontend_path = project_root / "frontend" / "app.py"
    subprocess.run([
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(frontend_path),
        f"--server.port={frontend_port}",
        f"--server.address={frontend_host}"
    ])
