import streamlit as st
from pathlib import Path
from PIL import Image
import os

# icon_path 먼저 정의
icon_path = Path(__file__).parent.parent.parent / "static" / "fine_icon.ico"

# 헬퍼 함수: 유효한 API 키인지 확인
def is_valid_api_key(key):
    """유효한 API 키인지 확인 (빈 값, None, placeholder 제외)"""
    if not key:
        return False
    # placeholder 문자열 필터링
    invalid_values = [
        'your_api_key_here',
        'your_dart_api_key_here',
        'your_gemini_api_key_here',
        'your_openai_api_key_here',
        'your_claude_api_key_here',
        'your_upstage_api_key_here',
        'none',
        'null',
        ''
    ]
    return key.lower() not in invalid_values and len(key) > 10

# 세션 상태 초기화 (.env에서 기본값 로드)
if 'dart_api_key' not in st.session_state:
    env_dart_key = os.getenv('DART_API_KEY', '')
    st.session_state.dart_api_key = env_dart_key if is_valid_api_key(env_dart_key) else ''

if 'llm_api_keys' not in st.session_state:
    st.session_state.llm_api_keys = {}
    for provider_id, env_var in [
        ('gemini', 'GEMINI_API_KEY'),
        ('openai', 'OPENAI_API_KEY'),
        ('claude', 'CLAUDE_API_KEY'),
        ('upstage', 'UPSTAGE_API_KEY')
    ]:
        env_key = os.getenv(env_var, '')
        st.session_state.llm_api_keys[provider_id] = env_key if is_valid_api_key(env_key) else ''
if 'selected_companies' not in st.session_state:
    st.session_state.selected_companies = []
if 'financial_results' not in st.session_state:
    st.session_state.financial_results = {}

# 여백 축소 CSS 적용
st.markdown("""
<style>
    /* 블록 요소들 사이 간격 축소 */
    .stMarkdown, .stDataFrame, .stMetric {
        margin-bottom: 0.3rem !important;
    }

    /* 구분선 마진 축소 */
    hr {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }

    /* expander 내부 패딩 축소 */
    .streamlit-expanderContent {
        padding-top: 0.3rem !important;
        padding-bottom: 0.3rem !important;
    }

    /* 컬럼 간격 축소 */
    [data-testid="column"] {
        padding: 0 0.3rem !important;
    }

    /* 서브헤더 마진 축소 */
    h2, h3 {
        margin-top: 0.5rem !important;
        margin-bottom: 0.3rem !important;
    }

    /* caption 마진 축소 */
    .stCaption {
        margin-top: 0.1rem !important;
        margin-bottom: 0.1rem !important;
    }

    /* info/warning/error 박스 마진 축소 */
    .stAlert {
        padding: 0.5rem !important;
        margin-bottom: 0.3rem !important;
    }

    /* 버튼 그룹 간격 */
    .stButton {
        margin-top: 0.2rem !important;
        margin-bottom: 0.2rem !important;
    }

    /* 텍스트 입력 필드 마진 */
    .stTextInput {
        margin-bottom: 0.3rem !important;
    }
</style>
""", unsafe_allow_html=True)

