from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import inch
from reportlab.lib import colors

doc = SimpleDocTemplate(
    "layout_test.pdf",
    pagesize=landscape(LETTER),
    topMargin=0.15*inch,
    bottomMargin=0.2*inch,
    leftMargin=0.3*inch,
    rightMargin=0.3*inch
)

title_style = ParagraphStyle(
    'Title',
    fontSize=12,
    textColor='black',
    alignment=TA_CENTER,
    spaceAfter=8,
    spaceBefore=0
)

content_style = ParagraphStyle(
    'Content',
    fontSize=9,
    alignment=TA_LEFT,
    spaceAfter=5
)

header_style = ParagraphStyle(
    'Header',
    fontSize=10,
    alignment=TA_LEFT,
    textColor='black',
    spaceAfter=3,
    fontName='Helvetica-Bold'
)

story = []

title = Paragraph("Ethiopia, March 2026", title_style)
story.append(title)

summary_content = [
    Paragraph("Summary", header_style),
    Paragraph("This is the BLUF summary section with dummy content. " * 5, content_style)
]

section1_content = [
    Paragraph("Section 1", header_style),
    Paragraph("This is Section 1 with dummy content and would contain a temporal chart. " * 3, content_style)
]

section2_content = [
    Paragraph("Section 2", header_style),
    Paragraph("This is Section 2 with dummy content and would contain covariate distributions. " * 3, content_style)
]

section3_content = [
    Paragraph("Section 3", header_style),
    Paragraph("This is Section 3 with dummy content and would contain the symlog visualization. " * 3, content_style)
]

quadrant_table = Table(
    [
        [summary_content, section1_content],
        [section2_content, section3_content]
    ],
    colWidths=[5*inch, 5*inch],
    rowHeights=[3.8*inch, 3.8*inch]
)

quadrant_table.setStyle(TableStyle([
    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ('TOPPADDING', (0, 0), (-1, -1), 5),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.grey),
    ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.grey),
    ('LINEBEFORE', (1, 0), (1, -1), 0.5, colors.grey),
]))

story.append(quadrant_table)

doc.build(story)
print("Generated layout_test.pdf")