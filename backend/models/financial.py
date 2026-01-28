from pydantic import BaseModel
from typing import Optional, Dict

class FinancialData(BaseModel):
    """재무 데이터 모델"""
    account_id: str
    account_nm: str
    base_display_name: str
    display_name: str
    thstrm_amount: Optional[str] = None  # 당기
    frmtrm_amount: Optional[str] = None  # 전기
    bfefrmtrm_amount: Optional[str] = None  # 전전기
    
    class Config:
        from_attributes = True

class FinancialRatio(BaseModel):
    """재무 비율 모델"""
    name: str
    thstrm: float
    frmtrm: float
    bfefrmtrm: float

class StockInfo(BaseModel):
    """주가 정보 모델"""
    status: str
    price: Optional[float] = None
    shares: Optional[float] = None
    message: Optional[str] = None
    debug: Optional[list] = []

class PERPBRData(BaseModel):
    """PER/PBR 데이터"""
    PER: Dict[str, str]
    PBR: Dict[str, str]
    note: Optional[str] = None