from abc import ABC, abstractmethod
from typing import Dict, Optional


class BaseLLMProvider(ABC):
    """LLM 제공자 기본 클래스"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    @abstractmethod
    async def generate_briefing(
        self,
        corp_name: str,
        financial_data: Dict,
        style: str = "default"
    ) -> str:
        """재무 브리핑 생성
        
        Args:
            corp_name: 회사명
            financial_data: 재무 데이터
            style: 브리핑 스타일 (default, executive, detailed)
            
        Returns:
            생성된 브리핑 텍스트
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """API 사용 가능 여부 확인"""
        pass
    
    def _build_prompt(
        self,
        corp_name: str,
        financial_data: Dict,
        style: str
    ) -> str:
        """프롬프트 생성 (공통)"""
        
        # 복수 회사 비교 분석인지 확인
        items = financial_data.get('items', [])
        
        # items가 리스트이고 각 요소가 dict로 corp_name을 가지고 있으면 복수 회사
        if isinstance(items, list) and items and isinstance(items[0], dict) and 'corp_name' in items[0]:
            # 복수 회사 비교
            return self._build_comparison_prompt(items, style)
        else:
            # 단일 회사 분석
            return self._build_single_prompt(corp_name, financial_data, style)
    
    def _build_single_prompt(
        self,
        corp_name: str,
        financial_data: Dict,
        style: str
    ) -> str:
        """단일 회사 프롬프트"""
        
        # 데이터를 문자열로 변환
        data_text = "=== 재무 데이터 ===\n\n"
        
        summary_accts = ['매출액', '영업이익', '당기순이익', '자산총계', '부채총계', '자본총계']
        
        data_text += "【주요 계정】\n"
        for acct in summary_accts:
            for item in financial_data.get('items', []):
                if item.get('base_display_name') == acct:
                    thstrm = self._safe_convert(item.get('thstrm_amount'))
                    frmtrm = self._safe_convert(item.get('frmtrm_amount'))
                    bfefrmtrm = self._safe_convert(item.get('bfefrmtrm_amount'))
                    
                    data_text += f"{acct}: 당기 {thstrm} / 전기 {frmtrm} / 전전기 {bfefrmtrm}\n"
                    break
        
        # 스타일별 프롬프트
        prompts = {
            "executive": self._get_executive_prompt(corp_name, data_text),
            "detailed": self._get_detailed_prompt(corp_name, data_text),
            "default": self._get_default_prompt(corp_name, data_text)
        }
        
        return prompts.get(style, prompts["default"])
    
    def _build_comparison_prompt(
        self,
        companies_data: list,
        style: str
    ) -> str:
        """복수 회사 비교 프롬프트"""
        
        company_names = [comp['corp_name'] for comp in companies_data]
        
        # 각 회사의 주요 지표 추출
        data_text = "=== 회사별 재무 데이터 ===\n\n"
        
        summary_accts = ['매출액', '영업이익', '당기순이익', '자산총계', '부채총계', '자본총계']
        
        for company in companies_data:
            corp_name = company['corp_name']
            items = company.get('items', [])
            
            data_text += f"\n【{corp_name}】\n"
            
            for acct in summary_accts:
                for item in items:
                    if item.get('base_display_name') == acct:
                        thstrm = self._safe_convert(item.get('thstrm_amount'))
                        data_text += f"  {acct}: {thstrm}\n"
                        break
            
            # 비율 데이터 추가
            ratios = company.get('ratios', {})
            if ratios:
                data_text += "  \n  [주요 비율]\n"
                for ratio_name, values in ratios.items():
                    if isinstance(values, dict) and 'thstrm' in values:
                        data_text += f"  {ratio_name}: {values['thstrm']:.2f}%\n"
        
        # 스타일별 프롬프트
        if style == "executive":
            return self._get_comparison_executive_prompt(company_names, data_text)
        elif style == "detailed":
            return self._get_comparison_detailed_prompt(company_names, data_text)
        else:
            return self._get_comparison_default_prompt(company_names, data_text)
    
    def _safe_convert(self, val) -> str:
        """안전한 숫자 변환"""
        if val is None:
            return 'N/A'
        try:
            if isinstance(val, str):
                val = val.replace(',', '')
            return f"{int(float(val)):,}"
        except:
            return 'N/A'
    
    def _get_default_prompt(self, corp_name: str, data_text: str) -> str:
        """기본 프롬프트 (이모지 제거)"""
        return f"""당신은 재무 분석 전문가입니다. 반드시 한글로만 답변하세요.

{corp_name}의 3년 재무 데이터를 분석하여 상세한 브리핑을 작성해주세요.

{data_text}

요구사항:
1. 최소 600단어 이상 작성
2. 한글로만 작성
3. 다음 구조로 상세하게 작성:
   - **1. 3년 매출/수익 트렌드 분석**
   - **2. 수익성 분석**
   - **3. 재무 건전성 평가**
   - **4. 주의할 점**
   - **5. 핵심 포인트**
   - **6. 종합 평가**

각 섹션마다 구체적인 수치와 상세한 설명을 포함하여 작성해주세요."""
    
    def _get_executive_prompt(self, corp_name: str, data_text: str) -> str:
        """경영진 보고 프롬프트 (이모지 제거)"""
        return f"""당신은 투자 컨설턴트입니다. 반드시 한글로만 답변하세요.

{corp_name}의 3년 재무 데이터를 심층 분석하고 경영진 보고서 형식의 브리핑을 작성해주세요.

{data_text}

요구사항:
1. 최소 500단어 이상 작성
2. 한글로만 작성
3. 다음 구조로 상세하게 작성:
   - **주요 재무 지표 분석**
   - **수익성 변화 분석**
   - **재무 건전성 평가**
   - **긍정적 신호**
   - **리스크 요소**
   - **투자 의견**

각 항목마다 구체적인 수치와 설명을 포함하여 상세하게 작성해주세요."""
    
    def _get_detailed_prompt(self, corp_name: str, data_text: str) -> str:
        """상세 분석 프롬프트 (이모지 제거)"""
        return f"""당신은 재무 분석 전문가입니다. 반드시 한글로만 답변하세요.

{corp_name}의 3년 재무 데이터를 심층적으로 분석하여 전문가급 브리핑을 작성해주세요.

{data_text}

요구사항:
1. 최소 800단어 이상 작성
2. 한글로만 작성
3. 다음 구조로 매우 상세하게 작성:
   - **1. 매출액 분석**
   - **2. 수익성 분석**
   - **3. 재무 구조 분석**
   - **4. 효율성 지표**
   - **5. 리스크 평가**
   - **6. 종합 평가 (SWOT)**
   - **7. 투자 결론**

각 항목마다 구체적인 수치를 제시하고 심층적으로 분석해주세요."""
    
    def _get_comparison_default_prompt(self, company_names: list, data_text: str) -> str:
        """복수 회사 비교 - 기본 프롬프트 (이모지 제거)"""
        companies_str = ', '.join(company_names)
        return f"""당신은 재무 분석 전문가입니다. 반드시 한글로만 답변하세요.

{companies_str} 회사들의 재무 데이터를 비교 분석하여 상세한 브리핑을 작성해주세요.

{data_text}

요구사항:
1. 최소 700단어 이상 작성
2. 한글로만 작성
3. 다음 구조로 상세하게 작성:
   - **1. 회사 개요 및 규모 비교**
   - **2. 매출 및 수익성 비교**
   - **3. 수익률 분석 (영업이익률, 순이익률, ROE)**
   - **4. 재무 건전성 비교 (부채비율, 자기자본비율)**
   - **5. 각 회사의 강점과 약점**
   - **6. 투자 관점에서의 비교 평가**

각 섹션마다 구체적인 수치를 비교하고, 각 회사를 A/B 같은 기호가 아닌 실제 회사명으로 언급하며 상세하게 분석해주세요.
"""
    
    def _get_comparison_executive_prompt(self, company_names: list, data_text: str) -> str:
        """복수 회사 비교 - 경영진 보고 프롬프트 (이모지 제거)"""
        companies_str = ', '.join(company_names)
        return f"""당신은 투자 컨설턴트입니다. 반드시 한글로만 답변하세요.

{companies_str} 회사들의 재무 데이터를 비교 분석하고 경영진 보고서 형식의 브리핑을 작성해주세요.

{data_text}

요구사항:
1. 최소 600단어 이상 작성
2. 한글로만 작성
3. 다음 구조로 상세하게 작성:
   - **주요 재무 지표 비교**
   - **수익성 분석**
   - **재무 안정성 평가**
   - **각 회사의 경쟁력**
   - **리스크 요인 비교**
   - **투자 권고사항**

각 회사를 실제 회사명으로 명확히 언급하고, 구체적인 수치를 바탕으로 비교하며 상세하게 설명해주세요.
"""
    
    def _get_comparison_detailed_prompt(self, company_names: list, data_text: str) -> str:
        """복수 회사 비교 - 상세 분석 프롬프트 (이모지 제거)"""
        companies_str = ', '.join(company_names)
        return f"""당신은 재무 분석 전문가입니다. 반드시 한글로만 답변하세요.

{companies_str} 회사들의 재무 데이터를 심층적으로 비교 분석하여 전문가급 브리핑을 작성해주세요.

{data_text}

요구사항:
1. 최소 900단어 이상 작성
2. 한글로만 작성
3. 다음 구조로 매우 상세하게 작성:
   - **1. 기업 규모 및 산업 내 위치 비교**
   - **2. 매출 및 수익 구조 상세 분석**
   - **3. 수익성 지표 심층 비교 (영업이익률, 순이익률, ROE, ROA)**
   - **4. 재무 구조 분석 (자산, 부채, 자본 구조)**
   - **5. 재무 건전성 및 리스크 평가**
   - **6. 각 회사의 SWOT 분석**
   - **7. 종합 평가 및 투자 결론**

각 회사의 이름을 명확히 사용하고, 모든 주요 지표를 구체적으로 비교하며 심층적으로 분석해주세요."""
