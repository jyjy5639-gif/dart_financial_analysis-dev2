from typing import Dict, List
from collections import Counter

class FinancialService:
    """Financial calculation service"""
    
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
    
    def prepare_data(self, data: List[dict]) -> List[dict]:
        """Financial data preprocessing"""
        for item in data:
            account_id = item.get('account_id', '')
            account_nm = item.get('account_nm', '')
            
            if account_id in self.ACCOUNT_ID_MAP:
                item['base_display_name'] = self.ACCOUNT_ID_MAP[account_id]
            elif '당기순이익' in account_nm:
                item['base_display_name'] = '당기순이익'
            else:
                item['base_display_name'] = account_nm
        
        # Handle duplicate account names
        counts = Counter(i['base_display_name'] for i in data)
        for item in data:
            base_name = item['base_display_name']
            if counts[base_name] > 1:
                item['display_name'] = base_name + ' (' + item.get('account_id', '') + ')'
            else:
                item['display_name'] = base_name
        
        return data
    
    def calculate_ratios(self, data: List[dict]) -> Dict[str, Dict[str, float]]:
        """Calculate financial ratios"""
        # Extract accounts by amount
        accounts = {}
        for item in data:
            base_name = item.get('base_display_name')
            accounts[base_name] = {
                'thstrm': self._safe_float(item.get('thstrm_amount')),
                'frmtrm': self._safe_float(item.get('frmtrm_amount')),
                'bfefrmtrm': self._safe_float(item.get('bfefrmtrm_amount'))
            }
        
        def calc_ratio(numerator: str, denominator: str, percentage: bool = True):
            """Ratio calculation helper"""
            result = {}
            for period in ['thstrm', 'frmtrm', 'bfefrmtrm']:
                num = accounts.get(numerator, {}).get(period, 0)
                den = accounts.get(denominator, {}).get(period, 1)
                
                if den != 0:
                    value = (num / den) * (100 if percentage else 1)
                    result[period] = value
                else:
                    result[period] = 0
            return result
        
        return {
            '영업이익률': calc_ratio('영업이익', '매출액'),
            '순이익률': calc_ratio('당기순이익', '매출액'),
            'ROE': calc_ratio('당기순이익', '자본총계'),
            'ROA': calc_ratio('당기순이익', '자산총계'),
            '부채비율': calc_ratio('부채총계', '자본총계'),
            '자기자본비율': calc_ratio('자본총계', '자산총계'),
        }
    
    def calculate_per_pbr(
        self,
        data: List[dict],
        stock_price: float,
        shares: float
    ) -> Dict:
        """Calculate PER/PBR"""
        if not stock_price or not shares:
            return {
                'PER': {'thstrm': 'N/A', 'frmtrm': 'N/A', 'bfefrmtrm': 'N/A'},
                'PBR': {'thstrm': 'N/A', 'frmtrm': 'N/A', 'bfefrmtrm': 'N/A'},
                'note': '주가 또는 주식수 정보 없음'
            }
        
        # Extract accounts
        accounts = {}
        for item in data:
            base_name = item.get('base_display_name')
            accounts[base_name] = {
                'thstrm': self._safe_float(item.get('thstrm_amount')),
                'frmtrm': self._safe_float(item.get('frmtrm_amount')),
                'bfefrmtrm': self._safe_float(item.get('bfefrmtrm_amount'))
            }
        
        per = {}
        pbr = {}
        
        for period in ['thstrm', 'frmtrm', 'bfefrmtrm']:
            # EPS = net profit / shares
            net_profit = accounts.get('당기순이익', {}).get(period, 0)
            eps = net_profit / shares if shares > 0 else 0
            
            # BPS = equity / shares
            equity = accounts.get('자본총계', {}).get(period, 0)
            bps = equity / shares if shares > 0 else 0
            
            # PER = stock price / EPS
            per[period] = '{:.2f}'.format(stock_price / eps) if eps > 0 else 'N/A'
            
            # PBR = stock price / BPS
            pbr[period] = '{:.2f}'.format(stock_price / bps) if bps > 0 else 'N/A'
        
        return {
            'PER': per,
            'PBR': pbr,
            'note': None
        }
    
    def prepare_comparison_data(
        self,
        companies_financial_data: Dict[str, List[dict]]
    ) -> Dict[str, Dict]:
        """
        Prepare financial data for multiple companies.
        
        Input format:
        {
            "00005930": [financial items...],
            "00066570": [financial items...]
        }
        
        Output format:
        {
            "00005930": {
                "prepared_data": [preprocessed items],
                "ratios": {financial ratios}
            },
            "00066570": {...}
        }
        """
        result = {}
        
        for corp_code, financial_data in companies_financial_data.items():
            # Preprocess data
            prepared = self.prepare_data(financial_data)
            
            # Calculate ratios
            ratios = self.calculate_ratios(prepared)
            
            result[corp_code] = {
                'prepared_data': prepared,
                'ratios': ratios
            }
        
        return result
    
    def format_comparison_by_year(
        self,
        companies_comparison_data: Dict[str, Dict],
        company_info: Dict[str, dict]
    ) -> Dict[str, List[dict]]:
        """
        Format multiple company data by year for side-by-side comparison.
        
        Input:
        companies_comparison_data = {
            "00005930": {
                "prepared_data": [...],
                "ratios": {...}
            },
            "00066570": {...}
        }
        
        company_info = {
            "00005930": {"corp_name": "삼성전자"},
            "00066570": {"corp_name": "LG전자"}
        }
        
        Output:
        {
            "2024": [
                {
                    "corp_code": "00005930",
                    "corp_name": "삼성전자",
                    "financial_data": [...],
                    "ratios": {...}
                },
                {
                    "corp_code": "00066570",
                    "corp_name": "LG전자",
                    "financial_data": [...],
                    "ratios": {...}
                }
            ],
            "2023": [...]
        }
        """
        
        # Extract all years from data
        all_years = set()
        
        for corp_code, comparison_data in companies_comparison_data.items():
            prepared_data = comparison_data['prepared_data']
            for item in prepared_data:
                # Extract year from thstrm_dt (e.g. "20240331" -> "2024")
                thstrm_dt = item.get('thstrm_dt', '')
                if thstrm_dt and len(thstrm_dt) >= 4:
                    year = thstrm_dt[:4]
                    all_years.add(year)
        
        # Group by year
        result = {}
        for year in sorted(all_years, reverse=True):
            result[year] = []
            
            for corp_code, comparison_data in companies_comparison_data.items():
                company_info_data = company_info.get(corp_code, {})
                
                result[year].append({
                    'corp_code': corp_code,
                    'corp_name': company_info_data.get('corp_name', corp_code),
                    'stock_code': company_info_data.get('stock_code', 'N/A'),
                    'financial_data': comparison_data['prepared_data'],
                    'ratios': comparison_data['ratios']
                })
        
        return result
    
    def get_account_values_by_year(
        self,
        financial_data: List[dict],
        account_name: str
    ) -> Dict[str, float]:
        """
        Extract 3-year data for a specific account.
        
        Input:
        account_name = "유동자산"
        
        Output:
        {
            "2024": 1234567890,
            "2023": 987654321,
            "2022": 876543210
        }
        """
        result = {}
        
        for item in financial_data:
            display_name = item.get('display_name') or item.get('base_display_name')
            
            if display_name == account_name:
                # thstrm (current period)
                thstrm_dt = item.get('thstrm_dt', '')
                if thstrm_dt and len(thstrm_dt) >= 4:
                    year = thstrm_dt[:4]
                    result[year] = self._safe_float(item.get('thstrm_amount'))
                
                # frmtrm (previous period)
                frmtrm_dt = item.get('frmtrm_dt', '')
                if frmtrm_dt and len(frmtrm_dt) >= 4:
                    year = frmtrm_dt[:4]
                    result[year] = self._safe_float(item.get('frmtrm_amount'))
                
                # bfefrmtrm (period before previous)
                bfefrmtrm_dt = item.get('bfefrmtrm_dt', '')
                if bfefrmtrm_dt and len(bfefrmtrm_dt) >= 4:
                    year = bfefrmtrm_dt[:4]
                    result[year] = self._safe_float(item.get('bfefrmtrm_amount'))
        
        return result
    
    @staticmethod
    def _safe_float(value) -> float:
        """Safe float conversion"""
        try:
            if value is None:
                return 0.0
            if isinstance(value, str):
                value = value.replace(',', '')
            return float(value)
        except:
            return 0.0
    
    @staticmethod
    def format_number(value) -> str:
        """Format number with commas"""
        try:
            return '{:,}'.format(int(value))
        except:
            return str(value) if value else '0'