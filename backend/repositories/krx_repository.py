import pandas as pd
import os
import requests
from bs4 import BeautifulSoup
from typing import Optional
from backend.core.exceptions import KRXDataException
from backend.core.config import settings
from backend.core.logger import get_backend_logger

logger = get_backend_logger("krx_repository")


class KRXRepository:
    """KRX 데이터 액세스 레이어"""
    
    def __init__(self, cache_file: str = "krx_codes.csv"):
        self.cache_file = cache_file
        self.krx_url = settings.krx_url
    
    def download_krx_codes(self, force_refresh: bool = False) -> pd.DataFrame:
        """KRX 공식 종목코드 다운로드
        
        Args:
            force_refresh: True면 캐시 무시하고 새로 다운로드
        """
        
        # 캐시 확인 (force_refresh가 아닐 때만)
        if not force_refresh and os.path.exists(self.cache_file):
            try:
                df = pd.read_csv(self.cache_file, dtype={'종목코드': str})
                logger.info(f"KRX 데이터 캐시 로드: {len(df)}개")
                return df
            except Exception as e:
                logger.warning(f"캐시 로드 실패: {e}")
        
        # 방법 1: KRX 공식 사이트
        try:
            logger.info("KRX 공식 사이트에서 다운로드 시도...")
            url = f'{self.krx_url}?method=download&searchType=13'
            
            df = pd.read_csv(url, dtype={'종목코드': str}, encoding='cp949')
            
            # 컬럼명 정리
            df.columns = ['회사명', '종목코드', '업종', '주요제품', '상장일', 
                         '결산월', '대표자명', '홈페이지', '지역']
            
            # 종목코드 패딩 (6자리)
            df['종목코드'] = df['종목코드'].astype(str).str.zfill(6)
            
            # CSV 저장
            df.to_csv(self.cache_file, index=False, encoding='utf-8-sig')
            
            logger.info(f"KRX 데이터 다운로드 성공: {len(df)}개")
            return df
            
        except Exception as e1:
            logger.error(f"KRX 공식 다운로드 실패: {e1}")
            
            # 방법 2: 네이버 금융 파싱
            try:
                logger.info("네이버 금융에서 파싱 시도...")
                df = self._download_from_naver()
                if df is not None and not df.empty:
                    df.to_csv(self.cache_file, index=False, encoding='utf-8-sig')
                    logger.info(f"네이버 금융 파싱 성공: {len(df)}개")
                    return df
            except Exception as e2:
                logger.error(f"네이버 금융 파싱 실패: {e2}")
            
            # 방법 3: Fallback 데이터
            try:
                logger.warning("Fallback 데이터 사용")
                return self._get_fallback_data()
            except Exception as e3:
                raise KRXDataException(f"KRX 데이터 다운로드 실패: {str(e1)}, {str(e3)}")
    
    def _download_from_naver(self) -> Optional[pd.DataFrame]:
        """네이버 금융에서 종목 리스트 파싱 (Fallback)"""
        try:
            url = "https://finance.naver.com/sise/siseListData.nhn"
            
            data = []
            # 최대 5페이지만 (너무 많으면 느림)
            for page in range(1, 6):
                params = {'gubun': 0, 'page': page}
                headers = {'User-Agent': 'Mozilla/5.0'}
                
                response = requests.get(url, params=params, headers=headers, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                rows = soup.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        try:
                            name = cols[0].text.strip()
                            code = cols[1].text.strip()
                            if name and code and code.isdigit():
                                data.append({'회사명': name, '종목코드': code.zfill(6)})
                        except:
                            continue
            
            if data:
                return pd.DataFrame(data)
            return None
            
        except Exception as e:
            logger.error(f"네이버 파싱 실패: {e}")
            return None
    
    def _get_fallback_data(self) -> pd.DataFrame:
        """Fallback: 최소 데이터 (주요 대형주)"""
        return pd.DataFrame({
            '회사명': ['삼성전자', '현대차', 'SK하이닉스', 'LG전자', 
                     'NAVER', 'Kakao', '선광', '알테오젠', 'POSCO홀딩스',
                     '기아', 'KB금융', '신한지주', '삼성바이오로직스'],
            '종목코드': ['005930', '005380', '000660', '066570',
                       '035420', '035720', '003100', '196100', '005490',
                       '000270', '105560', '055550', '207940']
        })
    
    def get_krx_code_by_name(self, corp_name: str) -> Optional[str]:
        """회사명으로 KRX 공식 종목코드 검색
        
        Args:
            corp_name: 검색할 회사명
            
        Returns:
            종목코드 (6자리) 또는 None
        """
        
        try:
            df = self.download_krx_codes()
            
            if df is None or df.empty:
                logger.warning("KRX 데이터가 비어있음")
                return None
            
            # 1. 정확한 매칭
            exact = df[df['회사명'] == corp_name]
            if not exact.empty:
                code = exact.iloc[0]['종목코드']
                logger.info(f"정확 매칭: {corp_name} -> {code}")
                return code
            
            # 2. 부분 매칭 (포함)
            partial = df[df['회사명'].str.contains(corp_name, na=False, regex=False)]
            if not partial.empty:
                code = partial.iloc[0]['종목코드']
                logger.info(f"부분 매칭: {corp_name} -> {partial.iloc[0]['회사명']} ({code})")
                return code
            
            # 3. 공백 제거 후 매칭
            corp_name_stripped = corp_name.replace(' ', '')
            df['회사명_stripped'] = df['회사명'].str.replace(' ', '')
            stripped_match = df[df['회사명_stripped'] == corp_name_stripped]
            if not stripped_match.empty:
                code = stripped_match.iloc[0]['종목코드']
                logger.info(f"공백 무시 매칭: {corp_name} -> {stripped_match.iloc[0]['회사명']} ({code})")
                return code
            
            logger.info(f"매칭 실패: {corp_name}")
            return None
            
        except Exception as e:
            logger.error(f"종목코드 검색 오류: {e}")
            return None
    
    def find_by_name(self, corp_name: str) -> Optional[str]:
        """회사명으로 종목코드 찾기 (별칭)"""
        return self.get_krx_code_by_name(corp_name)
