def get_year_labels(financial_data):
    """재무 데이터에서 연도 라벨 추출 (전전기, 전기, 당기)"""
    year_labels = {'bfefrmtrm': '전전기', 'frmtrm': '전기', 'thstrm': '당기'}
    
    # 첫 번째 항목에서 연도 추출
    for item in financial_data:
        bfefrmtrm_dt = item.get('bfefrmtrm_dt', '')
        frmtrm_dt = item.get('frmtrm_dt', '')
        thstrm_dt = item.get('thstrm_dt', '')
        
        if bfefrmtrm_dt and len(bfefrmtrm_dt) >= 4:
            year_labels['bfefrmtrm'] = f"전전기 ({bfefrmtrm_dt[:4]})"
        if frmtrm_dt and len(frmtrm_dt) >= 4:
            year_labels['frmtrm'] = f"전기 ({frmtrm_dt[:4]})"
        if thstrm_dt and len(thstrm_dt) >= 4:
            year_labels['thstrm'] = f"당기 ({thstrm_dt[:4]})"
        
        # 연도를 찾았으면 break
        if all(key in year_labels and '(' in year_labels[key] for key in ['bfefrmtrm', 'frmtrm', 'thstrm']):
            break
    
    return year_labels


def create_ratio_chart(ratios, financial_data):
    """재무비율 차트 생성 (연도 포함)"""
    key_ratios = ['영업이익률', '순이익률', 'ROE', 'ROA']
    available_ratios = {k: v for k, v in ratios.items() if k in key_ratios and v}
    
    if not available_ratios:
        return None
    
    # 연도 라벨 가져오기
    year_labels = get_year_labels(financial_data)
    
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
