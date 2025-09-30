from pathlib import Path
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import inch
from reportlab.lib import colors
from typing import List
from grid_base_module import GridOutputModule
import sys

sys.path.append(str(Path(__file__).parent.parent / "abtest_vito"))
from grid_bluf_reader import GridBLUFReader

class GridPDFRenderer:
    def __init__(self, output_dir: Path, blufs_dir: Path = None):
        self.output_dir = output_dir
        self.styles = self._create_styles()
        
        if blufs_dir is None:
            blufs_dir = Path(__file__).parent.parent / "abtest_vito" / "output"
        
        self.bluf_reader = GridBLUFReader(blufs_dir)
    
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
            'interpretation': ParagraphStyle(
                'Interpretation',
                parent=base_styles['Normal'],
                fontSize=7,
                alignment=TA_LEFT,
                spaceAfter=3
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
        doc = SimpleDocTemplate(
            str(output_file), 
            pagesize=landscape(LETTER),
            topMargin=0.15*inch,
            bottomMargin=0.15*inch,
            leftMargin=0.3*inch,
            rightMargin=0.3*inch
        )
        
        story = []
        
        if country_name:
            title_text = f"Grid {priogrid_gid} ({country_name}), {month_str}"
        else:
            title_text = f"Grid {priogrid_gid}, {month_str}"
        
        story.append(Paragraph(title_text, self.styles['title']))
        
        summary_content = []
        temporal_content = []
        spatial_content = []
        comparison_content = []
        
        summary_content.append(Paragraph("Summary", self.styles['section_header']))
        
        bluf_text = self.bluf_reader.get_bluf(priogrid_gid, target_month_id)
        if bluf_text:
            summary_content.append(Paragraph(bluf_text, self.styles['interpretation']))
        else:
            summary_content.append(Paragraph(
                f"BLUF not available for Grid {priogrid_gid}, Month {target_month_id}", 
                self.styles['context']
            ))
        
        temporal_module = modules[0]
        temporal_content.append(Paragraph("Violence trend", self.styles['section_header']))
        temporal_content.append(Paragraph(temporal_module.get_context(), self.styles['context']))
        
        content_path = temporal_module.generate_content(priogrid_gid, target_month_id,
                                                       forecast_data, historical_data, self.output_dir)
        if content_path and content_path.exists():
            temporal_content.append(Image(str(content_path), width=4*inch, height=2*inch))
        
        interpretation = temporal_module.get_interpretation(priogrid_gid, target_month_id,
                                                           forecast_data, historical_data)
        if interpretation:
            temporal_content.append(Paragraph(interpretation, self.styles['interpretation']))
        
        spatial_module = modules[2]
        spatial_content.append(Paragraph("Geographic context", self.styles['section_header']))
        spatial_content.append(Paragraph(spatial_module.get_context(), self.styles['context']))
        
        content_path = spatial_module.generate_content(priogrid_gid, target_month_id,
                                                       forecast_data, historical_data, self.output_dir)
        if content_path and content_path.exists():
            spatial_content.append(Image(str(content_path), width=4*inch, height=2*inch))
        
        interpretation = spatial_module.get_interpretation(priogrid_gid, target_month_id,
                                                          forecast_data, historical_data)
        if interpretation:
            spatial_content.append(Paragraph(interpretation, self.styles['interpretation']))
        
        comparison_module = modules[1]
        comparison_content.append(Paragraph("Climate and food security model", self.styles['section_header']))
        comparison_content.append(Paragraph(comparison_module.get_context(), self.styles['context']))
        
        content_path = comparison_module.generate_content(priogrid_gid, target_month_id,
                                                         forecast_data, historical_data, self.output_dir)
        if content_path and content_path.exists():
            comparison_content.append(Image(str(content_path), width=4*inch, height=2*inch))
        
        interpretation = comparison_module.get_interpretation(priogrid_gid, target_month_id,
                                                             forecast_data, historical_data)
        if interpretation:
            comparison_content.append(Paragraph(interpretation, self.styles['interpretation']))
        
        quadrant_table = Table(
            [
                [summary_content, temporal_content],
                [spatial_content, comparison_content]
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