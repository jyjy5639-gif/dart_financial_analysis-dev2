import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# frontend 폴더를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from api_client import APIClient
import base64
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import os

# ← 여기 추가: Backend URL 설정
BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "https://dart-financial-analysis-dev-backend.onrender.com"
)

if "backend_url" not in st.session_state:
    st.session_state.backend_url = BACKEND_URL



# Helper functions
def _format_number(value) -> str:
    """Number formatting"""
    try:
        if isinstance(value, str):
            value = value.replace(',', '')
        return '{:,}'.format(int(float(value)))
    except:
        return str(value) if value else '0'

def get_download_link(file_bytes, filename, file_type="excel"):
    """Generate download link"""
    b64 = base64.b64encode(file_bytes).decode()
    
    if file_type == "excel":
        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        icon = "📥"
    elif file_type == "pdf":
        mime_type = "application/pdf"
        icon = "📄"
    else:
        mime_type = "application/octet-stream"
        icon = "📎"
    
    return '<a href="data:{};base64,{}" download="{}">{} {} 다운로드</a>'.format(mime_type, b64, filename, icon, filename)

def is_valid_api_key(key):
    """Check if API key is valid"""
    if not key:
        return False
    invalid_values = [
        'your_api_key_here', 'your_dart_api_key_here', 'your_gemini_api_key_here',
        'your_openai_api_key_here', 'your_claude_api_key_here', 'your_upstage_api_key_here',
        'none', 'null', ''
    ]
    return key.lower() not in invalid_values and len(key) > 10

def clean_briefing_text(text: str) -> str:
    """Clean AI briefing text"""
    if not text:
        return ""
    
    import re
    
    cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)
    cleaned = cleaned.strip()
    
    return cleaned

def create_trend_chart(financial_data, accounts=['매출액', '영업이익', '당기순이익']):
    """Create trend chart for main financial indicators"""
    chart_data = {}
    years = []
    
    for account in accounts:
        for item in financial_data:
            if item.get('base_display_name') == account:
                values = []
                item_years = []
                
                year_data = [
                    (item.get('bfefrmtrm_amount'), item.get('bfefrmtrm_dt')),
                    (item.get('frmtrm_amount'), item.get('frmtrm_dt')),
                    (item.get('thstrm_amount'), item.get('thstrm_dt'))
                ]
                
                for amount, date in year_data:
                    if amount and date:
                        try:
                            year = date[:4]
                            value = float(str(amount).replace(',', ''))
                            values.append(value / 100000000)
                            item_years.append(year)
                        except:
                            continue
                
                if values:
                    chart_data[account] = values
                    if not years:
                        years = item_years
                break
    
    if not chart_data:
        return None
    
    fig = go.Figure()
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    for i, account in enumerate(accounts):
        if account in chart_data:
            fig.add_trace(go.Scatter(
                x=years,
                y=chart_data[account],
                mode='lines+markers',
                name=account,
                line=dict(color=colors[i % len(colors)], width=3),
                marker=dict(size=8)
            ))
    
    fig.update_layout(
        title={
            'text': '주요 재무지표 추이 (단위: 억원)',
            'x': 0.5,
            'font': {'size': 16}
        },
        xaxis_title='연도',
        yaxis_title='금액 (억원)',
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        template="plotly_white",
        height=400
    )
    
    return fig

def create_ratio_chart(ratios, financial_data):
    """Create financial ratio chart"""
    key_ratios = ['영업이익률', '순이익률', 'ROE', 'ROA']
    available_ratios = {k: v for k, v in ratios.items() if k in key_ratios and v}
    
    if not available_ratios:
        return None
    
    year_labels = {'bfefrmtrm': '전전기', 'frmtrm': '전기', 'thstrm': '당기'}
    for item in financial_data:
        bfefrmtrm_dt = item.get('bfefrmtrm_dt', '')
        frmtrm_dt = item.get('frmtrm_dt', '')
        thstrm_dt = item.get('thstrm_dt', '')
        
        if bfefrmtrm_dt and len(bfefrmtrm_dt) >= 4:
            year_labels['bfefrmtrm'] = 'Year Before Last ({})'.format(bfefrmtrm_dt[:4])
        if frmtrm_dt and len(frmtrm_dt) >= 4:
            year_labels['frmtrm'] = 'Previous Year ({})'.format(frmtrm_dt[:4])
        if thstrm_dt and len(thstrm_dt) >= 4:
            year_labels['thstrm'] = 'Current Year ({})'.format(thstrm_dt[:4])
        
        if all('(' in year_labels[k] for k in ['bfefrmtrm', 'frmtrm', 'thstrm']):
            break
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=list(available_ratios.keys()),
        specs=[[{"type": "bar"}, {"type": "bar"}], 
               [{"type": "bar"}, {"type": "bar"}]]
    )
    
    positions = [(1,1), (1,2), (2,1), (2,2)]
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    
    for i, (ratio_name, values) in enumerate(available_ratios.items()):
        if i >= 4:
            break
        
        row, col = positions[i]
        years = [
            year_labels.get('bfefrmtrm', '전전기'),
            year_labels.get('frmtrm', '전기'),
            year_labels.get('thstrm', '당기')
        ]
        ratio_values = [
            values.get('bfefrmtrm', 0), 
            values.get('frmtrm', 0), 
            values.get('thstrm', 0)
        ]
        
        fig.add_trace(go.Bar(
            x=years,
            y=ratio_values,
            name=ratio_name,
            showlegend=False,
            marker_color=colors[i % len(colors)]
        ), row=row, col=col)
        
        fig.update_yaxes(title_text="(%)", row=row, col=col)
    
    fig.update_layout(
        title={
            'text': '주요 재무비율 비교',
            'x': 0.5,
            'font': {'size': 16}
        },
        height=500,
        template="plotly_white"
    )
    
    return fig

