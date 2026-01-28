from typing import Dict, Optional
from backend.repositories.stock_repository import StockRepository
from backend.repositories.krx_repository import KRXRepository
from backend.utils.formatters import safe_float


class StockService:
    """주가 정보 비즈니스 로직"""
    
    def __init__(self):
        self.stock_repo = StockRepository()
        self.krx_repo = KRXRepository()
    
    def get_stock_info(
        self,
        stock_code: str,
        corp_name: Optional[str] = None
    ) -> Dict:
        """주가 정보 조회
        
        Args:
            stock_code: 종목코드
            corp_name: 회사명 (종목코드가 없을 때 검색용)
            
        Returns:
            주가 정보
        """
        # 종목코드가 없으면 회사명으로 검색
        if stock_code == 'N/A' or not stock_code:
            if corp_name:
                stock_code = self.krx_repo.get_krx_code_by_name(corp_name)
                if not stock_code:
                    return {
                        'status': 'no_data',
                        'price': None,
                        'shares': None,
                        'message': '비상장 회사 (KRX에서 찾을 수 없음)',
                        'debug': [f"회사명 검색 실패: {corp_name}"]
                    }
            else:
                return {
                    'status': 'no_data',
                    'price': None,
                    'shares': None,
                    'message': '비상장 회사',
                    'debug': []
                }
        
        # 주가 조회
        return self.stock_repo.get_stock_price(stock_code)
    
    def calc_per_pbr(
        self,
        financial_data: Dict,
        stock_info: Dict
    ) -> Dict:
        """PER, PBR 계산
        
        Args:
            financial_data: 재무 데이터
            stock_info: 주가 정보
            
        Returns:
            PER, PBR 데이터
        """
        # 주가 데이터 없음
        if stock_info['status'] == 'no_data':
            return {
                'PER': {'thstrm': 'N/A', 'frmtrm': 'N/A', 'bfefrmtrm': 'N/A'},
                'PBR': {'thstrm': 'N/A', 'frmtrm': 'N/A', 'bfefrmtrm': 'N/A'},
                'note': '비상장 회사'
            }
        
        # 조회 오류
        if stock_info['status'] == 'error':
            return {
                'PER': {'thstrm': '오류', 'frmtrm': '오류', 'bfefrmtrm': '오류'},
                'PBR': {'thstrm': '오류', 'frmtrm': '오류', 'bfefrmtrm': '오류'},
                'note': stock_info['message']
            }
        
        stock_price = stock_info['price']
        shares = stock_info.get('shares')
        
        # 주식수 정보 없음
        if shares is None:
            return {
                'PER': {'thstrm': 'N/A', 'frmtrm': 'N/A', 'bfefrmtrm': 'N/A'},
                'PBR': {'thstrm': 'N/A', 'frmtrm': 'N/A', 'bfefrmtrm': 'N/A'},
                'note': '발행주식수 정보 없음 (데이터 제공자 한계)'
            }
        
        try:
            # 계정별 금액 추출
            items = financial_data.get('items', [])
            accts = {
                i.get('base_display_name'): {
                    'thstrm': safe_float(i.get('thstrm_amount')),
                    'frmtrm': safe_float(i.get('frmtrm_amount')),
                    'bfefrmtrm': safe_float(i.get('bfefrmtrm_amount'))
                }
                for i in items
            }
            
            # 당기순이익과 자본총계
            net_profit = accts.get('당기순이익', {})
            equity = accts.get('자본총계', {})
            
            # EPS, BPS 계산
            per_data = {}
            pbr_data = {}
            
            for period in ['thstrm', 'frmtrm', 'bfefrmtrm']:
                # EPS = 당기순이익 / 주식수
                eps = net_profit.get(period, 0) / shares if shares > 0 else 0
                
                # BPS = 자본총계 / 주식수
                bps = equity.get(period, 0) / shares if shares > 0 else 0
                
                # PER = 주가 / EPS
                per = stock_price / eps if eps > 0 else None
                per_data[period] = f"{per:.2f}" if per else 'N/A'
                
                # PBR = 주가 / BPS
                pbr = stock_price / bps if bps > 0 else None
                pbr_data[period] = f"{pbr:.2f}" if pbr else 'N/A'
            
            return {
                'PER': per_data,
                'PBR': pbr_data,
                'note': None
            }
            
        except Exception as e:
            return {
                'PER': {'thstrm': '오류', 'frmtrm': '오류', 'bfefrmtrm': '오류'},
                'PBR': {'thstrm': '오류', 'frmtrm': '오류', 'bfefrmtrm': '오류'},
                'note': f'계산 오류: {str(e)}'
            }
