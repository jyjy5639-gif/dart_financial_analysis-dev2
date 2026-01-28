from backend.repositories.krx_repository import KRXRepository
from typing import Optional
import pandas as pd

class KRXService:
    """KRX 비즈니스 로직"""
    
    def __init__(self):
        self.repository = KRXRepository()
    
    def get_stock_code(self, corp_name: str) -> Optional[str]:
        """회사명으로 종목코드 조회"""
        return self.repository.find_by_name(corp_name)
    
    def download_krx_data(self, force_refresh: bool = False) -> pd.DataFrame:
        """KRX 데이터 다운로드
        
        Args:
            force_refresh: True면 캐시 무시하고 새로 다운로드
            
        Returns:
            KRX 데이터 DataFrame
        """
        return self.repository.download_krx_codes(force_refresh)
    
    def search_by_name(self, corp_name: str) -> Optional[str]:
        """회사명으로 종목코드 검색 (별칭)"""
        return self.get_stock_code(corp_name)