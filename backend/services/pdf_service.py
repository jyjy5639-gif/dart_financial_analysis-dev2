from io import BytesIO
from datetime import datetime
from typing import Dict, List, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import base64
from pathlib import Path
from backend.services.chart_service import ChartService


class PDFService:
    """AI 브리핑 PDF 생성 서비스 (차트 포함) - 모든 환경 지원"""
    
    def __init__(self):
        self._setup_fonts()
        self.styles = self._create_styles()
        self.chart_service = ChartService()
    
    def _setup_fonts(self):
        """한글 폰트 설정 - Windows/Linux/Mac/클라우드 모두 지원"""
        try:
            # 1. 프로젝트 내 폰트 확인 (모든 환경에서 작동)
            project_root = Path(__file__).parent.parent.parent
            project_font = project_root / "fonts" / "NotoSansKR-Regular.otf"
            
            if project_font.exists():
                pdfmetrics.registerFont(TTFont('NotoSansKR', str(project_font)))
                print(f"✅ PDFService 폰트 로드 (프로젝트): {project_font}")
                return
            
            print(f"프로젝트 폰트 찾을 수 없음: {project_font}")
            
            # 2. Windows 경로 시도
            windows_paths = [
                "C:/Windows/Fonts/NotoSansKR-Regular.otf",
                "C:/Windows/Fonts/NotoSansKR-Medium.otf",
            ]
            for path in windows_paths:
                if os.path.exists(path):
                    pdfmetrics.registerFont(TTFont('NotoSansKR', path))
                    print(f"✅ PDFService 폰트 로드 (Windows): {path}")
                    return
            
            # 3. Linux 경로 시도
            linux_paths = [
                "/usr/share/fonts/opentype/noto/NotoSansKR-Regular.otf",
                "/usr/share/fonts/noto/NotoSansKR-Regular.otf",
                "/usr/share/fonts/opentype/noto-cjk/NotoSansCJKkr-Regular.otf",
            ]
            for path in linux_paths:
                if os.path.exists(path):
                    pdfmetrics.registerFont(TTFont('NotoSansKR', path))
                    print(f"✅ PDFService 폰트 로드 (Linux): {path}")
                    return
            
            # 4. macOS 경로 시도
            mac_paths = [
                "/Library/Fonts/NotoSansKR-Regular.otf",
                f"{os.path.expanduser('~')}/Library/Fonts/NotoSansKR-Regular.otf",
            ]
            for path in mac_paths:
                if os.path.exists(path):
                    pdfmetrics.registerFont(TTFont('NotoSansKR', path))
                    print(f"✅ PDFService 폰트 로드 (macOS): {path}")
                    return
            
            print("⚠️ 경고: NotoSansKR 폰트를 찾을 수 없습니다.")
            print(f"   프로젝트 폰트 경로: {project_font}")
            
        except Exception as e:
            print(f"❌ PDFService 폰트 설정 오류: {e}")
    
    def _create_styles(self):
        """PDF 스타일 생성"""
        styles = getSampleStyleSheet()
        
        # 제목 스타일
        styles.add(ParagraphStyle(
            name='KoreanTitle',
            parent=styles['Title'],
            fontName='NotoSansKR',
            fontSize=18,
            spaceAfter=20,
            textColor=HexColor('#1f4e79'),
            alignment=TA_CENTER
        ))
        
        # 부제목 스타일
        styles.add(ParagraphStyle(
            name='KoreanHeading',
            parent=styles['Heading2'],
            fontName='NotoSansKR',
            fontSize=14,
            spaceAfter=12,
            textColor=HexColor('#2c5282'),
            alignment=TA_LEFT
        ))
        
        # 본문 스타일
        styles.add(ParagraphStyle(
            name='KoreanBody',
            parent=styles['Normal'],
            fontName='NotoSansKR',
            fontSize=10,
            leading=14,
            spaceAfter=8,
            alignment=TA_JUSTIFY,
            wordWrap='LTR'
        ))
        
        # 메타데이터 스타일
        styles.add(ParagraphStyle(
            name='Metadata',
            parent=styles['Normal'],
            fontName='NotoSansKR',
            fontSize=9,
            textColor=HexColor('#666666'),
            alignment=TA_RIGHT
        ))
        
        return styles
    
    def create_briefing_pdf(
        self,
        briefing_text: str,
        company_info: Dict,
        financial_summary: Optional[Dict] = None,
        llm_provider: str = "AI",
        analysis_style: str = "standard",
        include_charts: bool = True
    ) -> BytesIO:
        """
        AI 브리핑 PDF 생성 (차트 포함)
        
        Args:
            briefing_text: AI 브리핑 텍스트
            company_info: 회사 정보
            financial_summary: 재무 요약 정보 (선택)
            llm_provider: 사용한 LLM 제공자
            analysis_style: 분석 스타일
            include_charts: 차트 포함 여부
            
        Returns:
            BytesIO: PDF 파일 바이너리
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # 문서 내용
        story = []
        
        # 헤더 정보
        story.extend(self._create_header(company_info, llm_provider, analysis_style))
        
        # 차트 추가
        if include_charts and financial_summary:
            story.extend(self._create_charts_section(company_info, financial_summary))
        
        # 재무 요약 (있는 경우)
        if financial_summary:
            story.extend(self._create_financial_summary(financial_summary))
        
        # AI 브리핑 내용
        story.extend(self._create_briefing_content(briefing_text))
        
        # 푸터
        story.extend(self._create_footer())
        
        # PDF 생성
        doc.build(story)
        buffer.seek(0)
        
        return buffer
    
    def _create_charts_section(self, company_info: Dict, financial_summary: Dict) -> List:
        """차트 섹션 생성"""
        story = []
        
        try:
            # ✅ 수정: 제목 텍스트 정제
            visual_analysis_title = self._sanitize_text_for_pdf("시각적 분석")
            story.append(Paragraph(visual_analysis_title, self.styles['KoreanHeading']))
            
            # 단일 회사인 경우
            if 'companies' not in company_info or len(company_info.get('companies', [])) <= 1:
                # 단일 회사 차트 생성
                if 'key_metrics' in financial_summary:
                    # 재무 데이터를 차트 형식으로 변환
                    financial_items = self._convert_summary_to_chart_format(financial_summary)
                    
                    if financial_items:
                        # 트렌드 차트
                        trend_image = self.chart_service.create_trend_chart(
                            financial_items, 
                            chart_type="matplotlib"
                        )
                        
                        if trend_image:
                            chart_img = self._create_image_from_base64(trend_image)
                            if chart_img:
                                story.append(chart_img)
                                story.append(Spacer(1, 0.2*inch))
            
            else:
                # 복수 회사 비교 차트
                companies_data = self._convert_companies_to_chart_format(
                    company_info.get('companies', []), 
                    financial_summary
                )
                
                if companies_data:
                    # 비교 차트
                    comparison_image = self.chart_service.create_comparison_chart(
                        companies_data,
                        chart_type="matplotlib"
                    )
                    
                    if comparison_image:
                        chart_img = self._create_image_from_base64(comparison_image)
                        if chart_img:
                            story.append(chart_img)
                            story.append(Spacer(1, 0.2*inch))
                            
        except Exception as e:
            print(f"차트 생성 실패: {e}")
            # 차트 생성에 실패해도 PDF 생성은 계속
        
        return story
    
    def _create_image_from_base64(self, image_base64: str) -> Optional[Image]:
        """base64 이미지를 ReportLab Image로 변환 (BytesIO 사용)"""
        try:
            # base64 디코딩
            image_data = base64.b64decode(image_base64)
            
            # BytesIO를 사용하여 메모리에서 처리
            image_stream = BytesIO(image_data)
            
            # ReportLab Image 생성
            img = Image(image_stream)
            img.drawWidth = 15*cm  # 너비 조정
            img.drawHeight = 10*cm  # 높이 조정
            
            return img
                    
        except Exception as e:
            print(f"이미지 변환 실패: {e}")
            return None
    
    def _convert_summary_to_chart_format(self, financial_summary: Dict) -> List[Dict]:
        """재무 요약을 차트 형식으로 변환"""
        financial_items = []
        
        if 'key_metrics' in financial_summary:
            for metric in financial_summary['key_metrics']:
                item = {
                    'base_display_name': metric['name'],
                    'display_name': metric['name'],
                    'thstrm_amount': self._parse_amount(metric.get('current', '0')),
                    'thstrm_dt': '20231231',
                    'frmtrm_amount': self._parse_amount(metric.get('previous', '0')),
                    'frmtrm_dt': '20221231'
                }
                financial_items.append(item)
        
        return financial_items
    
    def _convert_companies_to_chart_format(self, companies: List[Dict], financial_summary: Dict) -> Dict:
        """복수 회사 정보를 차트 형식으로 변환"""
        companies_data = {}
        
        for idx, company in enumerate(companies):
            company_name = company.get('corp_name', f'회사{idx+1}')
            
            # 간단한 더미 데이터 생성 (실제로는 financial_summary에서 추출)
            financial_items = [
                {
                    'base_display_name': '매출액',
                    'display_name': '매출액',
                    'thstrm_amount': 1000000000,  # 더미 데이터
                    'thstrm_dt': '20231231'
                }
            ]
            
            companies_data[f'corp_{idx}'] = {
                'corp_name': company_name,
                'financial_data': financial_items,
                'ratios': {}
            }
        
        return companies_data
    
    def _parse_amount(self, amount_str: str) -> float:
        """금액 문자열을 숫자로 변환"""
        try:
            if isinstance(amount_str, str):
                amount_str = amount_str.replace(',', '').replace('원', '').replace(' ', '')
            return float(amount_str) if amount_str else 0
        except:
            return 0
    
    def _create_header(self, company_info: Dict, llm_provider: str, analysis_style: str) -> List:
        """PDF 헤더 생성"""
        story = []
        
        # 제목
        if len(company_info.get('companies', [])) > 1:
            # 복수 회사 비교
            company_names = [comp.get('corp_name', '') for comp in company_info['companies']]
            title = f"재무 분석 리포트 - {', '.join(company_names)} 비교"
        else:
            # 단일 회사
            corp_name = company_info.get('corp_name', '회사명')
            stock_code = company_info.get('stock_code', '')
            title = f"재무 분석 리포트 - {corp_name}"
            if stock_code and stock_code != 'N/A':
                title += f" ({stock_code})"
        
        # ✅ 수정: 제목 텍스트 정제
        title = self._sanitize_text_for_pdf(title)
        story.append(Paragraph(title, self.styles['KoreanTitle']))
        story.append(Spacer(1, 0.3*inch))
        
        # 메타데이터 테이블
        # ✅ 수정: 모든 텍스트 정제
        metadata = [
            [
                self._sanitize_text_for_pdf('생성일시'),
                self._sanitize_text_for_pdf(datetime.now().strftime('%Y년 %m월 %d일 %H:%M'))
            ],
            [
                self._sanitize_text_for_pdf('분석 엔진'),
                self._sanitize_text_for_pdf(str(llm_provider))
            ],
            [
                self._sanitize_text_for_pdf('분석 스타일'),
                self._sanitize_text_for_pdf(str(analysis_style))
            ],
        ]
        
        meta_table = Table(metadata, colWidths=[3*cm, 8*cm])
        meta_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'NotoSansKR'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
            ('BACKGROUND', (0, 0), (0, -1), HexColor('#f8f9fa')),
        ]))
        
        story.append(meta_table)
        story.append(Spacer(1, 0.3*inch))
        story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#e0e0e0')))
        story.append(Spacer(1, 0.2*inch))
        
        return story
    
    def _create_financial_summary(self, financial_summary: Dict) -> List:
        """재무 요약 테이블 생성"""
        story = []
        
        # ✅ 수정: 제목 텍스트 정제
        financial_summary_title = self._sanitize_text_for_pdf("재무 현황 요약")
        story.append(Paragraph(financial_summary_title, self.styles['KoreanHeading']))
        
        # 주요 지표 테이블
        if 'key_metrics' in financial_summary:
            # ✅ 수정: 테이블 헤더 정제
            metrics_data = [
                [
                    self._sanitize_text_for_pdf('항목'),
                    self._sanitize_text_for_pdf('당기'),
                    self._sanitize_text_for_pdf('전기'),
                    self._sanitize_text_for_pdf('증감률')
                ]
            ]
            
            for metric in financial_summary['key_metrics']:
                # ✅ 수정: 테이블 내용도 정제
                metrics_data.append([
                    self._sanitize_text_for_pdf(str(metric['name'])),
                    self._sanitize_text_for_pdf(str(metric.get('current', '-'))),
                    self._sanitize_text_for_pdf(str(metric.get('previous', '-'))),
                    self._sanitize_text_for_pdf(str(metric.get('change_rate', '-')))
                ])
            
            metrics_table = Table(metrics_data, colWidths=[4*cm, 3*cm, 3*cm, 2*cm])
            metrics_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'NotoSansKR'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#4472c4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
            ]))
            
            story.append(metrics_table)
            story.append(Spacer(1, 0.2*inch))
        
        return story
    
    def _sanitize_text_for_pdf(self, text: str) -> str:
        """텍스트를 PDF에 안전하게 변환 (HTML 태그 제거)"""
        import re
        
        # 문자열로 변환 (None이나 다른 타입일 수 있음)
        text = str(text) if text is not None else ""
        
        # XML/HTML 특수 문자 이스케이프
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        
        return text
    
    def _convert_markdown_to_reportlab(self, text: str) -> str:
        """마크다운을 ReportLab 형식으로 변환"""
        import re
        
        # 먼저 텍스트 정제 (XML 특수문자 제외)
        text = self._sanitize_text_for_pdf(text)
        
        # ### 제목 제거 (따로 처리)
        text = re.sub(r'^###\s+', '', text)
        text = re.sub(r'^##\s+', '', text)
        text = re.sub(r'^#\s+', '', text)
        
        # 마크다운 테이블 제거 (| 로 시작하는 라인)
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # 테이블 헤더나 구분선은 제거
            if line.strip().startswith('|') or line.strip().startswith('---'):
                continue
            cleaned_lines.append(line)
        text = '\n'.join(cleaned_lines)
        
        # ** 굵은 글씨 -> <b> 태그
        # **텍스트** 패턴을 찾아서 변환
        text = re.sub(r'\*\*([^\*]+)\*\*', r'<b>\1</b>', text)
        
        # * 리스트 -> 불릿 포인트 (저절로 처리)
        # - 리스트 -> 불릿 포인트
        text = re.sub(r'^\s*[-\*]\s+', '• ', text, flags=re.MULTILINE)
        
        return text
    
    def _create_briefing_content(self, briefing_text: str) -> List:
        """AI 브리핑 내용 생성 (마크다운 처리 개선)"""
        import re
        story = []
        
        # ✅ 수정: 제목 텍스트 정제
        ai_report_title = self._sanitize_text_for_pdf("AI 분석 리포트")
        story.append(Paragraph(ai_report_title, self.styles['KoreanHeading']))
        
        # 텍스트를 줄 단위로 분할하여 처리
        lines = briefing_text.split('\n')
        
        current_paragraph = []
        
        for line in lines:
            line = line.strip()
            
            # 빈 줄이면 현재 문단 종료
            if not line:
                if current_paragraph:
                    para_text = ' '.join(current_paragraph)
                    converted_text = self._convert_markdown_to_reportlab(para_text)
                    
                    if converted_text.strip():
                        try:
                            story.append(Paragraph(converted_text, self.styles['KoreanBody']))
                            story.append(Spacer(1, 0.1*inch))
                        except Exception as e:
                            # 파싱 실패 시 텍스트만 추출
                            plain_text = re.sub(r'<[^>]+>', '', converted_text)
                            story.append(Paragraph(plain_text, self.styles['KoreanBody']))
                            story.append(Spacer(1, 0.1*inch))
                    
                    current_paragraph = []
                continue
            
            # ### 제목 처리
            if line.startswith('###'):
                # 현재 문단 먼저 출력
                if current_paragraph:
                    para_text = ' '.join(current_paragraph)
                    converted_text = self._convert_markdown_to_reportlab(para_text)
                    if converted_text.strip():
                        try:
                            story.append(Paragraph(converted_text, self.styles['KoreanBody']))
                        except:
                            plain_text = re.sub(r'<[^>]+>', '', converted_text)
                            story.append(Paragraph(plain_text, self.styles['KoreanBody']))
                    current_paragraph = []
                
                # 제목 출력
                heading_text = line.replace('###', '').strip()
                heading_text = self._sanitize_text_for_pdf(heading_text)
                story.append(Spacer(1, 0.15*inch))
                story.append(Paragraph(f"<b>{heading_text}</b>", self.styles['KoreanHeading']))
                continue
            
            # ## 제목 처리
            if line.startswith('##'):
                if current_paragraph:
                    para_text = ' '.join(current_paragraph)
                    converted_text = self._convert_markdown_to_reportlab(para_text)
                    if converted_text.strip():
                        try:
                            story.append(Paragraph(converted_text, self.styles['KoreanBody']))
                        except:
                            plain_text = re.sub(r'<[^>]+>', '', converted_text)
                            story.append(Paragraph(plain_text, self.styles['KoreanBody']))
                    current_paragraph = []
                
                heading_text = line.replace('##', '').strip()
                heading_text = self._sanitize_text_for_pdf(heading_text)
                story.append(Spacer(1, 0.2*inch))
                story.append(Paragraph(f"<b>{heading_text}</b>", self.styles['KoreanHeading']))
                continue
            
            # 테이블 라인 무시 (| 로 시작)
            if line.startswith('|') or line.startswith('---'):
                continue
            
            # 일반 텍스트 라인
            current_paragraph.append(line)
        
        # 마지막 문단 처리
        if current_paragraph:
            para_text = ' '.join(current_paragraph)
            converted_text = self._convert_markdown_to_reportlab(para_text)
            if converted_text.strip():
                try:
                    story.append(Paragraph(converted_text, self.styles['KoreanBody']))
                    story.append(Spacer(1, 0.1*inch))
                except Exception as e:
                    plain_text = re.sub(r'<[^>]+>', '', converted_text)
                    story.append(Paragraph(plain_text, self.styles['KoreanBody']))
                    story.append(Spacer(1, 0.1*inch))
        
        return story
    
    def _create_footer(self) -> List:
        """PDF 푸터 생성"""
        story = []
        
        story.append(Spacer(1, 0.3*inch))
        story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#e0e0e0')))
        story.append(Spacer(1, 0.1*inch))
        
        # ✅ 수정: 푸터 텍스트도 정제
        footer_text = self._sanitize_text_for_pdf("※ 본 분석 리포트는 AI에 의해 자동 생성된 것으로, 투자 결정의 참고자료로만 활용하시기 바랍니다.")
        story.append(Paragraph(footer_text, self.styles['Metadata']))
        
        return story
    
    def create_comparison_pdf(
        self,
        briefing_text: str,
        companies: List[Dict],
        comparison_data: Optional[Dict] = None,
        llm_provider: str = "AI"
    ) -> BytesIO:
        """
        복수 회사 비교 PDF 생성 (차트 포함)
        
        Args:
            briefing_text: AI 비교 브리핑 텍스트
            companies: 회사 정보 리스트
            comparison_data: 비교 데이터
            llm_provider: 사용한 LLM 제공자
            
        Returns:
            BytesIO: PDF 파일 바이너리
        """
        company_info = {'companies': companies}
        
        return self.create_briefing_pdf(
            briefing_text=briefing_text,
            company_info=company_info,
            financial_summary=comparison_data,
            llm_provider=llm_provider,
            analysis_style="comparison",
            include_charts=True
        )