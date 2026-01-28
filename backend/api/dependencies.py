from fastapi import Header, HTTPException
from backend.services.dart_service import DARTService
from backend.services.krx_service import KRXService
from backend.services.stock_service import StockService
from backend.services.llm_service import LLMService
from backend.services.financial_service import FinancialService

def get_dart_service(api_key: str = Header(..., alias="X-DART-API-Key")) -> DARTService:
    """DART 서비스 의존성"""
    if not api_key:
        raise HTTPException(status_code=400, detail="DART API Key required")
    return DARTService(api_key=api_key)

def get_krx_service() -> KRXService:
    """KRX 서비스 의존성"""
    return KRXService()

def get_stock_service() -> StockService:
    """주가 서비스 의존성"""
    return StockService()

def get_llm_service() -> LLMService:
    """LLM 서비스 의존성"""
    return LLMService()

def get_financial_service() -> FinancialService:
    """재무 계산 서비스 의존성"""
    return FinancialService()