def create_comparison_chart(companies_data):
    """Create multiple company comparison chart"""
    accounts = ['매출액', '영업이익', '당기순이익', '자산총계']
    comparison_data = {}
    company_names = []
    
    for corp_code, corp_data in companies_data.items():
        company_names.append(corp_data['corp_name'])
        company_values = []
        
        for account in accounts:
            value = 0
            for item in corp_data['financial_data']:
                if item.get('base_display_name') == account:
                    try:
                        value = float(str(item.get('thstrm_amount', 0)).replace(',', '')) / 100000000
                    except:
                        value = 0
                    break
            company_values.append(value)
        
        comparison_data[corp_data['corp_name']] = company_values
    
    if not comparison_data:
        return None
    
    fig = go.Figure()
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    for i, company in enumerate(company_names):
        fig.add_trace(go.Bar(
            name=company,
            x=accounts,
            y=comparison_data[company],
            marker_color=colors[i % len(colors)]
        ))
    
    fig.update_layout(
        title={
            'text': '회사별 주요 재무지표 비교 (단위: 억원)',
            'x': 0.5,
            'font': {'size': 16}
        },
        xaxis_title='재무 지표',
        yaxis_title='금액 (억원)',
        barmode='group',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        template="plotly_white",
        height=450
    )
    
    return fig

def _render_disclosure_list(disclosures, key_prefix):
    """Render disclosure list"""
    for idx, disclosure in enumerate(disclosures[:20]):
        col1, col2, col3 = st.columns([2, 3, 1])

        with col1:
            rcept_dt = disclosure.get('rcept_dt', '')
            if rcept_dt and len(rcept_dt) == 8:
                formatted_date = "{}-{}-{}".format(rcept_dt[:4], rcept_dt[4:6], rcept_dt[6:8])
                st.write(f"**{formatted_date}**")
            else:
                st.write(f"**{rcept_dt}**")

        with col2:
            report_nm = disclosure.get('report_nm', '보고서명 없음')
            st.write(report_nm)

        with col3:
            rcept_no = disclosure.get('rcept_no', '')
            if rcept_no:
                dart_url = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo={}".format(rcept_no)
                st.markdown("[🔗 보기]({})".format(dart_url))

        if idx < len(disclosures) - 1:
            st.divider()

def create_ratio_comparison_chart(companies_data):
    """Create financial ratio comparison chart for multiple companies"""
    key_ratios = ['영업이익률', '순이익률', 'ROE', 'ROA']
    comparison_data = {}
    company_names = []
    
    for corp_code, corp_data in companies_data.items():
        company_names.append(corp_data['corp_name'])
        ratios = corp_data.get('ratios', {})
        
        ratio_values = []
        for ratio in key_ratios:
            if ratio in ratios:
                ratio_values.append(ratios[ratio].get('thstrm', 0))
            else:
                ratio_values.append(0)
        
        comparison_data[corp_data['corp_name']] = ratio_values
    
    if not comparison_data:
        return None
    
    fig = go.Figure()
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    for i, company in enumerate(company_names):
        fig.add_trace(go.Bar(
            name=company,
            x=key_ratios,
            y=comparison_data[company],
            marker_color=colors[i % len(colors)]
        ))
    
    fig.update_layout(
        title={
            'text': '회사별 주요 재무비율 비교',
            'x': 0.5,
            'font': {'size': 16}
        },
        xaxis_title='재무 비율',
        yaxis_title='비율 (%)',
        barmode='group',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        template="plotly_white",
        height=450
    )
    
    return fig


