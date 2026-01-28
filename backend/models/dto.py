from pydantic import BaseModel
from typing import Optional, List
from .company import Company
from .financial import FinancialData, FinancialRatio

class CompanySearchRequest(BaseModel):
    """회사 검색 요청"""
    keyword: str
    api_key: str

class CompanySearchResponse(BaseModel):
    """회사 검색 응답"""
    companies: List[Company]
    total: int

class FinancialDataRequest(BaseModel):
    """재무 데이터 조회 요청"""
    corp_code: str
    bsns_year: str
    fs_div: str = 'CFS'
    api_key: str

class FinancialDataResponse(BaseModel):
    """재무 데이터 조회 응답"""
    corp_name: str
    corp_code: str
    stock_code: str
    financial_data: List[FinancialData]
    ratios: List[FinancialRatio]

class BriefingRequest(BaseModel):
    """브리핑 생성 요청"""
    corp_name: str
    financial_data: List[dict]
    provider: str = 'gemini'
    style: str = 'default'
    api_key: str

class BriefingResponse(BaseModel):
    """브리핑 생성 응답"""
    briefing: str
    provider: str