from typing import List, Dict, Optional
from backend.repositories.dart_repository import DARTRepository
from backend.repositories.krx_repository import KRXRepository
from backend.core.exceptions import CompanyNotFoundException
from backend.services.unlisted_financial_service import UnlistedFinancialService
from backend.core.llm.upstage import UpstageProvider
from backend.core.config import settings
from collections import Counter


# 계정 ID 매핑
ACCOUNT_ID_MAP = {
    'ifrs-full_Assets': '자산총계',
    'ifrs-full_Liabilities': '부채총계',
    'ifrs-full_Equity': '자본총계',
    'ifrs-full_Revenue': '매출액',
    'dart_OperatingIncomeLoss': '영업이익',
    'ifrs-full_ProfitLoss': '당기순이익',
    'dart_ProfitLossAttributableToOwnersOfParent': '당기순이익',
    'ifrs-full_ProfitLossAttributableToOwnersOfParent': '당기순이익',
}


class DARTService:
    """DART 비즈니스 로직"""

    def __init__(self, api_key: Optional[str] = None):
        self.dart_repo = DARTRepository(api_key)
        self.krx_repo = KRXRepository()
        self._corp_list_cache = None

        # 비상장 기업 처리를 위한 서비스
        if settings.upstage_api_key:
            upstage_provider = UpstageProvider(settings.upstage_api_key)
            self.unlisted_service = UnlistedFinancialService(self.dart_repo, upstage_provider)
        else:
            self.unlisted_service = None
    
    def get_corp_list(self, force_refresh: bool = False) -> List[Dict]:
        """회사 목록 조회 (캐시 사용)"""
        if self._corp_list_cache is None or force_refresh:
            self._corp_list_cache = self.dart_repo.download_corp_codes()
        return self._corp_list_cache
    
    def search_companies(self, keyword: str) -> List[Dict]:
        """회사 검색
        
        Args:
            keyword: 검색 키워드 (회사명, 종목코드, 고유번호)
            
        Returns:
            검색 결과 리스트
        """
        if not keyword:
            return []
        
        corp_list = self.get_corp_list()
        
        results = [
            c for c in corp_list
            if keyword.lower() in c['corp_name'].lower()
            or keyword == c['corp_code']
            or (c['stock_code'] != 'N/A' and keyword == c['stock_code'])
        ]
        
        # 상장회사 우선, 이름순 정렬
        results.sort(key=lambda c: (0 if c['stock_code'] != 'N/A' else 1, c['corp_name']))
        
        return results
    
    def get_company_by_code(self, corp_code: str) -> Dict:
        """고유번호로 회사 정보 조회"""
        corp_list = self.get_corp_list()
        
        for corp in corp_list:
            if corp['corp_code'] == corp_code:
                return corp
        
        raise CompanyNotFoundException(f"회사를 찾을 수 없습니다: {corp_code}")
    
    async def get_financial_data(
        self,
        corp_code: str,
        bsns_year: str,
        fs_div: str = 'CFS'
    ) -> Dict:
        """재무정보 조회 및 가공

        Args:
            corp_code: 기업 고유번호
            bsns_year: 사업연도
            fs_div: 재무제표 구분

        Returns:
            가공된 재무 데이터
        """
        # 회사 정보 조회
        company = self.get_company_by_code(corp_code)
        is_listed = company['stock_code'] != 'N/A'

        # 상장 기업: 기존 로직
        if is_listed:
            # 재무 데이터 조회
            raw_data = self.dart_repo.get_financial_data(corp_code, bsns_year, fs_div)

            if not raw_data:
                # 빈 결과 반환 (데이터 없음)
                return {
                    'corp_code': corp_code,
                    'corp_name': company['corp_name'],
                    'stock_code': company['stock_code'],
                    'bsns_year': bsns_year,
                    'fs_div': fs_div,
                    'items': [],
                    'ratios': {},
                    'is_listed': True
                }

            # 데이터 가공
            processed = self._prepare_data(raw_data)

            # 재무비율 계산
            ratios = self._calc_ratios(processed)

            return {
                'corp_code': corp_code,
                'corp_name': company['corp_name'],
                'stock_code': company['stock_code'],
                'bsns_year': bsns_year,
                'fs_div': fs_div,
                'items': processed,
                'ratios': ratios,
                'is_listed': True
            }

        # 비상장 기업: 문서 파싱 (fs_div 무시)
        else:
            if not self.unlisted_service:
                return {
                    'corp_code': corp_code,
                    'corp_name': company['corp_name'],
                    'stock_code': company['stock_code'],
                    'bsns_year': bsns_year,
                    'fs_div': 'N/A',  # 비상장 기업은 연결/별도 구분 없음
                    'items': [],
                    'ratios': {},
                    'is_listed': False,
                    'error': 'Upstage API 키가 설정되지 않았습니다. 비상장 기업 재무정보를 조회할 수 없습니다.'
                }

            try:
                # 비상장 기업 재무정보 추출 (fs_div 무시)
                raw_data = await self.unlisted_service.get_unlisted_financial_data(
                    corp_code,
                    company['corp_name'],
                    bsns_year
                )

                if not raw_data:
                    return {
                        'corp_code': corp_code,
                        'corp_name': company['corp_name'],
                        'stock_code': company['stock_code'],
                        'bsns_year': bsns_year,
                        'fs_div': 'N/A',
                        'items': [],
                        'ratios': {},
                        'is_listed': False,
                        'error': '사업보고서 또는 감사보고서를 찾을 수 없습니다.'
                    }

                # 데이터 가공
                processed = self._prepare_data(raw_data)

                # 재무비율 계산
                ratios = self._calc_ratios(processed)

                return {
                    'corp_code': corp_code,
                    'corp_name': company['corp_name'],
                    'stock_code': company['stock_code'],
                    'bsns_year': bsns_year,
                    'fs_div': 'N/A',  # 비상장 기업은 연결/별도 구분 없음
                    'items': processed,
                    'ratios': ratios,
                    'is_listed': False,
                    'source': '사업보고서/감사보고서 (AI 파싱)'
                }

            except Exception as e:
                return {
                    'corp_code': corp_code,
                    'corp_name': company['corp_name'],
                    'stock_code': company['stock_code'],
                    'bsns_year': bsns_year,
                    'fs_div': 'N/A',
                    'items': [],
                    'ratios': {},
                    'is_listed': False,
                    'error': f'비상장 기업 재무정보 조회 실패: {str(e)}'
                }
    
    def _prepare_data(self, data: List[Dict]) -> List[Dict]:
        """재무 데이터 전처리"""
        for item in data:
            account_id = item.get('account_id', '')
            account_nm = item.get('account_nm', '')
            
            # 기본 표시명 설정
            if account_id in ACCOUNT_ID_MAP:
                item['base_display_name'] = ACCOUNT_ID_MAP[account_id]
            elif '당기순이익' in account_nm:
                item['base_display_name'] = '당기순이익'
            else:
                item['base_display_name'] = account_nm
        
        # 중복 계정 처리
        counts = Counter(i['base_display_name'] for i in data)
        for item in data:
            if counts[item['base_display_name']] > 1:
                item['display_name'] = f"{item['base_display_name']} ({item.get('account_id', '')})"
            else:
                item['display_name'] = item['base_display_name']
        
        return data
    
    def _calc_ratios(self, data: List[Dict]) -> Dict[str, Dict[str, float]]:
        """재무비율 계산"""
        from backend.utils.formatters import safe_float
        
        # 계정별 금액 추출
        accts = {
            i.get('base_display_name'): {
                'thstrm': safe_float(i.get('thstrm_amount')),
                'frmtrm': safe_float(i.get('frmtrm_amount')),
                'bfefrmtrm': safe_float(i.get('bfefrmtrm_amount'))
            }
            for i in data
        }
        
        def ratio(numerator: str, denominator: str, percentage: bool = True) -> Dict[str, float]:
            """비율 계산 헬퍼"""
            result = {}
            for period in ['thstrm', 'frmtrm', 'bfefrmtrm']:
                num = accts.get(numerator, {}).get(period, 0)
                den = accts.get(denominator, {}).get(period, 1)
                
                if den != 0:
                    value = (num / den) * (100 if percentage else 1)
                    result[period] = round(value, 2)
                else:
                    result[period] = 0.0
            
            return result
        
        return {
            '영업이익률': ratio('영업이익', '매출액', True),
            '순이익률': ratio('당기순이익', '매출액', True),
            'ROE': ratio('당기순이익', '자본총계', True),
            'ROA': ratio('당기순이익', '자산총계', True),
            '부채비율': ratio('부채총계', '자본총계', True),
            '자기자본비율': ratio('자본총계', '자산총계', True),
        }
    
    def get_disclosure_list(self, corp_code: str, bsns_year: str) -> Dict:
        """공시 목록 조회"""
        company = self.get_company_by_code(corp_code)
        disclosures = self.dart_repo.get_disclosure_list(corp_code, bsns_year)
        
        return {
            'corp_code': corp_code,
            'corp_name': company['corp_name'],
            'bsns_year': bsns_year,
            'disclosures': disclosures,
            'total': len(disclosures)
        }
