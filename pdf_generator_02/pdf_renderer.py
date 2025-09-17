from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
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
                fontSize=18,
                textColor='black',
                alignment=TA_CENTER,
                spaceAfter=15
            ),
            'subtitle': ParagraphStyle(
                'Subtitle',
                parent=base_styles['Heading2'],
                fontSize=14,
                textColor='black',
                alignment=TA_CENTER,
                spaceAfter=30
            ),
            'section_header': ParagraphStyle(
                'SectionHeader',
                parent=base_styles['Heading2'],
                fontSize=14,
                textColor='black',
                alignment=TA_LEFT,
                spaceAfter=15
            ),
            'normal': ParagraphStyle(
                'Normal',
                parent=base_styles['Normal'],
                fontSize=11,
                alignment=TA_LEFT,
                spaceAfter=12
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
        doc = SimpleDocTemplate(str(output_file), pagesize=A4)
        
        story = []
        story.append(Paragraph(f"Conflict Forecast: {country_name}", self.styles['title']))
        story.append(Paragraph(f"Target Month: {month_name} {target_year}", self.styles['subtitle']))
        story.append(Spacer(1, 20))
        
        for i, module in enumerate(modules, 1):
            # Add context
            story.append(Paragraph(f"Section {i}", self.styles['section_header']))
            story.append(Paragraph(module.get_context(), self.styles['normal']))
            story.append(Spacer(1, 15))
            
            # Generate and add content
            content_path = module.generate_content(country_code, forecast_data, historical_data, self.output_dir)
            if content_path and content_path.exists():
                story.append(Image(str(content_path), width=6*inch, height=3.5*inch))
                story.append(Spacer(1, 15))
            
            # Add interpretation
            interpretation = module.get_interpretation(country_code, forecast_data, historical_data)
            if interpretation:
                story.append(Paragraph(interpretation, self.styles['normal']))
                story.append(Spacer(1, 20))
        
        doc.build(story)
        return output_file