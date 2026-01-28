from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import company, financial, briefing
from backend.core.config import settings
from backend.core.logger import get_backend_logger
from contextlib import asynccontextmanager
import time

# 로거 초기화
logger = get_backend_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # Startup
    logger.info("=" * 60)
    logger.info("DART 재무정보 분석 API 시작")
    logger.info("Version: 2.0.0")
    logger.info(f"CORS Origins: {settings.cors_origins}")
    logger.info("=" * 60)

    yield  # <-- 애플리케이션 실행 구간

    # Shutdown
    logger.info("DART 재무정보 분석 API 종료")


app = FastAPI(
    title="화인 DART 재무정보 분석 API",
    description="한국 기업 재무정보 조회 및 AI 분석 API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 요청/응답 로깅 미들웨어
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """모든 HTTP 요청/응답 로깅"""
    start_time = time.time()

    logger.info(f"Request: {request.method} {request.url.path}")

    response = await call_next(request)

    process_time = time.time() - start_time

    logger.info(
        f"Response: {request.method} {request.url.path} "
        f"Status={response.status_code} Time={process_time:.3f}s"
    )

    return response


# 라우터 등록
app.include_router(company.router)
app.include_router(financial.router)
app.include_router(briefing.router)


@app.get("/")
async def root():
    """API 루트"""
    logger.info("Root endpoint accessed")
    return {
        "message": "DART 재무정보 분석 API",
        "version": "2.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    logger.info(
        f"Starting server on {settings.backend_host}:{settings.backend_port}"
    )
    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
    )
