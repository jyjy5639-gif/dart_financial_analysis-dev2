import streamlit as st

def render_briefing_viewer(financial_results: dict, api_client, llm_api_keys: dict):
    """AI 브리핑 뷰어"""
    
    st.header("🤖 AI 재무 브리핑")
    
    if not llm_api_keys:
        st.warning("⚠️ 사이드바에서 LLM API 키를 입력하세요")
        return
    
    # 단일 회사만 지원
    if len(financial_results) > 1:
        st.info("💡 브리핑은 단일 회사 조회 시 제공됩니다")
        return
    
    corp_data = list(financial_results.values())[0]
    
    # LLM 제공자 선택
    available_providers = [
        (key, name) for key, name in [
            ('gemini', '🔷 Google Gemini'),
            ('openai', '🟢 OpenAI GPT'),
            ('claude', '🟣 Anthropic Claude'),
            ('upstage', '🟠 Upstage Solar')
        ] if key in llm_api_keys and llm_api_keys[key]
    ]
    
    if not available_providers:
        st.warning("⚠️ 사용 가능한 LLM API 키가 없습니다")
        return
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        provider = st.selectbox(
            "LLM 제공자",
            options=[p[0] for p in available_providers],
            format_func=lambda x: dict(available_providers)[x]
        )
    
    with col2:
        style = st.selectbox(
            "분석 스타일",
            options=['default', 'executive', 'detailed'],
            format_func=lambda x: {
                'default': '📋 표준 (600단어)',
                'executive': '👔 경영진 보고 (500단어)',
                'detailed': '🔬 상세 분석 (800단어)'
            }[x]
        )
    
    with col3:
        st.write("")
        generate_btn = st.button("🤖 생성", use_container_width=True)
    
    # 브리핑 생성
    cache_key = f"briefing_{corp_data['corp_code']}_{provider}_{style}"
    
    if generate_btn:
        with st.spinner(f"브리핑 생성 중... ({dict(available_providers)[provider]})"):
            try:
                result = api_client.generate_briefing(
                    corp_name=corp_data['corp_name'],
                    financial_data=corp_data['financial_data'],
                    provider=provider,
                    api_key=llm_api_keys[provider],
                    style=style
                )
                
                briefing_text = result.get('briefing', '')
                st.session_state[cache_key] = briefing_text
                
                st.markdown(briefing_text)
            
            except Exception as e:
                st.error(f"❌ 브리핑 생성 실패: {str(e)}")
                st.info("💡 API 키 또는 할당량을 확인하세요")
    
    # 이전 브리핑 표시
    elif cache_key in st.session_state:
        st.markdown(st.session_state[cache_key])