from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, Flowable
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
import plotly.io as pio
import io
import os
from datetime import datetime

# BRAND COLORS
EMERALD = colors.HexColor("#10B981")
DARK_TEAL = colors.HexColor("#113229")
GRAY_TEXT = colors.HexColor("#64748b")
SF_BG = colors.HexColor("#F8FAFC")

class CorporateReport:
    def __init__(self, year, data):
        self.year = year
        self.data = data # Contains region, age, month, income keys
        self.styles = getSampleStyleSheet()
        self.setup_styles()

    def setup_styles(self):
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            fontName='Helvetica-Bold',
            fontSize=34,
            textColor=EMERALD,
            alignment=1, # Center
            spaceAfter=20
        ))
        self.styles.add(ParagraphStyle(
            name='ReportSubtitle',
            fontName='Helvetica',
            fontSize=18,
            textColor=GRAY_TEXT,
            alignment=1,
            letterSpacing=2,
            spaceAfter=50
        ))
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=DARK_TEAL,
            alignment=0,
            spaceAfter=15
        ))
        self.styles.add(ParagraphStyle(
            name='AnalysisBody',
            fontName='Helvetica',
            fontSize=11,
            textColor=colors.HexColor("#334155"),
            leading=16,
            alignment=4, # Justified
            spaceAfter=15
        ))
        self.styles.add(ParagraphStyle(
            name='TOCItem',
            fontName='Helvetica',
            fontSize=14,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=15
        ))
        self.styles.add(ParagraphStyle(
            name='SectionHeaderCentered',
            parent=self.styles['SectionHeader'],
            alignment=1, # Center
            spaceAfter=30
        ))

    def draw_header_footer(self, canvas, doc):
        canvas.saveState()
        # Header (Positioned well above the top margin)
        canvas.setFont('Helvetica-Bold', 10)
        canvas.setFillColor(EMERALD)
        canvas.drawString(inch, 11.4*inch, "TOURZEN INTELLIGENCE")
        canvas.setFont('Helvetica', 10)
        canvas.setFillColor(GRAY_TEXT)
        canvas.drawRightString(8.5*inch - inch, 11.4*inch, f"Annual Forecast {self.year}")
        canvas.setStrokeColor(colors.HexColor("#f1f5f9"))
        canvas.line(inch, 11.3*inch, 8.5*inch - inch, 11.3*inch)

        # Footer
        canvas.setFont('Helvetica-Bold', 10)
        canvas.setFillColor(GRAY_TEXT)
        canvas.drawString(inch, 0.5*inch, f"PAGE {doc.page:02d}")
        canvas.drawRightString(8.5*inch - inch, 0.5*inch, "Confidential - TourZen Advisory Board")
        canvas.restoreState()

    def get_plotly_image(self, fig_data, width=550, height=300):
        # fig_data can be a dict (from Plotly Figure)
        # Note: kaleido must be installed
        img_bytes = pio.to_image(fig_data, format='png', width=width, height=height, scale=2)
        return Image(io.BytesIO(img_bytes), width=5.5*inch, height=3*inch)

    def create_table(self, obj, col1, col2):
        # For simple 2-col tables
        table_data = [[col1, col2]]
        for k, v in obj.items():
            table_data.append([k, f"{int(v):,}"])
        
        t = Table(table_data, colWidths=[3*inch, 2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), EMERALD),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
        ]))
        return t

    def create_income_table(self, data_list):
        # 5-col table
        headers = ["Month", "Arrivals", "Avg Val", "Dur", "Income (Mn)"]
        table_data = [headers]
        for row in data_list:
            table_data.append([
                row["Month"],
                f"{int(row['Number of tourist arrivals']):,}",
                f"${row['Average value of the Month']:.2f}",
                f"{row['Average duration of the Month']:.1f}",
                f"${row['Total value (USD Mn)']:.1f}M"
            ])
        
        t = Table(table_data, colWidths=[1*inch, 1*inch, 1*inch, 1*inch, 1.2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), EMERALD),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
        ]))
        return t

    def build(self, output_path):
        # Increased top margin significantly to 1.5 inch to prevent any clashing with wrapped headers
        doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=inch, leftMargin=inch, topMargin=1.5*inch, bottomMargin=inch)
        story = []

        # PAGE 1: COVER
        story.append(Spacer(1, 1.5*inch))
        
        # Draw Vector Map Pin (Approximate with Path/drawing)
        # Using a stylized paragraph with a symbol if possible, 
        # but better to use a dedicated ParagraphStyle for the icon if I had a font.
        # Since I'm using Platypus, I'll use a placeholder or draw it.
        # Let's use a very large stylized "V" or similar? No, I'll draw it on the canvas
        # for the first page specifically using a Flowable.

        class MapPin(Flowable):
            def __init__(self, width=500, height=80):
                super().__init__()
                self.width = width
                self.height = height

            def wrap(self, availWidth, availHeight):
                return self.width, self.height

            def draw(self):
                self.canv.saveState()
                # Use total available width to truly center
                self.canv.translate(3.1*inch, 10) 
                self.canv.setFillColor(EMERALD)
                # Draw Pin Circle
                self.canv.circle(0, 40, 25, fill=1, stroke=0)
                # Draw Pin Point (Triangle)
                p = self.canv.beginPath()
                p.moveTo(-22, 28)
                p.lineTo(0, -10)
                p.lineTo(22, 28)
                p.close()
                self.canv.drawPath(p, fill=1, stroke=0)
                # Draw Inner White Circle
                self.canv.setFillColor(colors.white)
                self.canv.circle(0, 40, 8, fill=1, stroke=0)
                self.canv.restoreState()

        story.append(MapPin())
        story.append(Spacer(1, 0.8*inch))
        
        # Theme: Everything Emerald and Centered
        story.append(Paragraph("TourZen", self.styles['ReportTitle']))
        story.append(Spacer(1, 0.4*inch))
        
        cover_body_style = ParagraphStyle(
            name='CoverBody',
            fontName='Helvetica-Bold',
            fontSize=28,
            textColor=EMERALD,
            alignment=1,
            spaceAfter=20
        )
        
        story.append(Paragraph("Annual Tourism Forecast", cover_body_style))
        story.append(Paragraph(f"Year {self.year}", cover_body_style))
        story.append(PageBreak())

        # PAGE 2: TOC
        story.append(Paragraph("1. TABLE OF CONTENTS", self.styles['SectionHeader']))
        story.append(Spacer(1, 0.3*inch))
        toc = [
            ("Introduction: Sri Lankan Tourism Overview", "03"),
            ("Regional Market Breakdown", "04"),
            ("Demographic Persona Analysis", "05"),
            ("Monthly Seasonality Forecast", "06"),
            ("Economic Impact & Income Predictions", "07"),
            ("Strategic Conclusions", "08")
        ]
        for item, pg in toc:
            story.append(Paragraph(f"{item} . . . . . . . . . . . . {pg}", self.styles['TOCItem']))
        story.append(PageBreak())

        # PAGE 3: INTRODUCTION
        story.append(Paragraph("2. INDUSTRY INTRODUCTION", self.styles['SectionHeader']))
        story.append(Spacer(1, 0.2*inch)) # Space between topic and paragraph
        intro_text = f"The Sri Lankan tourism industry is entering its most transformative decade. As of {self.year}, our Machine Learning models predict a transition from a pure 'recovery' state to a 'premium-value' market. Sri Lanka’s unique geography—blending mist-shrouded highlands, ancient citadels, and golden coastlines—is being increasingly sought after by 'Experience Seekers' from both Western and Asian markets."
        story.append(Paragraph(intro_text, self.styles['AnalysisBody']))
        intro_text_2 = "Our forecasts suggest that the integration of digital nomad hubs and eco-sanctuaries has significantly stabilized the traditional 'off-peak' months, creating a more resilient and sustainable economic model for local communities. This report provides a detailed data-driven outlook to guide capacity planning and strategic investment for the upcoming fiscal year."
        story.append(Paragraph(intro_text_2, self.styles['AnalysisBody']))
        story.append(PageBreak())

        # DATA ANALYTICS FOR DYNAMIC TEXT
        top_region = max(self.data['region'], key=self.data['region'].get)
        total_arrivals = sum(self.data['month'].values())
        top_age = max(self.data['age'], key=self.data['age'].get)
        peak_income_row = max(self.data['income'], key=lambda x: x['Total value (USD Mn)'])
        total_income = sum(x['Total value (USD Mn)'] for x in self.data['income'])

        # PAGE 4: REGION Breakdown
        story.append(Paragraph("3. REGION MARKET BREAKDOWN", self.styles['SectionHeader']))
        fig_region = {
            'data': [{'labels': list(self.data['region'].keys()), 'values': list(self.data['region'].values()), 'type': 'pie', 'marker': {'colors': ["#10B981", "#34D399", "#059669", "#6EE7B7", "#A7F3D0"]}}]
        }
        story.append(self.get_plotly_image(fig_region))
        story.append(Spacer(1, 0.2*inch))
        story.append(self.create_table(self.data['region'], "Source Region", "Arrivals"))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("Trend Interpretation:", self.styles['Heading4']))
        region_dynamic = f"For the year {self.year}, {top_region} is projected to be the primary driver of tourism in Sri Lanka, contributing significantly to the total expected arrivals of {int(total_arrivals):,}. This justifies continued focus on {top_region}-centric marketing campaigns."
        story.append(Paragraph(region_dynamic, self.styles['AnalysisBody']))
        story.append(PageBreak())

        # PAGE 5: DEMOGRAPHICS
        story.append(Paragraph("4. DEMOGRAPHIC PERSONA ANALYSIS", self.styles['SectionHeader']))
        fig_age = {
            'data': [{'x': list(self.data['age'].values()), 'y': list(self.data['age'].keys()), 'type': 'bar', 'orientation': 'h', 'marker': {'color': '#10B981'}}]
        }
        story.append(self.get_plotly_image(fig_age))
        story.append(Spacer(1, 0.2*inch))
        story.append(self.create_table(self.data['age'], "Age Category", "Arrivals"))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("Trend Interpretation:", self.styles['Heading4']))
        age_dynamic = f"The {top_age} demographic is the most dominant segment in {self.year}. This highlights the importance of digital-first experiences and adventure-based tourism that resonates with this active traveler class."
        story.append(Paragraph(age_dynamic, self.styles['AnalysisBody']))
        story.append(PageBreak())

        # PAGE 6: MONTHLY
        story.append(Paragraph("5. MONTHLY SEASONALITY FORECAST", self.styles['SectionHeader']))
        fig_month = {
            'data': [{'x': list(self.data['month'].keys()), 'y': list(self.data['month'].values()), 'type': 'bar', 'marker': {'color': '#34D399'}}]
        }
        story.append(self.get_plotly_image(fig_month))
        story.append(Spacer(1, 0.2*inch))
        story.append(self.create_table(self.data['month'], "Month", "Arrivals"))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("Trend Interpretation:", self.styles['Heading4']))
        month_dynamic = f"Peak seasonal demand is expected in {peak_income_row['Month']}, allowing hospitality providers to optimize staffing and inventory. The {self.year} data shows a clear trend towards a more balanced annual distribution."
        story.append(Paragraph(month_dynamic, self.styles['AnalysisBody']))
        story.append(PageBreak())

        # PAGE 7: INCOME
        story.append(Paragraph("6. ECONOMIC IMPACT & INCOME PREDICTION", self.styles['SectionHeader']))
        income_months = [x["Month"][:3] for x in self.data['income']]
        income_vals = [x["Total value (USD Mn)"] for x in self.data['income']]
        fig_income = {
            'data': [{'x': income_months, 'y': income_vals, 'type': 'scatter', 'mode': 'lines+markers', 'line': {'color': '#10B981'}, 'fill': 'tozeroy'}]
        }
        story.append(self.get_plotly_image(fig_income))
        story.append(Spacer(1, 0.2*inch))
        story.append(self.create_income_table(self.data['income']))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("Trend Interpretation:", self.styles['Heading4']))
        income_dynamic = f"Total projected tourism income for {self.year} is estimated at ${total_income:,.1f} Million USD. The highest revenue yield month is anticipated to be {peak_income_row['Month']} with a contribution of ${peak_income_row['Total value (USD Mn)']:.1f}M."
        story.append(Paragraph(income_dynamic, self.styles['AnalysisBody']))
        story.append(PageBreak())

        # PAGE 8: CONCLUSION
        story.append(Paragraph("7. STRATEGIC CONCLUSIONS", self.styles['SectionHeader']))
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph(f"Our analysis for the fiscal year {self.year} concludes that Sri Lanka is moving towards a high-value tourism economy. With a projected {int(total_arrivals):,} arrivals generating ${total_income:,.1f}M in revenue, strategic focus should shift towards infrastructure quality.", self.styles['AnalysisBody']))
        
        conclusion_points = [
            f"<b>Primary Growth Segment:</b> Focus on the {top_age} group which leads with {self.data['age'][top_age]:,} arrivals.",
            f"<b>Regional Strategy:</b> Allocate 40% of the marketing budget to the {top_region} corridor to sustain leadership.",
            f"<b>Financial KPI:</b> Target an average monthly revenue of ${(total_income/12):.1f}M across the {self.year} calendar year."
        ]
        for p in conclusion_points:
            story.append(Paragraph(f"&bull; {p}", self.styles['AnalysisBody']))

        story.append(Spacer(1, 1*inch))
        story.append(Paragraph("END OF REPORT", self.styles['ReportSubtitle']))

        doc.build(story, onFirstPage=self.draw_header_footer, onLaterPages=self.draw_header_footer)
