def format_number(value) -> str:
    """숫자 포맷팅 (쉼표 추가)"""
    try:
        return f'{int(value):,}'
    except:
        return str(value) if value else '0'


def safe_float(value) -> float:
    """안전한 float 변환"""
    try:
        if isinstance(value, str):
            value = value.replace(',', '')
        return float(value) if value else 0.0
    except:
        return 0.0


def safe_int(value) -> int:
    """안전한 int 변환"""
    try:
        if isinstance(value, str):
            value = value.replace(',', '')
        return int(float(value)) if value else 0
    except:
        return 0
