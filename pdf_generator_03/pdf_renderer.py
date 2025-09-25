from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
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
                fontSize=14,
                textColor='black',
                alignment=TA_LEFT,
                spaceAfter=10
            ),
            'bluf': ParagraphStyle(
                'BLUF',
                parent=base_styles['Normal'],
                fontSize=10,
                alignment=TA_LEFT,
                spaceAfter=10,
                leftIndent=10,
                rightIndent=10,
                borderWidth=1,
                borderColor=colors.gray,
                borderPadding=10
            ),
            'section_header': ParagraphStyle(
                'SectionHeader',
                parent=base_styles['Heading2'],
                fontSize=12,
                textColor='black',
                alignment=TA_LEFT,
                spaceAfter=10
            ),
            'normal': ParagraphStyle(
                'Normal',
                parent=base_styles['Normal'],
                fontSize=10,
                alignment=TA_LEFT,
                spaceAfter=10
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
            topMargin=0.3*inch,
            bottomMargin=0.5*inch,
            leftMargin=0.5*inch,
            rightMargin=0.5*inch
        )
        
        story = []
        
        title_style = ParagraphStyle(
            'CenteredTitle',
            parent=self.styles['title'],
            alignment=TA_CENTER
        )
        story.append(Paragraph(f"{country_name}, {month_name} {target_year}", title_style))
        story.append(Spacer(1, 5))
        
        bluf_content = []
        section1_content = []
        
        try:
            print("Attempting to generate BLUF...")
            from bluf_generator import BLUFGenerator
            bluf_generator = BLUFGenerator()
            
            bluf_text = bluf_generator.generate_bluf(
                country_code, target_month, target_year,
                forecast_data, historical_data, None
            )
            
            print(f"BLUF generated: {bluf_text[:100]}...")
            
            bluf_content.append(Paragraph(bluf_text, self.styles['bluf']))
            
            print("BLUF added successfully")
            
        except Exception as e:
            print(f"Error generating BLUF: {e}")
            import traceback
            traceback.print_exc()
            bluf_content.append(Paragraph("BLUF generation failed", self.styles['normal']))
        
        if len(modules) > 0:
            module = modules[0]
            section1_content.append(Paragraph(f"Section 1", self.styles['section_header']))
            section1_content.append(Paragraph(module.get_context(), self.styles['normal']))
            section1_content.append(Spacer(1, 5))
            
            content_path = module.generate_content(country_code, forecast_data, historical_data, self.output_dir)
            if content_path and content_path.exists():
                section1_content.append(Image(str(content_path), width=5*inch, height=2.8*inch))
                section1_content.append(Spacer(1, 5))
            
            interpretation = module.get_interpretation(country_code, forecast_data, historical_data)
            if interpretation:
                section1_content.append(Paragraph(interpretation, self.styles['normal']))
        
        page1_table = Table(
            [[bluf_content, section1_content]],
            colWidths=[5*inch, 5*inch]
        )
        
        page1_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        story.append(page1_table)
        story.append(PageBreak())
        
        for i, module in enumerate(modules[1:], 2):
            story.append(Paragraph(f"Section {i}", self.styles['section_header']))
            story.append(Paragraph(module.get_context(), self.styles['normal']))
            story.append(Spacer(1, 10))
            
            content_path = module.generate_content(country_code, forecast_data, historical_data, self.output_dir)
            if content_path and content_path.exists():
                story.append(Image(str(content_path), width=8*inch, height=4.5*inch))
                story.append(Spacer(1, 10))
            
            interpretation = module.get_interpretation(country_code, forecast_data, historical_data)
            if interpretation:
                story.append(Paragraph(interpretation, self.styles['normal']))
                story.append(Spacer(1, 15))
        
        doc.build(story)
        return output_file