# 로고 및 헤더
try:
    logo_path = Path(__file__).parent.parent.parent / "static" / "fine.png"
    if logo_path.exists():
        col1, col2, col3 = st.columns([1, 6, 1])
        with col1:
            logo = Image.open(logo_path)
            st.image(logo, width=100)
        with col2:
            st.markdown("""
            <div style="padding-top: 20px;">
                <h1 style="margin: 0; color: #1a1a1a;">DART 재무정보 분석 시스템</h1>
                <p style="color: #666; margin: 5px 0 0 0;">상장·비상장 회사 재무정보 비교 분석 플랫폼</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.title("DART 재무정보 분석 시스템")
        st.caption("상장·비상장 회사 재무정보 비교 분석 플랫폼")
except:
    st.title("DART 재무정보 분석 시스템")
    st.caption("상장·비상장 회사 재무정보 비교 분석 플랫폼")

st.divider()

# 소개
col1, col2 = st.columns([2, 1])

with col1:
    with st.expander("### 시스템 개요", expanded=False):
        st.markdown("""
        DART(Data Analysis, Retrieval and Transfer System)에 공시된 기업 재무정보를  
        조회하고 AI를 활용하여 자동으로 분석 리포트를 생성하는 시스템입니다.
        """)
        
        st.markdown("**주요 기능**")
        
        with st.container():
            st.markdown("""
            **1. 회사 검색 및 선택**  
            DART 등록 기업 검색 (상장/비상장), 최대 3개 회사 비교 가능
            
            **2. 재무제표 조회**  
            3개년 재무제표 조회, 주요 재무비율 자동 계산
            
            **3. AI 재무 브리핑**  
            4가지 LLM(Gemini, GPT, Claude, Solar)을 활용한 재무 분석 리포트 자동 생성
            """)

with col2:
    with st.expander("### 사용 가이드", expanded=False):
        st.info("""
        **STEP 1**  
        API 키 확인/설정 (아래)
        
        **STEP 2**  
        좌측 메뉴에서 '재무 분석' 선택
        
        **STEP 3**  
        회사 검색 및 선택
        
        **STEP 4**  
        재무 정보 조회
        
        **STEP 5**  
        AI 브리핑 생성 (선택)
        """)

st.divider()

# API 키 설정
st.markdown("### API 키 설정")
st.caption("환경 변수(.env)에서 자동으로 로드되며, 필요시 여기서 변경할 수 있습니다")

# DART API 키
with st.expander("**DART API 키 (필수)**", expanded=not bool(st.session_state.dart_api_key)):
    if st.session_state.dart_api_key:
        st.success("✓ 환경 변수에서 로드됨")
    else:
        st.warning("환경 변수에 설정되지 않음")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        dart_key = st.text_input(
            "DART API 키",
            value=st.session_state.dart_api_key or "",
            type="password",
            placeholder="DART API 키를 입력하세요",
            label_visibility="collapsed",
            help="환경 변수에 설정된 키를 사용하거나, 새로운 키를 입력하세요"
        )
    with col2:
        if st.button("저장", use_container_width=True, type="primary", key="save_dart"):
            if dart_key:
                st.session_state.dart_api_key = dart_key
                st.success("저장 완료")
                st.rerun()
            else:
                st.error("API 키를 입력하세요")
    
    st.caption("[API 키 발급하기 →](https://opendart.fss.or.kr/)")

# LLM API 키
with st.expander("**LLM API 키 (선택)**", expanded=False):
    st.caption("AI 브리핑 기능 사용 시 필요합니다 (최소 1개)")
    
    # 환경 변수에서 로드된 키 개수 표시
    env_loaded = sum(1 for key in st.session_state.llm_api_keys.values() if key and key != '')
    if env_loaded > 0:
        st.success(f"✓ 환경 변수에서 {env_loaded}개 키 로드됨")
    
    llm_providers = {
        'gemini': ('Google Gemini', 'https://aistudio.google.com/app/apikeys'),
        'openai': ('OpenAI GPT', 'https://platform.openai.com/api-keys'),
        'claude': ('Anthropic Claude', 'https://console.anthropic.com/'),
        'upstage': ('Upstage Solar', 'https://console.upstage.ai/')
    }
    
    for provider_id, (provider_name, url) in llm_providers.items():
        col1, col2, col3 = st.columns([2.5, 0.5, 0.5])
        
        with col1:
            current_key = st.session_state.llm_api_keys.get(provider_id, '')
            key = st.text_input(
                provider_name,
                value=current_key,
                type="password",
                placeholder=f"{provider_name} API 키" + (" (환경 변수 로드됨)" if current_key else ""),
                key=f"llm_{provider_id}",
                help="환경 변수에 설정된 키를 사용하거나, 새로운 키를 입력하세요"
            )
            # 값이 변경되면 세션 상태 업데이트
            if key != current_key:
                st.session_state.llm_api_keys[provider_id] = key
        
        with col2:
            if st.session_state.llm_api_keys.get(provider_id):
                st.success("✓")
            else:
                st.markdown(f"[발급]({url})")
        
        with col3:
            # 개별 초기화 버튼
            if st.session_state.llm_api_keys.get(provider_id):
                if st.button("🗑️", key=f"clear_{provider_id}", help="초기화"):
                    st.session_state.llm_api_keys[provider_id] = ''
                    st.rerun()

# 설정 상태
st.divider()
st.markdown("### 설정 상태")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**DART API**")
    if st.session_state.dart_api_key:
        st.success("✓ 설정 완료")
        # 키의 일부만 표시 (보안)
        masked_key = st.session_state.dart_api_key[:8] + "..." + st.session_state.dart_api_key[-4:]
        st.caption(f"현재 키: {masked_key}")
    else:
        st.warning("⚠ 미설정")
        st.caption("DART API 키를 설정하세요")

with col2:
    st.markdown("**LLM API**")
    active_llms = [name for name, key in st.session_state.llm_api_keys.items() if key]
    if active_llms:
        st.success(f"✓ {len(active_llms)}개 설정됨")
        for llm in active_llms:
            st.caption(f"• {llm_providers[llm][0]}")
    else:
        st.info("미설정 (AI 브리핑 사용 불가)")
        st.caption("최소 1개의 LLM API 키를 설정하세요")

# 재무 분석 페이지로 이동 버튼
st.divider()
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("📊 재무 분석으로 이동", use_container_width=True, type="primary"):
        st.switch_page("page_modules/01_analysis.py")
# 전체 초기화 버튼
st.divider()
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("🔄 모든 API 키 초기화", use_container_width=True, type="secondary"):
        # DART API 키 초기화
        env_dart_key = os.getenv('DART_API_KEY', '')
        st.session_state.dart_api_key = env_dart_key if is_valid_api_key(env_dart_key) else ''

        # LLM API 키 초기화
        st.session_state.llm_api_keys = {}
        for provider_id, env_var in [
            ('gemini', 'GEMINI_API_KEY'),
            ('openai', 'OPENAI_API_KEY'),
            ('claude', 'CLAUDE_API_KEY'),
            ('upstage', 'UPSTAGE_API_KEY')
        ]:
            env_key = os.getenv(env_var, '')
            st.session_state.llm_api_keys[provider_id] = env_key if is_valid_api_key(env_key) else ''

        st.success("환경 변수 값으로 초기화되었습니다")
        st.rerun()

# 푸터
st.divider()
st.caption("DART 재무정보 분석 시스템 v2.0 | Powered by FastAPI + Streamlit")