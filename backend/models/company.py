from pydantic import BaseModel
from typing import Optional

class Company(BaseModel):
    """회사 도메인 모델"""
    corp_code: str
    corp_name: str
    stock_code: Optional[str] = 'N/A'
    
    class Config:
        from_attributes = True

class CompanySearchResult(BaseModel):
    """회사 검색 결과"""
    companies: list[Company]
    total: int