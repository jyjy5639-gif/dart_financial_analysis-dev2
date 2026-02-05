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
        corp_name: Optional[str] = None,
        bsns_year: Optional[int] = None
    ) -> Dict:
        """주가 정보 조회

        Args:
            stock_code: 종목코드
            corp_name: 회사명 (종목코드가 없을 때 검색용)
            bsns_year: 조회년도 (연말 지표 조회용, 선택)

        Returns:
            주가 정보 (확장된 데이터 포함)
        """
        # 종목코드가 없으면 회사명으로 검색
        resolved_stock_code = stock_code
        if stock_code == 'N/A' or not stock_code:
            if corp_name:
                resolved_stock_code = self.krx_repo.get_krx_code_by_name(corp_name)
                if not resolved_stock_code:
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
        stock_info = self.stock_repo.get_stock_price(resolved_stock_code)

        # 연말 지표 조회 (bsns_year가 제공된 경우)
        if bsns_year and stock_info.get('status') in ['success', 'partial']:
            debug_log = stock_info.get('debug', [])
            year_end_data = self.stock_repo.get_year_end_fundamental(
                resolved_stock_code, bsns_year, debug_log
            )
            stock_info['year_end'] = year_end_data

        # 포맷팅된 데이터 추가
        if stock_info.get('status') in ['success', 'partial']:
            stock_info['formatted'] = self.format_stock_display(stock_info)

        return stock_info

    def format_stock_display(self, stock_info: Dict) -> Dict:
        """프론트엔드 표시용 포맷팅

        Args:
            stock_info: 원본 주가 정보

        Returns:
            포맷팅된 표시용 데이터
        """
        formatted = {}

        # 현재가
        price = stock_info.get('price')
        if price:
            formatted['current_price'] = f"{int(price):,}원"
        else:
            formatted['current_price'] = '-'

        # 전일대비 및 등락률
        change = stock_info.get('change')
        change_rate = stock_info.get('change_rate')
        if change is not None and change_rate is not None:
            sign = '+' if change >= 0 else ''
            formatted['change'] = f"{sign}{int(change):,}원 ({sign}{change_rate:.2f}%)"
            formatted['change_value'] = change
            formatted['change_rate_value'] = change_rate
        else:
            formatted['change'] = '-'
            formatted['change_value'] = 0
            formatted['change_rate_value'] = 0

        # 거래량
        volume = stock_info.get('volume')
        if volume:
            formatted['volume'] = f"{volume:,}주"
        else:
            formatted['volume'] = '-'

        # 시가총액
        market_cap = stock_info.get('market_cap')
        if market_cap:
            if market_cap >= 1000000000000:  # 1조 이상
                formatted['market_cap'] = f"{market_cap / 1000000000000:.1f}조원"
            elif market_cap >= 100000000:  # 1억 이상
                formatted['market_cap'] = f"{market_cap / 100000000:,.0f}억원"
            else:
                formatted['market_cap'] = f"{market_cap:,}원"
        else:
            formatted['market_cap'] = '-'

        # 52주 최고/최저
        high_52 = stock_info.get('high_52week')
        low_52 = stock_info.get('low_52week')
        if high_52 and low_52:
            formatted['week52_range'] = f"{int(low_52):,}원 ~ {int(high_52):,}원"
            formatted['high_52week'] = f"{int(high_52):,}원"
            formatted['low_52week'] = f"{int(low_52):,}원"
        else:
            formatted['week52_range'] = '-'
            formatted['high_52week'] = '-'
            formatted['low_52week'] = '-'

        # 당일 시가/고가/저가/전일종가
        open_price = stock_info.get('open_price')
        high_price = stock_info.get('high_price')
        low_price = stock_info.get('low_price')
        prev_close = stock_info.get('prev_close')

        formatted['open_price'] = f"{int(open_price):,}원" if open_price else '-'
        formatted['high_price'] = f"{int(high_price):,}원" if high_price else '-'
        formatted['low_price'] = f"{int(low_price):,}원" if low_price else '-'
        formatted['prev_close'] = f"{int(prev_close):,}원" if prev_close else '-'

        # 상장주식수
        shares = stock_info.get('shares')
        if shares:
            formatted['shares'] = f"{shares:,}주"
        else:
            formatted['shares'] = '-'

        # PER
        per = stock_info.get('per')
        formatted['per'] = f"{per:.2f}배" if per else '-'

        # PBR
        pbr = stock_info.get('pbr')
        formatted['pbr'] = f"{pbr:.2f}배" if pbr else '-'

        # EPS
        eps = stock_info.get('eps')
        formatted['eps'] = f"{int(eps):,}원" if eps else '-'

        # BPS
        bps = stock_info.get('bps')
        formatted['bps'] = f"{int(bps):,}원" if bps else '-'

        # 배당수익률
        div_yield = stock_info.get('div_yield')
        formatted['div_yield'] = f"{div_yield:.2f}%" if div_yield else '-'

        # 외국인 지분율
        foreign_ratio = stock_info.get('foreign_ratio')
        formatted['foreign_ratio'] = f"{foreign_ratio:.2f}%" if foreign_ratio else '-'

        # 데이터 기준일
        data_date = stock_info.get('data_date')
        if data_date:
            formatted['data_date'] = f"{data_date[:4]}-{data_date[4:6]}-{data_date[6:8]}"
            formatted['data_date_label'] = f"{data_date[:4]}년 {int(data_date[4:6])}월 {int(data_date[6:8])}일 값"
        else:
            formatted['data_date'] = '-'
            formatted['data_date_label'] = '값'

        # 연말 데이터 포맷팅
        year_end = stock_info.get('year_end', {})
        if year_end and year_end.get('data_year'):
            year_end_year = year_end.get('data_year')
            year_end_date = year_end.get('data_date', '')

            formatted['year_end_label'] = f"{year_end_year} 년말 지표"
            formatted['year_end_per'] = f"{year_end['per']:.2f}배" if year_end.get('per') else '-'
            formatted['year_end_pbr'] = f"{year_end['pbr']:.2f}배" if year_end.get('pbr') else '-'
            formatted['year_end_eps'] = f"{int(year_end['eps']):,}원" if year_end.get('eps') else '-'
            formatted['year_end_bps'] = f"{int(year_end['bps']):,}원" if year_end.get('bps') else '-'
            formatted['year_end_div_yield'] = f"{year_end['div_yield']:.2f}%" if year_end.get('div_yield') else '-'

            if year_end_date:
                formatted['year_end_date'] = f"{year_end_date[:4]}-{year_end_date[4:6]}-{year_end_date[6:8]}"
            else:
                formatted['year_end_date'] = '-'
        else:
            formatted['year_end_label'] = '년말 지표'
            formatted['year_end_per'] = '-'
            formatted['year_end_pbr'] = '-'
            formatted['year_end_eps'] = '-'
            formatted['year_end_bps'] = '-'
            formatted['year_end_div_yield'] = '-'
            formatted['year_end_date'] = '-'

        return formatted
    
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
