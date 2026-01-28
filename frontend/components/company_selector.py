import streamlit as st
from typing import List, Dict

def render_company_selector(api_client, dart_api_key: str):
    """회사 검색 및 선택 UI"""
    
    st.header("🔍 회사 선택")
    
    # 선택된 회사 표시
    if st.session_state.selected_companies:
        st.subheader("✅ 선택된 회사")
        for i, company in enumerate(st.session_state.selected_companies):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"**{i+1}. {company['corp_name']}** ({company['corp_code']})")
            with col2:
                status = "상장" if company.get('stock_code') != 'N/A' else "비상장"
                st.caption(status)
            with col3:
                if st.button("❌ 삭제", key=f"del_{i}"):
                    st.session_state.selected_companies.pop(i)
                    st.rerun()
    
    # 검색
    st.divider()
    st.subheader("🔍 회사 검색")
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        keyword = st.text_input(
            "회사명 또는 종목코드",
            placeholder="예: 삼성전자",
            label_visibility="collapsed"
        )
    
    with col2:
        search_btn = st.button("🔍 검색", use_container_width=True)
    
    # 검색 실행
    if search_btn and keyword:
        with st.spinner("검색 중..."):
            try:
                results = api_client.search_companies(keyword, dart_api_key)
                st.session_state.search_results = results
            except Exception as e:
                st.error(f"검색 실패: {str(e)}")
                st.session_state.search_results = []
    
    # 검색 결과 표시
    if 'search_results' in st.session_state and st.session_state.search_results:
        results = st.session_state.search_results
        st.success(f"✅ {len(results)}개의 결과를 찾았습니다.")
        
        for idx, company in enumerate(results[:50]):  # 최대 50개
            col1, col2, col3, col4 = st.columns([2.5, 1, 1, 1.2])
            
            is_listed = company.get('stock_code') != 'N/A'
            
            with col1:
                prefix = "⭐" if is_listed else "  "
                st.write(f"{prefix} {company['corp_name']}")
            with col2:
                st.write(f"`{company['corp_code']}`")
            with col3:
                st.write("상장" if is_listed else "비상장")
            with col4:
                # 이미 선택되었는지 확인
                already_selected = any(
                    c['corp_code'] == company['corp_code']
                    for c in st.session_state.selected_companies
                )
                
                if already_selected:
                    st.write("✅ 선택됨")
                elif len(st.session_state.selected_companies) < 3:
                    if st.button("선택", key=f"select_{idx}_{company['corp_code']}"):
                        st.session_state.selected_companies.append(company)
                        st.rerun()
                else:
                    st.caption("(최대 3개)")