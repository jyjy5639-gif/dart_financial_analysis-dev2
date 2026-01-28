import streamlit as st
import pandas as pd
import io

def render_financial_tables(financial_results: dict, api_client, dart_api_key: str, bsns_year: str):
    """재무 테이블 렌더링"""
    
    if len(financial_results) == 1:
        # 단일 회사
        _render_single_company(financial_results, api_client, dart_api_key, bsns_year)
    else:
        # 복수 회사 비교
        _render_comparison(financial_results)

def _render_single_company(financial_results: dict, api_client, dart_api_key: str, bsns_year: str):
    """단일 회사 재무정보"""
    
    corp_data = list(financial_results.values())[0]
    
    st.write(f"**{corp_data['corp_name']}**")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 요약", "📈 비율", "📋 전체", "📰 공시"])
    
    with tab1:
        _render_summary(corp_data)
    
    with tab2:
        _render_ratios(corp_data, api_client, dart_api_key)
    
    with tab3:
        _render_all_accounts(corp_data)
    
    with tab4:
        _render_disclosures(corp_data, api_client, dart_api_key, bsns_year)

def _render_summary(corp_data: dict):
    """요약 재무정보"""
    summary_accounts = ['매출액', '영업이익', '당기순이익', '자산총계', '부채총계', '자본총계']
    
    summary_data = []
    for item in corp_data['financial_data']:
        if item.get('base_display_name') in summary_accounts:
            summary_data.append({
                '계정명': item['display_name'],
                '당기': _format_number(item.get('thstrm_amount')),
                '전기': _format_number(item.get('frmtrm_amount')),
                '전전기': _format_number(item.get('bfefrmtrm_amount'))
            })
    
    df = pd.DataFrame(summary_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

def _render_ratios(corp_data: dict, api_client, dart_api_key: str):
    """재무 비율"""
    st.write("**주요 재무비율**")
    
    ratio_data = []
    for name, values in corp_data['ratios'].items():
        ratio_data.append({
            '비율명': name,
            '당기': f"{values['thstrm']:.2f}%",
            '전기': f"{values['frmtrm']:.2f}%",
            '전전기': f"{values['bfefrmtrm']:.2f}%"
        })
    
    # 주가 정보 조회
    with st.spinner("📊 주가 정보 조회 중..."):
        try:
            stock_info = api_client.get_stock_info(
                corp_code=corp_data['corp_code'],
                stock_code=corp_data.get('stock_code', 'N/A'),
                corp_name=corp_data['corp_name'],
                api_key=dart_api_key
            )
            
            # 디버그 로그
            if stock_info.get('debug'):
                with st.expander("🔍 디버그 로그"):
                    for log in stock_info['debug']:
                        st.write(f"- {log}")
            
            # PER/PBR은 주식수 정보가 있어야 계산 가능
            if stock_info.get('price'):
                st.info(f"💰 현재 주가: {stock_info['price']:,.0f}원")
                if stock_info.get('message'):
                    st.caption(stock_info['message'])
            else:
                st.warning(stock_info.get('message', '주가 정보 없음'))
        
        except Exception as e:
            st.error(f"주가 조회 실패: {str(e)}")
    
    df = pd.DataFrame(ratio_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

def _render_all_accounts(corp_data: dict):
    """전체 계정 정보"""
    detail_data = []
    for item in corp_data['financial_data']:
        detail_data.append({
            '계정명': item['display_name'],
            '당기': _format_number(item.get('thstrm_amount')),
            '전기': _format_number(item.get('frmtrm_amount')),
            '전전기': _format_number(item.get('bfefrmtrm_amount'))
        })
    
    df = pd.DataFrame(detail_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

def _render_disclosures(corp_data: dict, api_client, dart_api_key: str, bsns_year: str):
    """공시 정보"""
    st.subheader("📰 공시 목록")
    
    try:
        result = api_client.get_disclosures(
            corp_code=corp_data['corp_code'],
            bsns_year=bsns_year,
            api_key=dart_api_key
        )
        
        disclosures = result.get('disclosures', [])
        
        if disclosures:
            st.info(f"총 {len(disclosures)}개 공시")
            
            for idx, d in enumerate(disclosures[:100]):  # 최대 100개
                col1, col2, col3 = st.columns([1, 2, 1.5])
                
                with col1:
                    st.write(d.get('rcept_dt'))
                with col2:
                    st.write(d.get('report_nm'))
                with col3:
                    rcept_no = d.get('rcept_no')
                    link = f"http://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
                    st.markdown(f"[{rcept_no}]({link})")
        else:
            st.warning("공시 정보가 없습니다")
    
    except Exception as e:
        st.error(f"공시 조회 실패: {str(e)}")

def _render_comparison(financial_results: dict):
    """복수 회사 비교"""
    st.subheader("📊 회사 비교")
    
    tab1, tab2 = st.tabs(["📊 요약 비교", "📈 비율 비교"])
    
    with tab1:
        summary_accounts = ['매출액', '영업이익', '당기순이익', '자산총계', '부채총계', '자본총계']
        
        comparison_data = {'계정명': summary_accounts}
        
        for corp_data in financial_results.values():
            corp_values = []
            for account in summary_accounts:
                value = next(
                    (item.get('thstrm_amount') for item in corp_data['financial_data']
                     if item.get('base_display_name') == account),
                    '0'
                )
                corp_values.append(_format_number(value))
            
            comparison_data[corp_data['corp_name']] = corp_values
        
        df = pd.DataFrame(comparison_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    with tab2:
        # 첫 번째 회사의 비율 이름 사용
        first_corp = list(financial_results.values())[0]
        ratio_names = list(first_corp['ratios'].keys())
        
        ratio_comparison = {'비율명': ratio_names}
        
        for corp_data in financial_results.values():
            ratio_values = [
                f"{corp_data['ratios'][name]['thstrm']:.2f}%"
                for name in ratio_names
            ]
            ratio_comparison[corp_data['corp_name']] = ratio_values
        
        df = pd.DataFrame(ratio_comparison)
        st.dataframe(df, use_container_width=True, hide_index=True)

def _format_number(value) -> str:
    """숫자 포맷팅"""
    try:
        if isinstance(value, str):
            value = value.replace(',', '')
        return f'{int(float(value)):,}'
    except:
        return str(value) if value else '0'