def display_single_company(companies_data):
    """
    Display single company data (existing way)
    """
    st.subheader("📊 상장 기업 조회 결과")

    for corp_code, corp_data in companies_data.items():
        bsns_year = corp_data.get('bsns_year', '')
        fs_div = corp_data.get('fs_div', '')

        with st.expander("**{}** ({}년 {})".format(corp_data['corp_name'], bsns_year, fs_div), expanded=True):
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 주요 지표", "📈 재무 비율", "📋 상세 내역", "💹 주가 정보", "📰 공시 목록"])

            with tab1:
                trend_fig = create_trend_chart(corp_data['financial_data'])
                if trend_fig:
                    st.plotly_chart(trend_fig, use_container_width=True, key="trend_{}".format(corp_code))

                st.markdown("**📋 주요 지표 데이터**")
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
                if summary_data:
                    df = pd.DataFrame(summary_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)

            with tab2:
                if corp_data.get('ratios'):
                    ratio_fig = create_ratio_chart(corp_data['ratios'], corp_data['financial_data'])
                    if ratio_fig:
                        st.plotly_chart(ratio_fig, use_container_width=True, key="ratio_{}".format(corp_code))

                    st.markdown("**📋 재무 비율 데이터**")
                    ratio_data = []
                    for name, values in corp_data['ratios'].items():
                        ratio_data.append({
                            '비율명': name,
                            '당기': '{:.2f}%'.format(values['thstrm']),
                            '전기': '{:.2f}%'.format(values['frmtrm']),
                            '전전기': '{:.2f}%'.format(values['bfefrmtrm'])
                        })
                    df = pd.DataFrame(ratio_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("재무 비율 데이터가 없습니다")

            with tab3:
                detail_data = []
                for item in corp_data['financial_data']:
                    detail_data.append({
                        '계정명': item['display_name'],
                        '당기': _format_number(item.get('thstrm_amount')),
                        '전기': _format_number(item.get('frmtrm_amount')),
                        '전전기': _format_number(item.get('bfefrmtrm_amount'))
                    })
                if detail_data:
                    df = pd.DataFrame(detail_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)

            with tab4:
                st.markdown("**💹 주가 정보**")
                stock_code = corp_data.get('stock_code', '')
                if stock_code and stock_code != 'N/A':
                    try:
                        # bsns_year를 정수로 변환하여 전달
                        bsns_year_int = int(bsns_year) if bsns_year else None
                        stock_info = api_client.get_stock_info(
                            corp_code=corp_data['corp_code'],
                            stock_code=stock_code,
                            corp_name=corp_data['corp_name'],
                            api_key=st.session_state.dart_api_key,
                            bsns_year=bsns_year_int
                        )

                        if stock_info.get('status') in ['success', 'partial']:
                            formatted = stock_info.get('formatted', {})

                            # 기준일자 표시
                            if formatted.get('data_date') and formatted.get('data_date') != '-':
                                st.caption("📅 기준일: {}".format(formatted.get('data_date')))

                            # 현재가 및 등락 정보
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                change_val = formatted.get('change_value', 0)
                                delta_color = "normal" if change_val >= 0 else "inverse"
                                st.metric(
                                    "현재가",
                                    formatted.get('current_price', '-'),
                                    formatted.get('change', '-'),
                                    delta_color=delta_color
                                )
                            with col2:
                                st.metric("거래량", formatted.get('volume', '-'))
                            with col3:
                                st.metric("시가총액", formatted.get('market_cap', '-'))

                            st.divider()

                            # 52주 최고/최저
                            st.markdown("**📊 52주 가격 범위**")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("52주 최저", formatted.get('low_52week', '-'))
                            with col2:
                                current = stock_info.get('price', 0)
                                high52 = stock_info.get('high_52week', 0)
                                low52 = stock_info.get('low_52week', 0)
                                if high52 and low52 and current:
                                    position = ((current - low52) / (high52 - low52)) * 100
                                    st.metric("현재 위치", "{:.1f}%".format(position))
                                else:
                                    st.metric("현재 위치", "-")
                            with col3:
                                st.metric("52주 최고", formatted.get('high_52week', '-'))

                            st.divider()

                            # 당일 시세 테이블
                            st.markdown("**📋 당일 시세**")
                            day_data = [
                                {'항목': '시가', '가격': formatted.get('open_price', '-')},
                                {'항목': '고가', '가격': formatted.get('high_price', '-')},
                                {'항목': '저가', '가격': formatted.get('low_price', '-')},
                                {'항목': '전일종가', '가격': formatted.get('prev_close', '-')},
                            ]
                            df = pd.DataFrame(day_data)
                            st.dataframe(df, use_container_width=True, hide_index=True)

                            # 상장주식수
                            if formatted.get('shares') and formatted.get('shares') != '-':
                                st.caption("상장주식수: {}".format(formatted.get('shares')))

                            st.divider()

                            # 투자 지표 (KRX 공식 데이터)
                            st.markdown("**📈 투자 지표 (KRX 기준)**")

                            # 컬럼명 동적 생성
                            year_end_col = formatted.get('year_end_label', '년말 지표')
                            current_col = formatted.get('data_date_label', '값')

                            valuation_data = [
                                {
                                    '지표': 'PER (주가수익비율)',
                                    year_end_col: formatted.get('year_end_per', '-'),
                                    current_col: formatted.get('per', '-')
                                },
                                {
                                    '지표': 'PBR (주가순자산비율)',
                                    year_end_col: formatted.get('year_end_pbr', '-'),
                                    current_col: formatted.get('pbr', '-')
                                },
                                {
                                    '지표': 'EPS (주당순이익)',
                                    year_end_col: formatted.get('year_end_eps', '-'),
                                    current_col: formatted.get('eps', '-')
                                },
                                {
                                    '지표': 'BPS (주당순자산)',
                                    year_end_col: formatted.get('year_end_bps', '-'),
                                    current_col: formatted.get('bps', '-')
                                },
                                {
                                    '지표': '배당수익률',
                                    year_end_col: formatted.get('year_end_div_yield', '-'),
                                    current_col: formatted.get('div_yield', '-')
                                },
                            ]
                            df_valuation = pd.DataFrame(valuation_data)
                            st.dataframe(df_valuation, use_container_width=True, hide_index=True)
                            st.caption("※ KRX 한국거래소 제공 데이터")

                        else:
                            st.warning("⚠️ 주가 정보를 조회할 수 없습니다: {}".format(stock_info.get('message', '알 수 없는 오류')))

                    except Exception as e:
                        st.error("❌ 주가 조회 실패: {}".format(str(e)))
                else:
                    st.info("ℹ️ 비상장 회사는 주가 정보가 제공되지 않습니다.")

            with tab5:
                st.markdown("**📰 공시 목록**")
                try:
                    disclosure_response = api_client.get_disclosures(
                        corp_code=corp_data['corp_code'],
                        bsns_year=bsns_year,
                        api_key=st.session_state.dart_api_key
                    )

                    disclosures = disclosure_response.get('disclosures', [])
                    total = disclosure_response.get('total', 0)

                    if disclosures and total > 0:
                        st.info("📋 총 {}개의 공시".format(total))
                        _render_disclosure_list(disclosures, "listed_{}".format(corp_code))
                    else:
                        st.warning("⚠️ 공시 정보가 없습니다")

                except Exception as e:
                    st.error("❌ 공시 조회 실패: {}".format(str(e)))


def display_year_by_year_comparison(companies_data):
    """
    Display multiple companies with 4 tabs.
    Inside each tab, show year-by-year side-by-side comparison.
    """
    st.subheader("📊 상장 기업 조회 결과")
    
    company_names = [data['corp_name'] for data in companies_data.values()]
    st.caption("**{}** 비교 분석".format(', '.join(company_names)))
    
    # Get all years
    all_years = set()
    for corp_data in companies_data.values():
        for item in corp_data['financial_data']:
            thstrm_dt = item.get('thstrm_dt', '')
            if thstrm_dt and len(thstrm_dt) >= 4:
                all_years.add(thstrm_dt[:4])
            
            frmtrm_dt = item.get('frmtrm_dt', '')
            if frmtrm_dt and len(frmtrm_dt) >= 4:
                all_years.add(frmtrm_dt[:4])
            
            bfefrmtrm_dt = item.get('bfefrmtrm_dt', '')
            if bfefrmtrm_dt and len(bfefrmtrm_dt) >= 4:
                all_years.add(bfefrmtrm_dt[:4])
    
    sorted_years = sorted(all_years, reverse=True)
    
    # Create 5 tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 주요 지표", "📈 재무 비율", "📋 상세 내역", "💹 주가 정보", "📰 공시 목록"])
    
    # Tab 1: Main Indicators
    with tab1:
        for year in sorted_years:
            st.subheader("{}년".format(year))
            
            cols = st.columns(len(companies_data))
            
            for col_idx, (corp_code, corp_data) in enumerate(companies_data.items()):
                with cols[col_idx]:
                    st.markdown("**{}**".format(corp_data['corp_name']))
                    
                    # Trend chart
                    trend_fig = create_trend_chart(corp_data['financial_data'])
                    if trend_fig:
                        st.plotly_chart(trend_fig, use_container_width=True, key="trend_{}_{}".format(corp_code, year))
                    
                    # Summary data table
                    st.markdown("**주요 지표**")
                    summary_accounts = ['매출액', '영업이익', '당기순이익', '자산총계', '부채총계', '자본총계']
                    summary_data = []
                    
                    for item in corp_data['financial_data']:
                        if item.get('base_display_name') in summary_accounts:
                            display_name = item['display_name']
                            amount = 0
                            
                            if item.get('thstrm_dt', '')[:4] == year:
                                amount = item.get('thstrm_amount', 0)
                            elif item.get('frmtrm_dt', '')[:4] == year:
                                amount = item.get('frmtrm_amount', 0)
                            elif item.get('bfefrmtrm_dt', '')[:4] == year:
                                amount = item.get('bfefrmtrm_amount', 0)
                            
                            if amount:
                                summary_data.append({
                                    '계정명': display_name,
                                    '금액': _format_number(amount)
                                })
                    
                    if summary_data:
                        df = pd.DataFrame(summary_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.info("{}년 데이터 없음".format(year))
            
            st.divider()
    
    # Tab 2: Financial Ratios
    with tab2:
        for year in sorted_years:
            st.subheader("{}년".format(year))
            
            cols = st.columns(len(companies_data))
            
            for col_idx, (corp_code, corp_data) in enumerate(companies_data.items()):
                with cols[col_idx]:
                    st.markdown("**{}**".format(corp_data['corp_name']))
                    
                    if corp_data.get('ratios'):
                        # Ratio chart
                        ratio_fig = create_ratio_chart(corp_data['ratios'], corp_data['financial_data'])
                        if ratio_fig:
                            st.plotly_chart(ratio_fig, use_container_width=True, key="ratio_{}_{}".format(corp_code, year))
                        
                        # Ratio data table
                        st.markdown("**재무 비율**")
                        ratio_data = []
                        for name, values in corp_data['ratios'].items():
                            ratio_data.append({
                                '비율명': name,
                                '당기': '{:.2f}%'.format(values['thstrm']),
                                '전기': '{:.2f}%'.format(values['frmtrm']),
                                '전전기': '{:.2f}%'.format(values['bfefrmtrm'])
                            })
                        df = pd.DataFrame(ratio_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.info("재무 비율 데이터가 없습니다")
            
            st.divider()
    
    # Tab 3: Detailed Information
    with tab3:
        for year in sorted_years:
            st.subheader("{}년".format(year))
            
            cols = st.columns(len(companies_data))
            
            for col_idx, (corp_code, corp_data) in enumerate(companies_data.items()):
                with cols[col_idx]:
                    st.markdown("**{}**".format(corp_data['corp_name']))
                    
                    detail_data = []
                    for item in corp_data['financial_data']:
                        amount = 0
                        
                        if item.get('thstrm_dt', '')[:4] == year:
                            amount = item.get('thstrm_amount', 0)
                        elif item.get('frmtrm_dt', '')[:4] == year:
                            amount = item.get('frmtrm_amount', 0)
                        elif item.get('bfefrmtrm_dt', '')[:4] == year:
                            amount = item.get('bfefrmtrm_amount', 0)
                        
                        if amount:
                            detail_data.append({
                                '계정명': item['display_name'],
                                '금액': _format_number(amount)
                            })
                    
                    if detail_data:
                        df = pd.DataFrame(detail_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.info("{}년 데이터 없음".format(year))
            
            st.divider()
    
    # Tab 4: Stock Price Info
    with tab4:
        st.markdown("**💹 주가 정보 비교**")
        cols = st.columns(len(companies_data))

        for col_idx, (corp_code, corp_data) in enumerate(companies_data.items()):
            with cols[col_idx]:
                st.markdown("**{}**".format(corp_data['corp_name']))
                stock_code = corp_data.get('stock_code', '')
                bsns_year = corp_data.get('bsns_year', '')

                if stock_code and stock_code != 'N/A':
                    try:
                        # bsns_year를 정수로 변환하여 전달
                        bsns_year_int = int(bsns_year) if bsns_year else None
                        stock_info = api_client.get_stock_info(
                            corp_code=corp_code,
                            stock_code=stock_code,
                            corp_name=corp_data['corp_name'],
                            api_key=st.session_state.dart_api_key,
                            bsns_year=bsns_year_int
                        )

                        if stock_info.get('status') in ['success', 'partial']:
                            formatted = stock_info.get('formatted', {})

                            # 기준일자 표시
                            if formatted.get('data_date') and formatted.get('data_date') != '-':
                                st.caption("📅 {}".format(formatted.get('data_date')))

                            # 현재가 및 등락
                            change_val = formatted.get('change_value', 0)
                            delta_color = "normal" if change_val >= 0 else "inverse"
                            st.metric(
                                "현재가",
                                formatted.get('current_price', '-'),
                                formatted.get('change', '-'),
                                delta_color=delta_color
                            )
                            st.metric("거래량", formatted.get('volume', '-'))
                            st.metric("시가총액", formatted.get('market_cap', '-'))

                            st.divider()

                            # 52주 정보
                            st.caption("52주 범위")
                            st.write(formatted.get('week52_range', '-'))

                            # 당일 시세
                            st.caption("당일 시세")
                            day_data = [
                                {'항목': '시가', '가격': formatted.get('open_price', '-')},
                                {'항목': '고가', '가격': formatted.get('high_price', '-')},
                                {'항목': '저가', '가격': formatted.get('low_price', '-')},
                            ]
                            df = pd.DataFrame(day_data)
                            st.dataframe(df, use_container_width=True, hide_index=True)

                            # 투자 지표 (KRX 공식 데이터)
                            st.divider()
                            st.caption("투자 지표 (KRX 기준)")

                            # 연말 지표와 현재 지표 비교 표시
                            year_end_label = formatted.get('year_end_label', '년말')
                            st.write("**{}**".format(year_end_label))
                            st.write("PER: {} | PBR: {}".format(
                                formatted.get('year_end_per', '-'),
                                formatted.get('year_end_pbr', '-')
                            ))
                            st.write("EPS: {} | BPS: {}".format(
                                formatted.get('year_end_eps', '-'),
                                formatted.get('year_end_bps', '-')
                            ))

                            st.write("**현재**")
                            st.write("PER: {} | PBR: {}".format(
                                formatted.get('per', '-'),
                                formatted.get('pbr', '-')
                            ))
                            st.write("EPS: {} | BPS: {}".format(
                                formatted.get('eps', '-'),
                                formatted.get('bps', '-')
                            ))

                        else:
                            st.warning("주가 정보 없음")

                    except Exception as e:
                        st.error("조회 실패: {}".format(str(e)))
                else:
                    st.info("비상장 회사")

    # Tab 5: Disclosure List
    with tab5:
        for corp_code, corp_data in companies_data.items():
            st.subheader(corp_data['corp_name'])

            bsns_year = corp_data.get('bsns_year', '')

            try:
                disclosure_response = api_client.get_disclosures(
                    corp_code=corp_code,
                    bsns_year=bsns_year,
                    api_key=st.session_state.dart_api_key
                )

                disclosures = disclosure_response.get('disclosures', [])
                total = disclosure_response.get('total', 0)

                if disclosures and total > 0:
                    st.info("📋 총 {}개의 공시".format(total))
                    _render_disclosure_list(disclosures, "comparison_{}".format(corp_code))
                else:
                    st.warning("⚠️ 공시 정보가 없습니다")

            except Exception as e:
                st.error("❌ 공시 조회 실패: {}".format(str(e)))
            
            st.divider()



# Environment variable loading and session state initialization
import os
from dotenv import load_dotenv
load_dotenv()

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
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1
if 'search_page' not in st.session_state:
    st.session_state.search_page = 0

# 여백 축소 CSS 적용
st.markdown("""
<style>
    /* 블록 요소들 사이 간격 축소 */
    .stMarkdown, .stDataFrame, .stMetric, .stPlotlyChart {
        margin-bottom: 0.3rem !important;
    }

    /* 구분선 마진 축소 */
    hr {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }

    /* 탭 내부 패딩 축소 */
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 0.5rem !important;
    }

    /* expander 내부 패딩 축소 */
    .streamlit-expanderContent {
        padding-top: 0.3rem !important;
        padding-bottom: 0.3rem !important;
    }

    /* metric 컴포넌트 간격 축소 */
    [data-testid="stMetricValue"] {
        font-size: 1.3rem !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.8rem !important;
    }
    div[data-testid="metric-container"] {
        padding: 0.3rem 0 !important;
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

    /* dataframe 마진 축소 */
    .stDataFrame {
        margin-top: 0.2rem !important;
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
</style>
""", unsafe_allow_html=True)

# API client
@st.cache_resource
def get_api_client():
    return APIClient()

api_client = get_api_client()

# Check API key
if not st.session_state.dart_api_key:
    st.error("DART API 키가 설정되지 않았습니다.")
    st.info("홈 페이지에서 DART API 키를 설정하거나 .env 파일에 DART_API_KEY를 추가하세요")
    
    with st.expander("디버깅 정보"):
        st.write("환경변수 DART_API_KEY: {}".format(bool(os.getenv('DART_API_KEY'))))
        st.write("세션상태 dart_api_key: {}".format(bool(st.session_state.dart_api_key)))
        
        temp_key = st.text_input("임시 DART API 키 입력:", type="password")
        if st.button("임시 설정"):
            if temp_key and is_valid_api_key(temp_key):
                st.session_state.dart_api_key = temp_key
                st.success("임시로 API 키가 설정되었습니다")
                st.rerun()
            else:
                st.error("유효하지 않은 API 키입니다")
    
    st.stop()

# Header
st.title("재무 분석")

# Progress Bar
cols = st.columns(3)
for i, (col, label) in enumerate(zip(cols, ["회사 선택", "재무 조회", "AI 브리핑"])):
    with col:
        if i + 1 < st.session_state.current_step:
            st.success("✓ {}".format(label))
        elif i + 1 == st.session_state.current_step:
            st.info("**{}. {}**".format(i+1, label))
        else:
            st.markdown("<div style='line-height: 1.6;'>{}. {}</div>".format(i+1, label), unsafe_allow_html=True)
st.divider()

# ==================== STEP 1: Company Selection ====================
if st.session_state.current_step == 1:
    st.subheader("STEP 1. 분석할 회사 선택")
    st.caption("최대 3개의 회사를 선택하여 비교 분석할 수 있습니다")
    st.write("")
    
    if st.session_state.selected_companies:
        st.markdown("**선택된 회사**")
        for i, company in enumerate(st.session_state.selected_companies):
            col1, col2, col3, col4 = st.columns([0.5, 3, 1.5, 1])
            with col1:
                st.write("{}. ".format(i+1))
            with col2:
                st.write("**{}**".format(company['corp_name']))
            with col3:
                if company.get('stock_code') != 'N/A':
                    st.markdown("🔵 **상장**")
                else:
                    st.markdown("⚪ 비상장")
            with col4:
                if st.button("제거", key="del_{}".format(i), type="secondary"):
                    removed_company = st.session_state.selected_companies.pop(i)
                    # 해당 기업의 재무 데이터도 함께 삭제
                    corp_code = removed_company.get('corp_code')
                    if corp_code and corp_code in st.session_state.financial_results:
                        del st.session_state.financial_results[corp_code]
                    st.rerun()
        st.divider()
    
    col1, col2 = st.columns([4, 1])
    with col1:
        keyword = st.text_input(
            "회사명 또는 종목코드",
            placeholder="예: 삼성전자, 005930",
            label_visibility="collapsed"
        )
    with col2:
        search_btn = st.button("검색", use_container_width=True, type="primary")
    
    if search_btn and keyword:
        with st.spinner("검색 중..."):
            try:
                response = api_client.search_companies(keyword, st.session_state.dart_api_key)
                st.session_state.search_results = response.get('companies', [])
                st.session_state.search_page = 0
            except Exception as e:
                st.error("검색 실패: {}".format(str(e)))
                st.session_state.search_results = []
    
    if 'search_results' in st.session_state and st.session_state.search_results:
        results = st.session_state.search_results
        st.success("{}개의 결과를 찾았습니다.".format(len(results)))
        
        items_per_page = 20
        total_pages = (len(results) - 1) // items_per_page + 1
        current_page = st.session_state.search_page
        
        start_idx = current_page * items_per_page
        end_idx = min(start_idx + items_per_page, len(results))
        page_results = results[start_idx:end_idx]
        
        if total_pages > 1:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if current_page > 0:
                    if st.button("◀ 이전", key="prev_page"):
                        st.session_state.search_page -= 1
                        st.rerun()
            with col2:
                st.markdown("<div style='text-align: center'>페이지 {} / {} ({}-{} / {}건)</div>".format(current_page + 1, total_pages, start_idx + 1, end_idx, len(results)), 
                          unsafe_allow_html=True)
            with col3:
                if current_page < total_pages - 1:
                    if st.button("다음 ▶", key="next_page"):
                        st.session_state.search_page += 1
                        st.rerun()
            st.divider()
        
        col1, col2, col3, col4 = st.columns([2.5, 1.5, 1, 1.2])
        with col1:
            st.markdown("**회사명**")
        with col2:
            st.markdown("**고유번호**")
        with col3:
            st.markdown("**구분**")
        with col4:
            st.markdown("**선택**")
        
        st.divider()
        
        for idx, company in enumerate(page_results):
            col1, col2, col3, col4 = st.columns([2.5, 1.5, 1, 1.2])
            
            is_listed = company.get('stock_code') != 'N/A'
            
            with col1:
                st.write(company['corp_name'])
            with col2:
                st.caption(company['corp_code'])
            with col3:
                if is_listed:
                    st.markdown("🔵 **상장**")
                else:
                    st.markdown("⚪ 비상장")
            with col4:
                already_selected = any(
                    c['corp_code'] == company['corp_code']
                    for c in st.session_state.selected_companies
                )
                
                if already_selected:
                    st.caption("✓ 선택됨")
                elif len(st.session_state.selected_companies) < 3:
                    if st.button("선택", key="select_{}_{}".format(idx, company['corp_code']), type="secondary"):
                        st.session_state.selected_companies.append(company)
                        st.rerun()
                else:
                    st.caption("최대 3개")
    
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 1])
    with col3:
        if st.button("다음 단계 →", use_container_width=True, type="primary", 
                    disabled=len(st.session_state.selected_companies) == 0):
            st.session_state.current_step = 2
            st.rerun()

# ==================== STEP 2: Financial Data ====================
elif st.session_state.current_step == 2:
    st.subheader("STEP 2. 재무정보 조회")
    st.caption("선택한 회사의 재무제표를 조회합니다")
    st.write("")

    companies_by_type = {'listed': [], 'unlisted': []}
    for company in st.session_state.selected_companies:
        if company.get('stock_code') != 'N/A':
            companies_by_type['listed'].append(company)
        else:
            companies_by_type['unlisted'].append(company)

    if 'company_options' not in st.session_state:
        st.session_state.company_options = {}

    if companies_by_type['listed']:
        st.markdown("### 📊 상장 기업")
        st.caption("각 회사별로 조회 옵션을 선택하세요")

        col1, col2, col3, col4 = st.columns([2.5, 1.5, 2, 1])
        with col1:
            st.markdown("**회사명**")
        with col2:
            st.markdown("**사업연도**")
        with col3:
            st.markdown("**재무제표 구분**")
        with col4:
            st.markdown("**상태**")

        st.divider()

        for company in companies_by_type['listed']:
            corp_code = company['corp_code']
            col1, col2, col3, col4 = st.columns([2.5, 1.5, 2, 1])

            with col1:
                st.write("**{}**".format(company['corp_name']))

            with col2:
                year = st.selectbox(
                    "연도",
                    options=[str(y) for y in range(2025, 2010, -1)],
                    key="year_{}".format(corp_code),
                    label_visibility="collapsed"
                )
                st.session_state.company_options[corp_code] = st.session_state.company_options.get(corp_code, {})
                st.session_state.company_options[corp_code]['year'] = year

            with col3:
                fs_option = st.selectbox(
                    "구분",
                    options=["CFS (연결)", "OFS (별도)"],
                    key="fs_{}".format(corp_code),
                    label_visibility="collapsed"
                )
                st.session_state.company_options[corp_code]['fs_div'] = fs_option.split(' ')[0]

            with col4:
                if corp_code in st.session_state.financial_results:
                    st.success("✓ 조회됨")
                else:
                    st.caption("대기 중")

        st.write("")

        if st.button("📊 상장 기업 재무정보 조회", use_container_width=True, type="primary", key="btn_listed"):
            with st.spinner("상장 기업 재무정보 조회 중..."):
                for company in companies_by_type['listed']:
                    corp_code = company['corp_code']
                    options = st.session_state.company_options.get(corp_code, {})
                    bsns_year = options.get('year', '2024')
                    fs_div = options.get('fs_div', 'CFS')

                    try:
                        response = api_client.get_financial_data(
                            corp_code=corp_code,
                            bsns_year=bsns_year,
                            fs_div=fs_div,
                            api_key=st.session_state.dart_api_key
                        )

                        financial_data = response.get('financial_data', [])

                        if not financial_data:
                            st.warning("{}: {}년 재무 데이터 없음".format(company['corp_name'], bsns_year))
                            continue

                        st.session_state.financial_results[corp_code] = {
                            'corp_name': company['corp_name'],
                            'corp_code': corp_code,
                            'stock_code': company.get('stock_code'),
                            'is_listed': True,
                            'bsns_year': bsns_year,
                            'fs_div': fs_div,
                            'financial_data': financial_data,
                            'ratios': response.get('ratios', {})
                        }
                    except Exception as e:
                        st.error("{} 조회 실패: {}".format(company['corp_name'], str(e)))

                if any(c['corp_code'] in st.session_state.financial_results for c in companies_by_type['listed']):
                    st.success("상장 기업 재무정보 조회 완료")
                    st.rerun()

    if companies_by_type['unlisted']:
        if companies_by_type['listed']:
            st.divider()
        st.markdown("### 📄 비상장 기업")
        st.caption("비상장 기업은 재무정보 없이 최근 3년 공시 목록만 조회됩니다")

        col1, col2, col3 = st.columns([3, 2, 1.5])
        with col1:
            st.markdown("**회사명**")
        with col2:
            st.markdown("**조회 기간**")
        with col3:
            st.markdown("**상태**")

        st.divider()

        from datetime import datetime
        current_year = datetime.now().year

        for company in companies_by_type['unlisted']:
            corp_code = company['corp_code']
            col1, col2, col3 = st.columns([3, 2, 1.5])

            with col1:
                st.write("**{}**".format(company['corp_name']))

            with col2:
                st.caption("{}년 ~ {}년".format(current_year-2, current_year))

            with col3:
                if corp_code in st.session_state.financial_results:
                    st.success("✓ 조회됨")
                else:
                    st.caption("대기 중")

        st.write("")

        if st.button("📄 비상장 기업 공시 조회", use_container_width=True, type="primary", key="btn_unlisted"):
            with st.spinner("비상장 기업 공시 목록 조회 중..."):
                for company in companies_by_type['unlisted']:
                    corp_code = company['corp_code']

                    try:
                        all_disclosures = []
                        for year in range(current_year, current_year - 3, -1):
                            try:
                                response = api_client.get_disclosures(
                                    corp_code=corp_code,
                                    bsns_year=str(year),
                                    api_key=st.session_state.dart_api_key
                                )
                                disclosures = response.get('disclosures', [])
                                all_disclosures.extend(disclosures)
                            except:
                                continue

                        st.session_state.financial_results[corp_code] = {
                            'corp_name': company['corp_name'],
                            'corp_code': corp_code,
                            'stock_code': company.get('stock_code'),
                            'is_listed': False,
                            'financial_data': [],
                            'ratios': {},
                            'disclosures': all_disclosures
                        }

                    except Exception as e:
                        st.error("{} 공시 조회 실패: {}".format(company['corp_name'], str(e)))

                if any(c['corp_code'] in st.session_state.financial_results for c in companies_by_type['unlisted']):
                    st.success("비상장 기업 공시 조회 완료")
                    st.rerun()
    
    if st.session_state.financial_results:
        st.divider()

        listed_results = {k: v for k, v in st.session_state.financial_results.items() if v.get('is_listed', True)}
        unlisted_results = {k: v for k, v in st.session_state.financial_results.items() if not v.get('is_listed', True)}

        if listed_results:
            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                if st.button("📥 엑셀 다운로드", use_container_width=True, type="secondary"):
                    with st.spinner("엑셀 파일 생성 중..."):
                        try:
                            companies_data = []
                            for corp_data in listed_results.values():
                                companies_data.append({
                                    'corp_code': corp_data['corp_code'],
                                    'corp_name': corp_data['corp_name'],
                                    'stock_code': corp_data.get('stock_code', 'N/A'),
                                    'financial_data': corp_data['financial_data'],
                                    'ratios': corp_data.get('ratios', {})
                                })

                            excel_bytes = api_client.download_excel(companies_data)

                            from datetime import datetime
                            if len(companies_data) == 1:
                                filename = "재무제표_{}_{}".format(companies_data[0]['corp_name'], datetime.now().strftime('%Y%m%d')) + ".xlsx"
                            else:
                                filename = "재무제표_비교_{}".format(datetime.now().strftime('%Y%m%d')) + ".xlsx"

                            st.success("엑셀 파일이 생성되었습니다!")
                            st.markdown(get_download_link(excel_bytes, filename, "excel"), unsafe_allow_html=True)

                        except Exception as e:
                            st.error("엑셀 다운로드 실패: {}".format(str(e)))

            st.divider()

        # === Listed company results display ===
        if listed_results:
            if len(listed_results) >= 2:
                # Multiple companies: show 4 tabs with year-by-year comparison
                display_year_by_year_comparison(listed_results)
            else:
                # Single company: show expander with 4 tabs
                display_single_company(listed_results)

        # === Unlisted company results display ===
        if unlisted_results:
            if listed_results:
                st.divider()
            st.subheader("📄 비상장 기업 공시 목록")
            st.caption("비상장 기업은 공시 정보만 제공됩니다")

            for corp_code, corp_data in unlisted_results.items():
                with st.expander("**{}** (최근 3년 공시)".format(corp_data['corp_name']), expanded=True):
                    disclosures = corp_data.get('disclosures', [])

                    if disclosures:
                        st.info("📋 총 {}개의 공시".format(len(disclosures)))
                        _render_disclosure_list(disclosures, "unlisted_{}".format(corp_code))
                    else:
                        st.warning("⚠️ 공시 정보가 없습니다")
    
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("← 이전 단계", use_container_width=True, type="secondary"):
            # 이전 단계로 돌아갈 때 재무 데이터 초기화 (기업 재선택 시 혼동 방지)
            st.session_state.financial_results = {}
            st.session_state.current_step = 1
            st.rerun()
    with col3:
        if st.session_state.financial_results:
            if st.button("AI 브리핑 →", use_container_width=True, type="primary"):
                st.session_state.current_step = 3
                st.rerun()

# ==================== STEP 3: AI Briefing ====================
elif st.session_state.current_step == 3:
    available_providers = [
        (key, name) for key, name in [
            ('gemini', 'Google Gemini'),
            ('openai', 'OpenAI GPT'),
            ('claude', 'Anthropic Claude'),
            ('upstage', 'Upstage Solar')
        ] if key in st.session_state.llm_api_keys and st.session_state.llm_api_keys[key]
    ]

    if not available_providers:
        st.warning("먼저 홈에서 LLM API 키를 설정하세요")
        if st.button("← 이전 단계", type="secondary"):
            st.session_state.current_step = 2
            st.rerun()
        st.stop()

    st.subheader("STEP 3. AI 재무 브리핑")

    listed_results = {k: v for k, v in st.session_state.financial_results.items() if v.get('is_listed', True)}
    unlisted_results = {k: v for k, v in st.session_state.financial_results.items() if not v.get('is_listed', True)}

    if unlisted_results:
        unlisted_names = [v['corp_name'] for v in unlisted_results.values()]
        st.warning("⚠️ 비상장 기업은 재무 데이터가 없어 AI 브리핑이 불가능합니다: **{}**".format(', '.join(unlisted_names)))

    if not listed_results:
        st.error("❌ 선택된 회사 중 상장 기업이 없어 AI 재무 브리핑을 진행할 수 없습니다.")
        st.info("💡 AI 브리핑은 상장 기업의 재무 데이터를 기반으로 분석을 수행합니다. 비상장 기업은 공시 정보만 제공됩니다.")

        st.divider()
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("← 이전 단계", use_container_width=True, type="secondary"):
                st.session_state.current_step = 2
                st.rerun()
        with col3:
            if st.button("처음으로", use_container_width=True, type="primary"):
                st.session_state.current_step = 1
                st.session_state.selected_companies = []
                st.session_state.financial_results = {}
                st.rerun()
        st.stop()

    listed_names = [v['corp_name'] for v in listed_results.values()]
    if len(listed_results) == 1:
        st.caption("**{}**의 재무 데이터를 AI가 분석합니다".format(listed_names[0]))
    else:
        st.caption("**{}**의 재무 데이터를 비교 분석합니다".format(', '.join(listed_names)))

    st.write("")

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
                'default': '표준 분석 (600단어)',
                'executive': '경영진 보고 (500단어)',
                'detailed': '상세 분석 (800단어)'
            }[x]
        )

    with col3:
        st.write("")
        generate_btn = st.button("생성", use_container_width=True, type="primary")

    if len(listed_results) == 1:
        corp_data = list(listed_results.values())[0]
        cache_key = "briefing_{}_{}{}".format(corp_data['corp_code'], provider, style)

        if generate_btn:
            with st.spinner("브리핑 생성 중... ({})".format(dict(available_providers)[provider])):
                try:
                    financial_data_payload = {
                        "items": corp_data['financial_data'],
                        "ratios": corp_data.get('ratios', {})
                    }

                    result = api_client.generate_briefing(
                        corp_name=corp_data['corp_name'],
                        financial_data=financial_data_payload,
                        provider=provider,
                        api_key=st.session_state.llm_api_keys[provider],
                        style=style
                    )

                    briefing_text = result.get('briefing', '')

                    if briefing_text and len(briefing_text) > 50:
                        cleaned_text = clean_briefing_text(briefing_text)

                        if len(cleaned_text) > 50:
                            st.session_state[cache_key] = cleaned_text
                            st.session_state["{}_provider".format(cache_key)] = dict(available_providers)[provider]
                            st.session_state["{}_style".format(cache_key)] = style
                            st.divider()
                            st.markdown(cleaned_text)
                        else:
                            st.error("AI 브리핑 생성에 실패했습니다. 다른 LLM을 시도해보세요.")
                    else:
                        st.error("AI 브리핑이 제대로 생성되지 않았습니다. 다시 시도해주세요.")

                except Exception as e:
                    st.error("브리핑 생성 실패: {}".format(str(e)))
                    st.info("API 키 또는 할당량을 확인하세요")

        elif cache_key in st.session_state:
            st.divider()
            st.markdown(st.session_state[cache_key])

        if cache_key in st.session_state and st.session_state[cache_key]:
            st.divider()
            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                if st.button("📄 PDF 다운로드", use_container_width=True, type="secondary"):
                    with st.spinner("PDF 생성 중..."):
                        try:
                            company_info = {
                                'corp_name': corp_data['corp_name'],
                                'stock_code': corp_data.get('stock_code', 'N/A')
                            }

                            financial_summary = {'key_metrics': []}

                            summary_accounts = ['매출액', '영업이익', '당기순이익']
                            for account in summary_accounts:
                                for item in corp_data['financial_data']:
                                    if item.get('base_display_name') == account:
                                        financial_summary['key_metrics'].append({
                                            'name': account,
                                            'current': _format_number(item.get('thstrm_amount')),
                                            'previous': _format_number(item.get('frmtrm_amount')),
                                            'change_rate': '-'
                                        })
                                        break

                            provider_name = st.session_state.get("{}_provider".format(cache_key), dict(available_providers)[provider])
                            analysis_style = st.session_state.get("{}_style".format(cache_key), style)

                            pdf_bytes = api_client.download_briefing_pdf(
                                briefing_text=st.session_state[cache_key],
                                company_info=company_info,
                                financial_summary=financial_summary,
                                llm_provider=provider_name,
                                analysis_style=analysis_style
                            )

                            from datetime import datetime
                            filename = "AI재무분석_{}_{}".format(corp_data['corp_name'], datetime.now().strftime('%Y%m%d')) + ".pdf"

                            st.success("PDF 파일이 생성되었습니다!")
                            st.markdown(get_download_link(pdf_bytes, filename, "pdf"), unsafe_allow_html=True)

                        except Exception as e:
                            st.error("PDF 다운로드 실패: {}".format(str(e)))

    else:
        corp_codes = '_'.join([c['corp_code'] for c in listed_results.values()])
        cache_key = "briefing_compare_{}_{}{}".format(corp_codes, provider, style)

        if generate_btn:
            with st.spinner("비교 브리핑 생성 중... ({})".format(dict(available_providers)[provider])):
                try:
                    companies_data = []
                    for corp_data in listed_results.values():
                        companies_data.append({
                            "corp_name": corp_data['corp_name'],
                            "items": corp_data['financial_data'],
                            "ratios": corp_data.get('ratios', {})
                        })

                    comparison_payload = {
                        "items": companies_data,
                        "ratios": {}
                    }

                    result = api_client.generate_briefing(
                        corp_name="{} 회사 비교".format(len(companies_data)),
                        financial_data=comparison_payload,
                        provider=provider,
                        api_key=st.session_state.llm_api_keys[provider],
                        style=style
                    )

                    briefing_text = result.get('briefing', '')

                    if briefing_text and len(briefing_text) > 50:
                        cleaned_text = clean_briefing_text(briefing_text)

                        if len(cleaned_text) > 50:
                            st.session_state[cache_key] = cleaned_text
                            st.session_state["{}_provider".format(cache_key)] = dict(available_providers)[provider]
                            st.session_state["{}_style".format(cache_key)] = style
                            st.divider()
                            st.markdown(cleaned_text)
                        else:
                            st.error("AI 브리핑 생성에 실패했습니다. 다른 LLM을 시도해보세요.")
                    else:
                        st.error("AI 브리핑이 제대로 생성되지 않았습니다. 다시 시도해주세요.")

                except Exception as e:
                    st.error("브리핑 생성 실패: {}".format(str(e)))
                    st.info("API 키 또는 할당량을 확인하세요")

        elif cache_key in st.session_state:
            st.divider()
            st.markdown(st.session_state[cache_key])

        if cache_key in st.session_state and st.session_state[cache_key]:
            st.divider()
            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                if st.button("📄 PDF 다운로드", use_container_width=True, type="secondary"):
                    with st.spinner("PDF 생성 중..."):
                        try:
                            companies_info = []
                            for corp_data in listed_results.values():
                                companies_info.append({
                                    'corp_name': corp_data['corp_name'],
                                    'stock_code': corp_data.get('stock_code', 'N/A')
                                })

                            company_info = {'companies': companies_info}
                            provider_name = st.session_state.get("{}_provider".format(cache_key), dict(available_providers)[provider])

                            pdf_bytes = api_client.download_briefing_pdf(
                                briefing_text=st.session_state[cache_key],
                                company_info=company_info,
                                financial_summary=None,
                                llm_provider=provider_name,
                                analysis_style="comparison"
                            )

                            from datetime import datetime
                            filename = "AI재무분석_비교_{}".format(datetime.now().strftime('%Y%m%d')) + ".pdf"

                            st.success("PDF 파일이 생성되었습니다!")
                            st.markdown(get_download_link(pdf_bytes, filename, "pdf"), unsafe_allow_html=True)

                        except Exception as e:
                            st.error("PDF 다운로드 실패: {}".format(str(e)))
    
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("← 이전 단계", use_container_width=True, type="secondary"):
            st.session_state.current_step = 2
            st.rerun()
    with col3:
        if st.button("처음으로", use_container_width=True, type="primary"):
            st.session_state.current_step = 1
            st.session_state.selected_companies = []
            st.session_state.financial_results = {}
            st.rerun()