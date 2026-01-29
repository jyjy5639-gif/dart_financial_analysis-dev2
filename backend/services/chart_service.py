import os
import platform
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, List, Optional, Tuple
import base64
from io import BytesIO
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import numpy as np


class ChartService:
    """재무 데이터 시각화 서비스 - 모든 환경 지원"""
    
    def __init__(self):
        self._setup_matplotlib()
        self._setup_plotly()
    
    def _setup_matplotlib(self):
        """Matplotlib 한글 폰트 설정 - Windows/Linux/Mac/클라우드 모두 지원"""
        plt.rcParams['axes.unicode_minus'] = False
        
        font_registered = False
        current_system = platform.system()
        
        print(f"Matplotlib 폰트 설정 시작 (OS: {current_system})")
        
        # 1. 프로젝트 내 폰트 확인 (모든 환경에서 작동)
        try:
            project_root = Path(__file__).parent.parent.parent
            project_font = project_root / "fonts" / "NotoSansKR-Regular.ttf"
            
            if project_font.exists():
                fm.fontManager.addfont(str(project_font))
                plt.rcParams['font.family'] = 'NotoSansKR'
                font_registered = True
                print(f"✅ Matplotlib 폰트 로드 (프로젝트): {project_font}")
                return
            else:
                print(f"프로젝트 폰트 찾을 수 없음: {project_font}")
        except Exception as e:
            print(f"프로젝트 폰트 로드 실패: {e}")
        
        # 2. OS별 기본 경로
        if current_system == "Windows":
            windows_paths = [
                "C:/Windows/Fonts/NotoSansKR-Regular.ttf",
                "C:/Windows/Fonts/NotoSansKR-Medium.ttf",
            ]
            for path in windows_paths:
                if os.path.exists(path):
                    try:
                        fm.fontManager.addfont(path)
                        plt.rcParams['font.family'] = 'NotoSansKR'
                        font_registered = True
                        print(f"✅ Matplotlib 폰트 로드 (Windows): {path}")
                        return
                    except Exception as e:
                        print(f"Windows 폰트 로드 실패: {e}")
        
        elif current_system == "Darwin":  # macOS
            mac_paths = [
                "/Library/Fonts/NotoSansKR-Regular.ttf",
                "/System/Library/Fonts/NotoSansKR-Regular.ttf",
                f"{os.path.expanduser('~')}/Library/Fonts/NotoSansKR-Regular.ttf",
            ]
            for path in mac_paths:
                if os.path.exists(path):
                    try:
                        fm.fontManager.addfont(path)
                        plt.rcParams['font.family'] = 'NotoSansKR'
                        font_registered = True
                        print(f"✅ Matplotlib 폰트 로드 (macOS): {path}")
                        return
                    except Exception as e:
                        print(f"macOS 폰트 로드 실패: {e}")
        
        else:  # Linux (Render, Streamlit Cloud)
            linux_paths = [
                "/usr/share/fonts/opentype/noto/NotoSansKR-Regular.ttf",
                "/usr/share/fonts/noto/NotoSansKR-Regular.ttf",
                "/usr/share/fonts/opentype/noto-cjk/NotoSansCJKkr-Regular.ttf",
                "/usr/share/fonts/noto-cjk/NotoSansCJKkr-Regular.ttf",
            ]
            for path in linux_paths:
                if os.path.exists(path):
                    try:
                        fm.fontManager.addfont(path)
                        plt.rcParams['font.family'] = 'NotoSansKR'
                        font_registered = True
                        print(f"✅ Matplotlib 폰트 로드 (Linux): {path}")
                        return
                    except Exception as e:
                        print(f"Linux 폰트 로드 실패: {e}")
        
        # 3. 폰트 로드 실패 시
        if not font_registered:
            print("⚠️ 경고: NotoSansKR 폰트를 찾을 수 없습니다.")
            print(f"   OS: {current_system}")
            print(f"   프로젝트 루트: {Path(__file__).parent.parent.parent}")
            print(f"   현재 작업 디렉토리: {os.getcwd()}")
            print("   기본 폰트(DejaVu Sans)를 사용합니다.")
            plt.rcParams['font.family'] = ['DejaVu Sans']
    
    def _setup_plotly(self):
        """Plotly 기본 설정"""
        # 색상 팔레트 정의
        self.colors = {
            'primary': '#1f77b4',
            'secondary': '#ff7f0e', 
            'success': '#2ca02c',
            'danger': '#d62728',
            'warning': '#ff7f0e',
            'info': '#17a2b8',
            'light': '#f8f9fa',
            'dark': '#343a40'
        }
        
        self.color_sequence = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    def create_trend_chart(
        self, 
        financial_data: List[Dict], 
        accounts: List[str] = None,
        chart_type: str = "plotly"
    ) -> str:
        """
        주요 재무지표 트렌드 차트 생성
        
        Args:
            financial_data: 재무 데이터 리스트
            accounts: 표시할 계정 (기본: 주요 지표)
            chart_type: "plotly" 또는 "matplotlib"
            
        Returns:
            base64 인코딩된 차트 이미지 또는 plotly HTML
        """
        if accounts is None:
            accounts = ['매출액', '영업이익', '당기순이익']
        
        # 데이터 추출
        chart_data = {}
        years = []
        
        for account in accounts:
            for item in financial_data:
                if item.get('base_display_name') == account:
                    values = []
                    item_years = []
                    
                    # 연도별 데이터 수집
                    year_data = [
                        ('전전기', item.get('bfefrmtrm_amount'), item.get('bfefrmtrm_dt')),
                        ('전기', item.get('frmtrm_amount'), item.get('frmtrm_dt')),
                        ('당기', item.get('thstrm_amount'), item.get('thstrm_dt'))
                    ]
                    
                    for period, amount, date in year_data:
                        if amount and date:
                            try:
                                year = date[:4]
                                value = float(str(amount).replace(',', ''))
                                values.append(value / 100000000)  # 억원 단위
                                item_years.append(year)
                            except:
                                continue
                    
                    if values:
                        chart_data[account] = values
                        if not years:
                            years = item_years
                    break
        
        if chart_type == "plotly":
            return self._create_plotly_trend_chart(chart_data, years, accounts)
        else:
            return self._create_matplotlib_trend_chart(chart_data, years, accounts)
    
    def _create_plotly_trend_chart(self, chart_data: Dict, years: List[str], accounts: List[str]) -> str:
        """Plotly 트렌드 차트 생성"""
        fig = go.Figure()
        
        for i, account in enumerate(accounts):
            if account in chart_data:
                fig.add_trace(go.Scatter(
                    x=years,
                    y=chart_data[account],
                    mode='lines+markers',
                    name=account,
                    line=dict(color=self.color_sequence[i % len(self.color_sequence)], width=3),
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
        
        return fig.to_html(include_plotlyjs='cdn', div_id="trend_chart")
    
    def _create_matplotlib_trend_chart(self, chart_data: Dict, years: List[str], accounts: List[str]) -> str:
        """Matplotlib 트렌드 차트 생성 (PDF/Excel용)"""
        plt.figure(figsize=(10, 6))
        
        for i, account in enumerate(accounts):
            if account in chart_data:
                plt.plot(years, chart_data[account], 
                        marker='o', linewidth=2, markersize=6, 
                        label=account, color=self.color_sequence[i % len(self.color_sequence)])
        
        plt.title('주요 재무지표 추이 (단위: 억원)', fontsize=14, fontweight='bold', pad=20)
        plt.xlabel('연도', fontsize=12)
        plt.ylabel('금액 (억원)', fontsize=12)
        plt.legend(loc='upper left')
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # base64 인코딩
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()
        
        return image_base64
    
    def create_ratio_chart(
        self, 
        ratios: Dict, 
        chart_type: str = "plotly"
    ) -> str:
        """
        재무비율 차트 생성
        
        Args:
            ratios: 재무비율 데이터
            chart_type: "plotly" 또는 "matplotlib"
            
        Returns:
            base64 인코딩된 차트 이미지 또는 plotly HTML
        """
        # 주요 비율 선택
        key_ratios = ['영업이익률', '순이익률', 'ROE', 'ROA']
        available_ratios = {k: v for k, v in ratios.items() if k in key_ratios}
        
        if not available_ratios:
            return ""
        
        if chart_type == "plotly":
            return self._create_plotly_ratio_chart(available_ratios)
        else:
            return self._create_matplotlib_ratio_chart(available_ratios)
    
    def _create_plotly_ratio_chart(self, ratios: Dict) -> str:
        """Plotly 비율 차트 생성"""
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=list(ratios.keys()),
            specs=[[{"type": "bar"}, {"type": "bar"}], 
                   [{"type": "bar"}, {"type": "bar"}]]
        )
        
        positions = [(1,1), (1,2), (2,1), (2,2)]
        
        for i, (ratio_name, values) in enumerate(ratios.items()):
            if i >= 4:  # 최대 4개까지
                break
            
            row, col = positions[i]
            years = ['전전기', '전기', '당기']
            ratio_values = [values.get('bfefrmtrm', 0), values.get('frmtrm', 0), values.get('thstrm', 0)]
            
            fig.add_trace(go.Bar(
                x=years,
                y=ratio_values,
                name=ratio_name,
                showlegend=False,
                marker_color=self.color_sequence[i % len(self.color_sequence)]
            ), row=row, col=col)
            
            fig.update_yaxis(title_text="(%)", row=row, col=col)
        
        fig.update_layout(
            title={
                'text': '주요 재무비율 비교',
                'x': 0.5,
                'font': {'size': 16}
            },
            height=500,
            template="plotly_white"
        )
        
        return fig.to_html(include_plotlyjs='cdn', div_id="ratio_chart")
    
    def _create_matplotlib_ratio_chart(self, ratios: Dict) -> str:
        """Matplotlib 비율 차트 생성"""
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle('주요 재무비율 비교', fontsize=14, fontweight='bold')
        
        axes = axes.flatten()
        years = ['전전기', '전기', '당기']
        
        for i, (ratio_name, values) in enumerate(ratios.items()):
            if i >= 4:
                break
            
            ratio_values = [values.get('bfefrmtrm', 0), values.get('frmtrm', 0), values.get('thstrm', 0)]
            
            bars = axes[i].bar(years, ratio_values, color=self.color_sequence[i % len(self.color_sequence)])
            axes[i].set_title(ratio_name, fontweight='bold')
            axes[i].set_ylabel('(%)')
            axes[i].grid(True, alpha=0.3)
            
            # 값 표시
            for bar, value in zip(bars, ratio_values):
                height = bar.get_height()
                axes[i].text(bar.get_x() + bar.get_width()/2., height,
                           f'{value:.1f}%', ha='center', va='bottom')
        
        plt.tight_layout()
        
        # base64 인코딩
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()
        
        return image_base64
    
    def create_comparison_chart(
        self, 
        companies_data: Dict,
        chart_type: str = "plotly"
    ) -> str:
        """
        복수 회사 비교 차트 생성
        
        Args:
            companies_data: 회사별 재무 데이터
            chart_type: "plotly" 또는 "matplotlib"
            
        Returns:
            base64 인코딩된 차트 이미지 또는 plotly HTML
        """
        # 주요 지표 추출
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
                            value = float(str(item.get('thstrm_amount', 0)).replace(',', '')) / 100000000  # 억원
                        except:
                            value = 0
                        break
                company_values.append(value)
            
            comparison_data[corp_data['corp_name']] = company_values
        
        if chart_type == "plotly":
            return self._create_plotly_comparison_chart(comparison_data, accounts, company_names)
        else:
            return self._create_matplotlib_comparison_chart(comparison_data, accounts, company_names)
    
    def _create_plotly_comparison_chart(self, comparison_data: Dict, accounts: List[str], company_names: List[str]) -> str:
        """Plotly 비교 차트 생성"""
        fig = go.Figure()
        
        for i, company in enumerate(company_names):
            fig.add_trace(go.Bar(
                name=company,
                x=accounts,
                y=comparison_data[company],
                marker_color=self.color_sequence[i % len(self.color_sequence)]
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
        
        return fig.to_html(include_plotlyjs='cdn', div_id="comparison_chart")
    
    def _create_matplotlib_comparison_chart(self, comparison_data: Dict, accounts: List[str], company_names: List[str]) -> str:
        """Matplotlib 비교 차트 생성"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        x = np.arange(len(accounts))
        width = 0.35 if len(company_names) == 2 else 0.25
        
        for i, company in enumerate(company_names):
            offset = (i - len(company_names)/2 + 0.5) * width
            bars = ax.bar(x + offset, comparison_data[company], width, 
                         label=company, color=self.color_sequence[i % len(self.color_sequence)])
            
            # 값 표시
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{height:.0f}', ha='center', va='bottom', fontsize=9)
        
        ax.set_title('회사별 주요 재무지표 비교 (단위: 억원)', fontweight='bold', pad=20)
        ax.set_xlabel('재무 지표')
        ax.set_ylabel('금액 (억원)')
        ax.set_xticks(x)
        ax.set_xticklabels(accounts)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # base64 인코딩
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()
        
        return image_base64
    
    def create_ratio_comparison_chart(
        self, 
        companies_data: Dict,
        chart_type: str = "plotly"
    ) -> str:
        """
        회사별 재무비율 비교 차트
        
        Args:
            companies_data: 회사별 재무 데이터
            chart_type: "plotly" 또는 "matplotlib"
            
        Returns:
            base64 인코딩된 차트 이미지 또는 plotly HTML
        """
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
        
        if chart_type == "plotly":
            return self._create_plotly_ratio_comparison_chart(comparison_data, key_ratios, company_names)
        else:
            return self._create_matplotlib_ratio_comparison_chart(comparison_data, key_ratios, company_names)
    
    def _create_plotly_ratio_comparison_chart(self, comparison_data: Dict, ratios: List[str], company_names: List[str]) -> str:
        """Plotly 비율 비교 차트 생성"""
        fig = go.Figure()
        
        for i, company in enumerate(company_names):
            fig.add_trace(go.Bar(
                name=company,
                x=ratios,
                y=comparison_data[company],
                marker_color=self.color_sequence[i % len(self.color_sequence)]
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
        
        return fig.to_html(include_plotlyjs='cdn', div_id="ratio_comparison_chart")
    
    def _create_matplotlib_ratio_comparison_chart(self, comparison_data: Dict, ratios: List[str], company_names: List[str]) -> str:
        """Matplotlib 비율 비교 차트 생성"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        x = np.arange(len(ratios))
        width = 0.35 if len(company_names) == 2 else 0.25
        
        for i, company in enumerate(company_names):
            offset = (i - len(company_names)/2 + 0.5) * width
            bars = ax.bar(x + offset, comparison_data[company], width, 
                         label=company, color=self.color_sequence[i % len(self.color_sequence)])
            
            # 값 표시
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{height:.1f}%', ha='center', va='bottom', fontsize=9)
        
        ax.set_title('회사별 주요 재무비율 비교', fontweight='bold', pad=20)
        ax.set_xlabel('재무 비율')
        ax.set_ylabel('비율 (%)')
        ax.set_xticks(x)
        ax.set_xticklabels(ratios)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # base64 인코딩
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()
        
        return image_base64