from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from backend.services.llm_service import LLMService
from backend.services.pdf_service import PDFService
from backend.api.dependencies import get_llm_service
from backend.core.logger import get_backend_logger
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
from urllib.parse import quote

logger = get_backend_logger("briefing")
router = APIRouter(prefix="/api/briefing", tags=["briefing"])

class BriefingRequest(BaseModel):
    corp_name: str
    financial_data: Dict  # Dict로 변경 (items와 ratios 포함)
    provider: str = "gemini"
    style: str = "default"
    api_key: str

class PDFDownloadRequest(BaseModel):
    """PDF 다운로드 요청"""
    briefing_text: str
    company_info: Dict  # 회사 정보
    financial_summary: Optional[Dict] = None
    llm_provider: str = "AI"
    analysis_style: str = "standard"

@router.post("/generate")
async def generate_briefing(
    request: BriefingRequest,
    llm_service: LLMService = Depends(get_llm_service)
):
    """분석 생성"""
    try:
        logger.info(f"Generating briefing for {request.corp_name} using {request.provider}")
        
        # LLM 제공자 등록
        llm_service.register_provider(request.provider, request.api_key)
        
        # 브리핑 생성
        briefing = await llm_service.generate_briefing(
            provider_name=request.provider,
            corp_name=request.corp_name,
            financial_data=request.financial_data,
            style=request.style
        )
        
        logger.info(f"Successfully generated briefing for {request.corp_name}")
        
        return {
            "briefing": briefing,
            "provider": request.provider
        }
    except Exception as e:
        from backend.core.exceptions import LLMException
        
        logger.error(f"Briefing generation failed: {str(e)}", exc_info=True)
        
        # LLMException은 사용자 친화적인 메시지로 바로 보냄
        if isinstance(e, LLMException):
            raise HTTPException(status_code=400, detail=str(e))
        
        # 그 외 예외는 500 에러
        import traceback
        error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

@router.post("/download-pdf")
async def download_briefing_pdf(request: PDFDownloadRequest):
    """
    AI 브리핑을 PDF 파일로 다운로드
    """
    try:
        logger.info(f"Creating PDF for briefing: {request.company_info.get('corp_name', 'Unknown')}")
        
        # PDF 서비스 인스턴스 생성
        pdf_service = PDFService()
        
        # PDF 생성
        if 'companies' in request.company_info and len(request.company_info['companies']) > 1:
            # 복수 회사 비교
            pdf_file = pdf_service.create_comparison_pdf(
                briefing_text=request.briefing_text,
                companies=request.company_info['companies'],
                comparison_data=request.financial_summary,
                llm_provider=request.llm_provider
            )
            
            company_names = [comp.get('corp_name', '') for comp in request.company_info['companies']]
            filename = f"재무분석리포트_비교_{datetime.now().strftime('%Y%m%d')}.pdf"
        else:
            # 단일 회사
            pdf_file = pdf_service.create_briefing_pdf(
                briefing_text=request.briefing_text,
                company_info=request.company_info,
                financial_summary=request.financial_summary,
                llm_provider=request.llm_provider,
                analysis_style=request.analysis_style
            )
            
            corp_name = request.company_info.get('corp_name', '회사명')
            filename = f"재무분석리포트_{corp_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        # 한글 파일명 인코딩
        encoded_filename = quote(filename)
        
        logger.info(f"PDF created successfully: {filename}")
        
        # PDF 파일 다운로드 응답
        return StreamingResponse(
            pdf_file,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                "Content-Type": "application/pdf"
            }
        )
        
    except Exception as e:
        logger.error(f"PDF creation failed: {str(e)}", exc_info=True)
        import traceback
        error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

@router.get("/providers")
async def get_providers(
    llm_service: LLMService = Depends(get_llm_service)
):
    """사용 가능한 LLM 제공자 목록"""
    return {
        "providers": ["gemini", "openai", "claude", "upstage"]
    }
