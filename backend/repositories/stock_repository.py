import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, Optional
from backend.core.exceptions import StockInfoException


class StockRepository:
    """주가 정보 데이터 액세스 레이어"""
    
    def __init__(self):
        self.base_url = "https://finance.naver.com/item/main.nhn"
    
    def get_stock_price(self, stock_code: str) -> Dict:
        """네이버 금융에서 주가 정보 조회
        
        Args:
            stock_code: 종목코드 (6자리)
            
        Returns:
            {
                'status': 'success' | 'partial' | 'no_data' | 'error',
                'price': float or None,
                'shares': int or None,
                'message': str or None,
                'debug': List[str]
            }
        """
        
        debug_log = []
        
        if not stock_code or stock_code == 'N/A':
            debug_log.append(f"유효하지 않은 종목코드: {stock_code}")
            return {
                'status': 'no_data',
                'price': None,
                'shares': None,
                'message': '비상장 회사',
                'debug': debug_log
            }
        
        try:
            debug_log.append(f"네이버 금융 조회 시작: {stock_code}")
            
            url = f"{self.base_url}?code={stock_code}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                debug_log.append(f"네이버 금융 접속 실패: {response.status_code}")
                return {
                    'status': 'error',
                    'price': None,
                    'shares': None,
                    'message': '주가 정보 조회 실패',
                    'debug': debug_log
                }
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 주가 추출
            price = self._extract_price(soup, debug_log, response.text)
            
            if not price:
                debug_log.append("주가 파싱 실패")
                return {
                    'status': 'no_data',
                    'price': None,
                    'shares': None,
                    'message': '주가 파싱 실패',
                    'debug': debug_log
                }
            
            debug_log.append(f"주가 조회 성공: {price}")
            
            # 주식수는 현재 크롤링으로 얻기 어려움 (DART 데이터 필요)
            return {
                'status': 'partial',
                'price': price,
                'shares': None,
                'message': '주가는 조회됨 (주식수는 DART 데이터 필요)',
                'debug': debug_log
            }
            
        except Exception as e:
            debug_log.append(f"조회 실패: {type(e).__name__}: {str(e)}")
            return {
                'status': 'error',
                'price': None,
                'shares': None,
                'message': f'조회 실패: {str(e)}',
                'debug': debug_log
            }
    
    def _extract_price(self, soup: BeautifulSoup, debug_log: list, html_text: str = "") -> Optional[float]:
        """HTML에서 주가 추출 (다중 방법 시도)"""
        
        # 방법 1: 다양한 선택자 시도
        selectors = [
            'span._stock-price-var',
            'strong._price',
            'em#_price_now',
            'span.rate_text',
            'strong#_now_value',
            'p.no_today em',
            'em[id*="price"]',
            'div.rate_info span',
            'div#time_area p em',
            'span.today em',
            'p.no_today .blind',
            'span.code',
            'strong#_nowVal',
            'div.rate_info .blind'
        ]
        
        for selector in selectors:
            try:
                elem = soup.select_one(selector)
                if elem and elem.text.strip():
                    text = elem.text.strip().replace(',', '').replace('현재가', '').strip()
                    # 숫자만 추출
                    match = re.search(r'\d+', text)
                    if match:
                        price = float(match.group())
                        # 합리적인 가격 범위 확인 (100원 ~ 10,000,000원)
                        if 100 <= price <= 10000000:
                            debug_log.append(f"주가 추출 성공 (선택자: {selector}): {price}")
                            return price
            except Exception as e:
                continue
        
        # 방법 2: 정규식으로 HTML에서 직접 추출
        debug_log.append("선택자 실패, 정규식으로 시도...")
        try:
            # no_today 클래스 영역에서 찾기
            prices = re.findall(r'no_today.*?(\d{1,3}(?:,\d{3})*)', str(soup), re.DOTALL)
            if prices:
                for price_str in prices:
                    try:
                        price = float(price_str.replace(',', ''))
                        if 100 <= price <= 10000000:
                            debug_log.append(f"정규식으로 주가 추출 (no_today): {price}")
                            return price
                    except:
                        continue
            
            # 모든 숫자 패턴 찾기 (최후의 수단)
            all_prices = re.findall(r'[\d,]+(?:\.\d+)?', soup.text)
            if all_prices:
                price_candidates = []
                for p in all_prices:
                    try:
                        val = float(p.replace(',', ''))
                        # 합리적인 주가 범위
                        if 100 <= val <= 10000000 and len(p.replace(',', '')) >= 3:
                            price_candidates.append(val)
                    except:
                        continue
                
                if price_candidates:
                    # 중간값 사용 (극단값 피하기)
                    price_candidates.sort()
                    median_idx = len(price_candidates) // 2
                    price = price_candidates[median_idx]
                    debug_log.append(f"정규식으로 주가 추출 (중간값): {price}")
                    return price
        except Exception as e:
            debug_log.append(f"정규식 추출 실패: {e}")
        
        return None
