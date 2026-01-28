# DART 재무정보 분석기 (Refactored)

## 프로젝트 구조

```
refactor_dart/
├── backend/              # FastAPI 백엔드
│   ├── api/             # API 라우트
│   ├── services/        # 비즈니스 로직
│   ├── repositories/    # 데이터 액세스
│   ├── models/          # 도메인 모델
│   ├── core/            # 핵심 설정 및 LLM
│   └── utils/           # 유틸리티
├── frontend/            # Streamlit 프론트엔드
│   ├── pages/          # 페이지
│   ├── components/     # UI 컴포넌트
│   └── api_client.py   # FastAPI 클라이언트
└── shared/             # 공통 스키마

## 설치 및 실행

### 1. 환경 설정
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 환경변수 설정
`.env` 파일 생성:
```
DART_API_KEY=your_dart_api_key
GEMINI_API_KEY=your_gemini_api_key
```

### 3. 백엔드 실행
```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 4. 프론트엔드 실행
```bash
cd frontend
streamlit run app.py
```

## 기능

- ✅ DART API 기업 검색
- ✅ 재무정보 조회 (3년치)
- ✅ 재무비율 계산 (ROE, ROA, PER, PBR 등)
- ✅ 주가 정보 크롤링
- ✅ AI 재무 브리핑 (Gemini, GPT, Claude, Upstage)
- ✅ Excel 다운로드
- ✅ 다중 회사 비교

## API 문서

FastAPI 실행 후: http://localhost:8000/docs
