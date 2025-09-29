from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import inch
from reportlab.lib import colors
from typing import List
from grid_base_module import GridOutputModule

class GridPDFRenderer:
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
    
    def create_grid_report(self, priogrid_gid: int, target_month_id: int,
                          modules: List[GridOutputModule],
                          forecast_data, historical_data) -> Path:
        
        from GridDataProvider import GridDataProvider
        data_provider = GridDataProvider()
        
        country_name = data_provider.get_country_name(priogrid_gid)
        month_str = data_provider.month_id_to_string(target_month_id)
        
        output_file = self.output_dir / f"grid_{priogrid_gid}_forecast_{target_month_id}.pdf"
        doc = SimpleDocTemplate(str(output_file), pagesize=A4)
        
        story = []
        
        if country_name:
            title_text = f"Grid Cell Forecast: {priogrid_gid} ({country_name})"
        else:
            title_text = f"Grid Cell Forecast: {priogrid_gid}"
        
        story.append(Paragraph(title_text, self.styles['title']))
        story.append(Paragraph(f"Target Month: {month_str}", self.styles['subtitle']))
        story.append(Spacer(1, 20))
        
        for i, module in enumerate(modules, 1):
            story.append(Paragraph(f"Section {i}", self.styles['section_header']))
            story.append(Paragraph(module.get_context(), self.styles['normal']))
            story.append(Spacer(1, 15))
            
            content_path = module.generate_content(priogrid_gid, target_month_id,
                                                  forecast_data, historical_data, self.output_dir)
            if content_path and content_path.exists():
                if 'spatial' in str(content_path):
                    story.append(Image(str(content_path), width=4.5*inch, height=4.5*inch))
                else:
                    story.append(Image(str(content_path), width=6*inch, height=3.5*inch))
                story.append(Spacer(1, 15))
            
            interpretation = module.get_interpretation(priogrid_gid, target_month_id,
                                                      forecast_data, historical_data)
            if interpretation:
                story.append(Paragraph(interpretation, self.styles['normal']))
                story.append(Spacer(1, 20))
        
        doc.build(story)
        return output_file