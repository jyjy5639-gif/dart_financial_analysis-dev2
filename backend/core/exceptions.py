class DARTAPIException(Exception):
    """DART API 관련 예외"""
    pass


class KRXDataException(Exception):
    """KRX 데이터 관련 예외"""
    pass


class StockInfoException(Exception):
    """주가 정보 조회 예외"""
    pass


class LLMException(Exception):
    """LLM 관련 예외"""
    pass


class CompanyNotFoundException(Exception):
    """회사를 찾을 수 없음"""
    pass


class FinancialDataNotFoundException(Exception):
    """재무 데이터를 찾을 수 없음"""
    pass
