import requests
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()

class APIClient:
    """FastAPI 백엔드 통신 클라이언트"""
    
    def __init__(self, base_url: str = None):
        # 환경변수에서 백엔드 URL 읽기
        if base_url is None:
            base_url = os.getenv('BACKEND_URL', 'http://localhost:8000')
        self.base_url = base_url
    
    def _get_headers(self, api_key: str) -> dict:
        """API 요청 헤더"""
        return {"X-DART-API-Key": api_key}
    
    def download_companies(self, api_key: str, force_refresh: bool = False) -> dict:
        """전체 기업 목록 다운로드"""
        response = requests.get(
            f"{self.base_url}/api/companies/list",
            params={"force_refresh": force_refresh},
            headers=self._get_headers(api_key)
        )
        response.raise_for_status()
        return response.json()
    
    def search_companies(self, keyword: str, api_key: str) -> List[Dict]:
        """기업 검색"""
        response = requests.get(
            f"{self.base_url}/api/companies/search",
            params={"keyword": keyword},
            headers=self._get_headers(api_key)
        )
        response.raise_for_status()
        return response.json()
    
    def get_financial_data(
        self,
        corp_code: str,
        bsns_year: str,
        fs_div: str,
        api_key: str
    ) -> dict:
        """재무 데이터 조회"""
        response = requests.get(
            f"{self.base_url}/api/financial/{corp_code}",
            params={"bsns_year": bsns_year, "fs_div": fs_div},
            headers=self._get_headers(api_key)
        )
        response.raise_for_status()
        return response.json()
    
    def get_stock_info(
        self,
        corp_code: str,
        stock_code: str,
        corp_name: Optional[str],
        api_key: str,
        bsns_year: Optional[int] = None
    ) -> dict:
        """주가 정보 조회"""
        params = {"stock_code": stock_code}
        if corp_name:
            params["corp_name"] = corp_name
        if bsns_year:
            params["bsns_year"] = bsns_year

        response = requests.get(
            f"{self.base_url}/api/financial/{corp_code}/stock-info",
            params=params,
            headers=self._get_headers(api_key)
        )
        response.raise_for_status()
        return response.json()
    
    def get_disclosures(
        self,
        corp_code: str,
        bsns_year: str,
        api_key: str
    ) -> dict:
        """공시 목록 조회"""
        response = requests.get(
            f"{self.base_url}/api/financial/{corp_code}/disclosures",
            params={"bsns_year": bsns_year},
            headers=self._get_headers(api_key)
        )
        response.raise_for_status()
        return response.json()
    
    def generate_briefing(
        self,
        corp_name: str,
        financial_data: dict,
        provider: str,
        api_key: str,
        style: str = "default"
    ) -> dict:
        """AI 브리핑 생성"""
        payload = {
            "corp_name": corp_name,
            "financial_data": financial_data,
            "provider": provider,
            "api_key": api_key,
            "style": style
        }
        
        response = requests.post(
            f"{self.base_url}/api/briefing/generate",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def download_excel(self, companies: List[Dict]) -> bytes:
        """
        재무 데이터를 엑셀 파일로 다운로드
        
        Args:
            companies: 회사 정보 및 재무 데이터 리스트
        
        Returns:
            bytes: 엑셀 파일 바이너리
        """
        payload = {"companies": companies}
        
        response = requests.post(
            f"{self.base_url}/api/financial/download-excel",
            json=payload
        )
        response.raise_for_status()
        return response.content
    
    def get_financial_documents(
        self,
        corp_code: str,
        api_key: str,
        start_year: Optional[str] = None,
        end_year: Optional[str] = None
    ) -> dict:
        """재무정보가 포함된 공시 문서 목록 조회"""
        params = {}
        if start_year:
            params['start_year'] = start_year
        if end_year:
            params['end_year'] = end_year

        response = requests.get(
            f"{self.base_url}/api/financial/{corp_code}/financial-documents",
            params=params,
            headers=self._get_headers(api_key)
        )
        response.raise_for_status()
        return response.json()

    def extract_from_document(
        self,
        corp_code: str,
        rcept_no: str,
        report_nm: str,
        api_key: str
    ) -> dict:
        """특정 공시 문서에서 재무정보 추출"""
        response = requests.post(
            f"{self.base_url}/api/financial/{corp_code}/extract-from-document",
            params={
                "rcept_no": rcept_no,
                "report_nm": report_nm
            },
            headers=self._get_headers(api_key)
        )
        response.raise_for_status()
        return response.json()

    def calc_per_pbr(
        self,
        corp_code: str,
        stock_code: str,
        corp_name: Optional[str],
        financial_items: List[Dict],
        api_key: str
    ) -> dict:
        """PER/PBR 계산"""
        payload = {
            "stock_code": stock_code,
            "corp_name": corp_name,
            "financial_items": financial_items
        }

        response = requests.post(
            f"{self.base_url}/api/financial/{corp_code}/calc-per-pbr",
            json=payload,
            headers=self._get_headers(api_key)
        )
        response.raise_for_status()
        return response.json()

    def download_briefing_pdf(
        self,
        briefing_text: str,
        company_info: Dict,
        financial_summary: Optional[Dict] = None,
        llm_provider: str = "AI",
        analysis_style: str = "standard"
    ) -> bytes:
        """
        AI 브리핑을 PDF 파일로 다운로드

        Args:
            briefing_text: AI 브리핑 텍스트
            company_info: 회사 정보
            financial_summary: 재무 요약 정보 (선택)
            llm_provider: 사용한 LLM 제공자
            analysis_style: 분석 스타일

        Returns:
            bytes: PDF 파일 바이너리
        """
        payload = {
            "briefing_text": briefing_text,
            "company_info": company_info,
            "financial_summary": financial_summary,
            "llm_provider": llm_provider,
            "analysis_style": analysis_style
        }

        response = requests.post(
            f"{self.base_url}/api/briefing/download-pdf",
            json=payload
        )
        response.raise_for_status()
        return response.content
