from datetime import datetime, timedelta
from typing import Dict, Optional
from pykrx import stock


class StockRepository:
    """주가 정보 데이터 액세스 레이어 (pykrx 사용)"""

    def __init__(self):
        pass

    def _get_latest_business_date(self) -> str:
        """최근 영업일 계산 (YYYYMMDD 형식)"""
        today = datetime.now()
        # 주말이면 금요일로 조정
        if today.weekday() == 5:  # 토요일
            today = today - timedelta(days=1)
        elif today.weekday() == 6:  # 일요일
            today = today - timedelta(days=2)
        return today.strftime("%Y%m%d")

    def _get_52week_ago_date(self) -> str:
        """52주 전 날짜 계산 (YYYYMMDD 형식)"""
        date_52w_ago = datetime.now() - timedelta(weeks=52)
        return date_52w_ago.strftime("%Y%m%d")

    def get_stock_price(self, stock_code: str) -> Dict:
        """pykrx를 사용하여 주가 정보 조회

        Args:
            stock_code: 종목코드 (6자리)

        Returns:
            {
                'status': 'success' | 'partial' | 'no_data' | 'error',
                'price': float or None,
                'change': float or None,
                'change_rate': float or None,
                'volume': int or None,
                'market_cap': int or None,
                'high_52week': float or None,
                'low_52week': float or None,
                'open_price': float or None,
                'high_price': float or None,
                'low_price': float or None,
                'prev_close': float or None,
                'shares': int or None,
                'per': float or None,
                'pbr': float or None,
                'eps': float or None,
                'bps': float or None,
                'div_yield': float or None,
                'foreign_ratio': float or None,
                'data_date': str or None,
                'message': str or None,
                'debug': List[str]
            }
        """
        debug_log = []

        if not stock_code or stock_code == 'N/A':
            debug_log.append(f"유효하지 않은 종목코드: {stock_code}")
            return self._empty_result('비상장 회사', debug_log)

        try:
            debug_log.append(f"pykrx 조회 시작: {stock_code}")
            latest_date = self._get_latest_business_date()
            debug_log.append(f"조회 기준일: {latest_date}")

            # 1. OHLCV 데이터 조회 (최근 2일 - 전일대비 계산용)
            ohlcv = self._get_ohlcv_data(stock_code, latest_date, debug_log)
            if ohlcv is None:
                return self._empty_result('OHLCV 데이터 조회 실패', debug_log)

            # 2. 시가총액 데이터 조회
            cap_data = self._get_market_cap_data(stock_code, latest_date, debug_log)

            # 3. 펀더멘털 데이터 조회 (PER, PBR, EPS 등)
            fundamental = self._get_fundamental_data(stock_code, latest_date, debug_log)

            # 4. 52주 최고/최저 계산
            week52 = self._get_52week_high_low(stock_code, debug_log)

            return {
                'status': 'success',
                'price': ohlcv.get('close'),
                'change': ohlcv.get('change'),
                'change_rate': ohlcv.get('change_rate'),
                'volume': ohlcv.get('volume'),
                'market_cap': cap_data.get('market_cap'),
                'high_52week': week52.get('high'),
                'low_52week': week52.get('low'),
                'open_price': ohlcv.get('open'),
                'high_price': ohlcv.get('high'),
                'low_price': ohlcv.get('low'),
                'prev_close': ohlcv.get('prev_close'),
                'shares': cap_data.get('shares'),
                'per': fundamental.get('per'),
                'pbr': fundamental.get('pbr'),
                'eps': fundamental.get('eps'),
                'bps': fundamental.get('bps'),
                'div_yield': fundamental.get('div_yield'),
                'foreign_ratio': cap_data.get('foreign_ratio'),
                'data_date': latest_date,
                'message': None,
                'debug': debug_log
            }

        except Exception as e:
            debug_log.append(f"조회 실패: {type(e).__name__}: {str(e)}")
            return self._empty_result(f'조회 실패: {str(e)}', debug_log)

    def _get_ohlcv_data(self, stock_code: str, date: str, debug_log: list) -> Optional[Dict]:
        """OHLCV 데이터 조회"""
        try:
            # 최근 5일 데이터 조회 (영업일 확인용)
            start_date = (datetime.strptime(date, "%Y%m%d") - timedelta(days=10)).strftime("%Y%m%d")
            df = stock.get_market_ohlcv(start_date, date, stock_code)

            if df.empty:
                debug_log.append("OHLCV 데이터 없음")
                return None

            # 최근 영업일 데이터
            latest = df.iloc[-1]
            debug_log.append(f"OHLCV 조회 성공: 종가={latest['종가']}, 거래량={latest['거래량']}")

            # 전일 데이터 (전일대비 계산용)
            prev_close = None
            change = None
            change_rate = None

            if len(df) >= 2:
                prev = df.iloc[-2]
                prev_close = float(prev['종가'])
                change = float(latest['종가']) - prev_close
                if prev_close > 0:
                    change_rate = (change / prev_close) * 100
                debug_log.append(f"전일대비: {change}, 등락률: {change_rate:.2f}%")

            return {
                'open': float(latest['시가']),
                'high': float(latest['고가']),
                'low': float(latest['저가']),
                'close': float(latest['종가']),
                'volume': int(latest['거래량']),
                'prev_close': prev_close,
                'change': change,
                'change_rate': change_rate
            }
        except Exception as e:
            debug_log.append(f"OHLCV 조회 실패: {e}")
            return None

    def _get_market_cap_data(self, stock_code: str, date: str, debug_log: list) -> Dict:
        """시가총액, 상장주식수, 외국인비율 조회"""
        result = {'market_cap': None, 'shares': None, 'foreign_ratio': None}

        try:
            # 최근 5일 데이터 조회
            start_date = (datetime.strptime(date, "%Y%m%d") - timedelta(days=10)).strftime("%Y%m%d")
            df = stock.get_market_cap(start_date, date, stock_code)

            if not df.empty:
                latest = df.iloc[-1]
                result['market_cap'] = int(latest['시가총액'])
                result['shares'] = int(latest['상장주식수'])
                debug_log.append(f"시가총액: {result['market_cap']}, 상장주식수: {result['shares']}")

            # 외국인 보유비율 조회
            try:
                foreign_df = stock.get_exhaustion_rates_of_foreign_investment(start_date, date, stock_code)
                if not foreign_df.empty:
                    result['foreign_ratio'] = float(foreign_df.iloc[-1]['지분율'])
                    debug_log.append(f"외국인 지분율: {result['foreign_ratio']}%")
            except Exception:
                pass

        except Exception as e:
            debug_log.append(f"시가총액 조회 실패: {e}")

        return result

    def _get_fundamental_data(self, stock_code: str, date: str, debug_log: list) -> Dict:
        """PER, PBR, EPS, BPS, 배당수익률 조회"""
        result = {'per': None, 'pbr': None, 'eps': None, 'bps': None, 'div_yield': None}

        try:
            # 최근 5일 데이터 조회
            start_date = (datetime.strptime(date, "%Y%m%d") - timedelta(days=10)).strftime("%Y%m%d")
            df = stock.get_market_fundamental(start_date, date, stock_code)

            if not df.empty:
                latest = df.iloc[-1]
                result['bps'] = float(latest['BPS']) if latest['BPS'] > 0 else None
                result['per'] = float(latest['PER']) if latest['PER'] > 0 else None
                result['pbr'] = float(latest['PBR']) if latest['PBR'] > 0 else None
                result['eps'] = float(latest['EPS']) if latest['EPS'] > 0 else None
                result['div_yield'] = float(latest['DIV']) if latest['DIV'] > 0 else None
                debug_log.append(f"PER: {result['per']}, PBR: {result['pbr']}, EPS: {result['eps']}")

        except Exception as e:
            debug_log.append(f"펀더멘털 조회 실패: {e}")

        return result

    def _get_52week_high_low(self, stock_code: str, debug_log: list) -> Dict:
        """52주 최고/최저 계산"""
        result = {'high': None, 'low': None}

        try:
            end_date = self._get_latest_business_date()
            start_date = self._get_52week_ago_date()

            df = stock.get_market_ohlcv(start_date, end_date, stock_code)

            if not df.empty:
                result['high'] = float(df['고가'].max())
                result['low'] = float(df['저가'].min())
                debug_log.append(f"52주 최고: {result['high']}, 52주 최저: {result['low']}")

        except Exception as e:
            debug_log.append(f"52주 정보 조회 실패: {e}")

        return result

    def get_year_end_fundamental(self, stock_code: str, year: int, debug_log: list = None) -> Dict:
        """연말(12월 31일) 기준 펀더멘털 데이터 조회

        Args:
            stock_code: 종목코드
            year: 조회년도
            debug_log: 디버그 로그 리스트

        Returns:
            {
                'per': float or None,
                'pbr': float or None,
                'eps': float or None,
                'bps': float or None,
                'div_yield': float or None,
                'data_year': int or None,  # 실제 데이터가 있는 년도
                'data_date': str or None   # 실제 데이터 날짜 (YYYYMMDD)
            }
        """
        if debug_log is None:
            debug_log = []

        result = {
            'per': None, 'pbr': None, 'eps': None, 'bps': None,
            'div_yield': None, 'data_year': None, 'data_date': None
        }

        if not stock_code or stock_code == 'N/A':
            return result

        # 최대 3년까지 fallback (요청년도, 요청년도-1, 요청년도-2)
        for fallback_year in range(year, year - 3, -1):
            try:
                # 12월 마지막 영업일 데이터 조회 (12월 20일 ~ 12월 31일 범위)
                start_date = f"{fallback_year}1220"
                end_date = f"{fallback_year}1231"

                debug_log.append(f"연말 펀더멘털 조회: {fallback_year}년 ({start_date}~{end_date})")

                df = stock.get_market_fundamental(start_date, end_date, stock_code)

                if not df.empty:
                    # 가장 마지막 날짜 데이터 사용 (12월 마지막 영업일)
                    latest = df.iloc[-1]
                    latest_date = df.index[-1].strftime("%Y%m%d")

                    result['bps'] = float(latest['BPS']) if latest['BPS'] > 0 else None
                    result['per'] = float(latest['PER']) if latest['PER'] > 0 else None
                    result['pbr'] = float(latest['PBR']) if latest['PBR'] > 0 else None
                    result['eps'] = float(latest['EPS']) if latest['EPS'] > 0 else None
                    result['div_yield'] = float(latest['DIV']) if latest['DIV'] > 0 else None
                    result['data_year'] = fallback_year
                    result['data_date'] = latest_date

                    debug_log.append(f"연말 데이터 조회 성공: {fallback_year}년 ({latest_date})")
                    debug_log.append(f"  PER: {result['per']}, PBR: {result['pbr']}, EPS: {result['eps']}")
                    return result
                else:
                    debug_log.append(f"{fallback_year}년 연말 데이터 없음, 이전 년도 시도")

            except Exception as e:
                debug_log.append(f"{fallback_year}년 연말 조회 실패: {e}")
                continue

        debug_log.append("연말 펀더멘털 데이터를 찾을 수 없음")
        return result

    def _empty_result(self, message: str, debug_log: list) -> Dict:
        """빈 결과 반환"""
        return {
            'status': 'no_data',
            'price': None,
            'change': None,
            'change_rate': None,
            'volume': None,
            'market_cap': None,
            'high_52week': None,
            'low_52week': None,
            'open_price': None,
            'high_price': None,
            'low_price': None,
            'prev_close': None,
            'shares': None,
            'per': None,
            'pbr': None,
            'eps': None,
            'bps': None,
            'div_yield': None,
            'foreign_ratio': None,
            'data_date': None,
            'message': message,
            'debug': debug_log
        }
