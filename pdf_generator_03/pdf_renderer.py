from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import inch
from reportlab.lib import colors
from typing import List
from base_module import OutputModule

class PDFRenderer:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.styles = self._create_styles()
    
    def _create_styles(self):
        base_styles = getSampleStyleSheet()
        
        styles = {
            'title': ParagraphStyle(
                'Title',
                parent=base_styles['Heading1'],
                fontSize=12,
                textColor='black',
                alignment=TA_CENTER,
                spaceAfter=8,
                spaceBefore=0
            ),
            'section_header': ParagraphStyle(
                'SectionHeader',
                parent=base_styles['Heading2'],
                fontSize=10,
                textColor='black',
                alignment=TA_LEFT,
                spaceAfter=5,
                fontName='Helvetica-Bold'
            ),
            'context': ParagraphStyle(
                'Context',
                parent=base_styles['Normal'],
                fontSize=7,
                alignment=TA_LEFT,
                spaceAfter=3
            ),
            'bluf': ParagraphStyle(
                'BLUF',
                parent=base_styles['Normal'],
                fontSize=7,
                alignment=TA_LEFT,
                spaceAfter=3
            ),
            'interpretation': ParagraphStyle(
                'Interpretation',
                parent=base_styles['Normal'],
                fontSize=7,
                alignment=TA_LEFT,
                spaceAfter=3
            )
        }
        return styles
    
    def create_monthly_report(self, country_code: str, country_name: str, 
                            target_month: int, target_year: int, 
                            modules: List[OutputModule], 
                            forecast_data, historical_data) -> Path:
        
        month_names = {12: "December", 3: "March", 9: "September"}
        month_name = month_names[target_month]
        
        output_file = self.output_dir / f"{country_code}_forecast_{month_name.lower()}_{target_year}.pdf"
        doc = SimpleDocTemplate(
            str(output_file), 
            pagesize=landscape(LETTER),
            topMargin=0.15*inch,
            bottomMargin=0.15*inch,
            leftMargin=0.3*inch,
            rightMargin=0.3*inch
        )
        
        story = []
        
        story.append(Paragraph(f"{country_name}, {month_name} {target_year}", self.styles['title']))
        
        summary_content = []
        section1_content = []
        section2_content = []
        section3_content = []
        
        try:
            from bluf_generator import BLUFGenerator
            bluf_generator = BLUFGenerator()
            
            bluf_text = bluf_generator.generate_bluf(
                country_code, target_month, target_year,
                forecast_data, historical_data, None
            )
            
            summary_content.append(Paragraph("Summary", self.styles['section_header']))
            summary_content.append(Paragraph(bluf_text, self.styles['bluf']))
            
        except Exception as e:
            print(f"Error generating BLUF: {e}")
            summary_content.append(Paragraph("Summary", self.styles['section_header']))
            summary_content.append(Paragraph("BLUF generation failed", self.styles['bluf']))
        
        if len(modules) > 0:
            module = modules[0]
            section1_content.append(Paragraph("Violence trend", self.styles['section_header']))
            section1_content.append(Paragraph(module.get_context(), self.styles['context']))
            
            content_path = module.generate_content(country_code, forecast_data, historical_data, self.output_dir)
            if content_path and content_path.exists():
                section1_content.append(Image(str(content_path), width=4*inch, height=2*inch))
            
            interpretation = module.get_interpretation(country_code, forecast_data, historical_data)
            if interpretation:
                section1_content.append(Paragraph(interpretation, self.styles['interpretation']))
        
        if len(modules) > 1:
            module = modules[1]
            section2_content.append(Paragraph("Structural risk factors", self.styles['section_header']))
            section2_content.append(Paragraph(module.get_context(), self.styles['context']))
            
            content_path = module.generate_content(country_code, forecast_data, historical_data, self.output_dir)
            if content_path and content_path.exists():
                section2_content.append(Image(str(content_path), width=4*inch, height=2*inch))
            
            interpretation = module.get_interpretation(country_code, forecast_data, historical_data)
            if interpretation:
                section2_content.append(Paragraph(interpretation, self.styles['interpretation']))
        
        if len(modules) > 2:
            module = modules[2]
            section3_content.append(Paragraph("Comparable cases", self.styles['section_header']))
            section3_content.append(Paragraph(module.get_context(), self.styles['context']))
            
            content_path = module.generate_content(country_code, forecast_data, historical_data, self.output_dir)
            if content_path and content_path.exists():
                section3_content.append(Image(str(content_path), width=4*inch, height=2*inch))
            
            interpretation = module.get_interpretation(country_code, forecast_data, historical_data)
            if interpretation:
                section3_content.append(Paragraph(interpretation, self.styles['interpretation']))
        
        quadrant_table = Table(
            [
                [summary_content, section1_content],
                [section2_content, section3_content]
            ],
            colWidths=[5*inch, 5*inch],
            rowHeights=[3.75*inch, 3.75*inch]
        )
        
        quadrant_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.grey),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.grey),
            ('LINEBEFORE', (1, 0), (1, -1), 0.5, colors.grey),
        ]))
        
        story.append(quadrant_table)
        
        doc.build(story)
        return output_file