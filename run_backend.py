#!/usr/bin/env python
"""
DART 재무정보 분석기 - 백엔드 실행 스크립트
루트 디렉토리에서 실행: python run_backend.py
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 환경 변수 로드
from dotenv import load_dotenv
load_dotenv()

if __name__ == "__main__":
    import uvicorn
    from backend.core.config import settings
    
    print("=" * 60)
    print("DART 재무정보 분석기 - 백엔드 서버 시작")
    print("=" * 60)
    print(f"프로젝트 루트: {project_root}")
    print(f"호스트: {settings.backend_host}")
    print(f"포트: {settings.backend_port}")
    print(f"API 문서: http://localhost:{settings.backend_port}/docs")
    print(f"Swagger UI: http://localhost:{settings.backend_port}/redoc")
    print("=" * 60)
    print()
    
    # FastAPI 앱 실행
    uvicorn.run(
        "backend.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
        reload_dirs=[str(project_root / "backend")]
    )
