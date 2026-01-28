from pydantic import BaseModel, Field
from typing import Optional, List, Dict


# ==================== Company ====================

class Company(BaseModel):
    """회사 정보"""
    corp_code: str = Field(..., description="DART 고유번호")
    corp_name: str = Field(..., description="회사명")
    stock_code: Optional[str] = Field("N/A", description="종목코드")


class CompanySearchResponse(BaseModel):
    """회사 검색 응답"""
    companies: List[Company]
    total: int


# ==================== Financial Data ====================

class FinancialItem(BaseModel):
    """재무 항목"""
    account_nm: str = Field(..., description="계정명")
    account_id: Optional[str] = Field(None, description="계정 ID")
    thstrm_amount: Optional[str] = Field(None, description="당기 금액")
    frmtrm_amount: Optional[str] = Field(None, description="전기 금액")
    bfefrmtrm_amount: Optional[str] = Field(None, description="전전기 금액")
    base_display_name: Optional[str] = Field(None, description="기본 표시명")
    display_name: Optional[str] = Field(None, description="표시명")


class FinancialDataRequest(BaseModel):
    """재무정보 조회 요청"""
    corp_code: str
    bsns_year: str = Field(..., pattern=r"^\d{4}$")
    fs_div: str = Field("CFS", description="재무제표 구분 (CFS: 연결, OFS: 별도)")


class FinancialDataResponse(BaseModel):
    """재무정보 조회 응답"""
    corp_code: str
    corp_name: str
    stock_code: Optional[str]
    bsns_year: str
    fs_div: str
    items: List[FinancialItem]
    ratios: Optional[Dict[str, Dict[str, float]]] = None


# ==================== Financial Ratios ====================

class FinancialRatios(BaseModel):
    """재무 비율"""
    영업이익률: Dict[str, float]
    순이익률: Dict[str, float]
    ROE: Dict[str, float]
    ROA: Dict[str, float]
    부채비율: Dict[str, float]
    자기자본비율: Dict[str, float]
    유동비율: Optional[Dict[str, float]] = None


# ==================== Stock Info ====================

class StockInfo(BaseModel):
    """주가 정보"""
    stock_code: str
    price: Optional[float] = None
    shares: Optional[int] = None
    status: str = Field(..., description="조회 상태 (success, partial, no_data, error)")
    message: Optional[str] = None


class PERPBRData(BaseModel):
    """PER/PBR 데이터"""
    PER: Dict[str, str]  # thstrm, frmtrm, bfefrmtrm
    PBR: Dict[str, str]
    note: Optional[str] = None


# ==================== Briefing ====================

class BriefingRequest(BaseModel):
    """브리핑 생성 요청"""
    corp_name: str
    financial_data: Dict
    style: str = Field("default", description="브리핑 스타일 (default, executive, detailed)")
    llm_provider: str = Field("gemini", description="LLM 제공자 (gemini, openai, claude, upstage)")


class BriefingResponse(BaseModel):
    """브리핑 생성 응답"""
    briefing: str
    provider: str


# ==================== Error ====================

class ErrorResponse(BaseModel):
    """에러 응답"""
    error: str
    detail: Optional[str] = None


# ==================== Disclosure ====================

class Disclosure(BaseModel):
    """공시 정보"""
    rcept_dt: str = Field(..., description="접수일")
    report_nm: str = Field(..., description="보고서명")
    rcept_no: str = Field(..., description="접수번호")


class DisclosureListResponse(BaseModel):
    """공시 목록 응답"""
    corp_code: str
    bsns_year: str
    disclosures: List[Disclosure]
    total: int
