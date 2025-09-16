from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import inch
from reportlab.lib import colors

class PDFBuilder:
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
    
    def _add_model_outputs_section(self, story: list, country_code: str, data_loader):
        story.append(Paragraph("Model Outputs", self.styles['section_header']))
        
        month_indices = [2, 5, 11]
        forecast_data = data_loader.get_country_forecast_data(country_code, month_indices)
        
        if forecast_data:
            country_name = list(forecast_data.values())[0]['country_name']
        else:
            country_name = country_code
        
        explanation_text = f"""
        To contextualize our forecasts, consider our primary output metrics: Probability of >=25 Fatalities and Predicted Fatalities.
        
        The probability measure refers to our estimate of how likely {country_name} is to experience more than 25 fatalities in a given month. We use this metric as an indicator of the likelihood of a 'severe' conflict. Based on the distribution of this value throughout our outcome data, we determined that there are four risk categories: 1) Extremely Unlikely; 2) Unlikely; 3) Likely; 4) Extremely Likely.
        
        The predicted fatalities measure refers to the number of forecasted fatalities for a given month. Based on the distribution of this value throughout our outcome data, the range of predicted fatalities fits into the following five categories: 1) 0 fatalities; 2) 1-10 fatalities; 3) 11-100 fatalities; 4) 101-1000 fatalities; 5) 1001 - 10000 fatalities.
        
        The table below shows the forecast values for each key month, followed by a figure showing the average position across all three months.
        """
        
        story.append(Paragraph(explanation_text, self.styles['normal']))
        story.append(Spacer(1, 15))
        
        story.append(Paragraph("<b>Table 1</b>", self.styles['normal']))
        story.append(Spacer(1, 5))
        
        headers = ['Month', 'Probability ≥25 Fatalities', 'Likelihood Category', 
                  'Predicted Fatalities', 'Intensity Category']
        
        table_data = [headers]
        
        months = [
            ('December 2025', 2),
            ('March 2026', 5), 
            ('September 2026', 11)
        ]
        
        total_prob = 0
        total_fatalities = 0
        valid_months = 0
        
        for month_name, month_idx in months:
            if month_idx in forecast_data:
                month_data = forecast_data[month_idx]
                prob_value = f"{month_data['probability']:.3f} ({month_data['probability']*100:.1f}%)"
                likelihood_cat = data_loader.categorize_probability(month_data['probability'])
                pred_fatalities = f"{month_data['predicted_fatalities']:.1f}"
                intensity_cat = data_loader.categorize_intensity(month_data['predicted_fatalities'])
                
                total_prob += month_data['probability']
                total_fatalities += month_data['predicted_fatalities']
                valid_months += 1
            else:
                prob_value = "No data"
                likelihood_cat = "No data"
                pred_fatalities = "No data"
                intensity_cat = "No data"
            
            row = [month_name, prob_value, likelihood_cat, pred_fatalities, intensity_cat]
            table_data.append(row)
        
        if valid_months > 0:
            avg_prob = total_prob / valid_months
            avg_fatalities = total_fatalities / valid_months
            avg_prob_formatted = f"{avg_prob:.3f} ({avg_prob*100:.1f}%)"
            avg_likelihood = data_loader.categorize_probability(avg_prob)
            avg_fatalities_formatted = f"{avg_fatalities:.1f}"
            avg_intensity = data_loader.categorize_intensity(avg_fatalities)
            
            avg_row = ['Average', avg_prob_formatted, avg_likelihood, avg_fatalities_formatted, avg_intensity]
            table_data.append(avg_row)
        
        table = Table(table_data, colWidths=[100, 120, 120, 100, 120])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        story.append(Spacer(1, 20))
        
        if valid_months > 0 and hasattr(data_loader, 'create_average_forecast_plot'):
            story.append(Paragraph(f"Figure 1 below depicts the Average Conflict Forecast Position for {country_name} across each of three months above.", self.styles['normal']))
            story.append(Spacer(1, 10))
            
            plot_path = data_loader.create_average_forecast_plot(country_code, avg_prob, avg_fatalities, self.output_dir)
            if plot_path and plot_path.exists():
                story.append(Paragraph("<b>Figure 1</b>", self.styles['normal']))
                story.append(Image(str(plot_path), width=5*inch, height=3.5*inch))
                story.append(Spacer(1, 15))
        
        return valid_months, country_name, avg_prob, avg_fatalities
    
    def _add_temporal_context_section(self, story: list, country_code: str, country_name: str, data_loader):
        story.append(Paragraph("Temporal Context", self.styles['section_header']))
        
        story.append(Paragraph("The figure below depicts our yearly projection for conflict fatalities in the context of the prior decade.", self.styles['normal']))
        story.append(Spacer(1, 15))
        
        story.append(Paragraph("<b>Figure 2</b>", self.styles['normal']))
        story.append(Spacer(1, 5))
        
        if hasattr(data_loader, 'create_rolling_periods_plot'):
            plot_path = data_loader.create_rolling_periods_plot(country_code, self.output_dir)
            if plot_path and plot_path.exists():
                story.append(Image(str(plot_path), width=6*inch, height=3.5*inch))
                story.append(Spacer(1, 15))
    
    def _add_similar_countries_section(self, story: list, country_code: str, country_name: str, avg_prob: float, avg_fatalities: float, data_loader):
        story.append(Paragraph("Most-similar Countries", self.styles['section_header']))
        
        story.append(Paragraph(f"Table 2 below depicts the position of {country_name} in relation to the countries with the most similar conflict profile.", self.styles['normal']))
        story.append(Spacer(1, 15))
        
        story.append(Paragraph("<b>Table 2</b>", self.styles['normal']))
        story.append(Spacer(1, 5))
        
        similar_countries = data_loader.get_similar_countries(country_code, avg_prob, avg_fatalities)
        
        headers = ['Country', 'Avg Probability ≥25 Fatalities', 'Avg Likelihood Category', 
                  'Avg Predicted Fatalities', 'Avg Intensity Category']
        
        table_data = [headers]
        
        for country_data in similar_countries:
            country_display = country_data['name']
            
            prob_formatted = f"{country_data['avg_probability']:.3f} ({country_data['avg_probability']*100:.1f}%)"
            likelihood_cat = data_loader.categorize_probability(country_data['avg_probability'])
            fatalities_formatted = f"{country_data['avg_fatalities']:.1f}"
            intensity_cat = data_loader.categorize_intensity(country_data['avg_fatalities'])
            
            row = [country_display, prob_formatted, likelihood_cat, fatalities_formatted, intensity_cat]
            table_data.append(row)
        
        table = Table(table_data, colWidths=[80, 130, 110, 100, 110])
        
        table_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]
        
        for i, country_data in enumerate(similar_countries, start=1):
            if country_data['code'] == country_code:
                table_style.append(('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold'))
                table_style.append(('BACKGROUND', (0, i), (-1, i), colors.lightblue))
        
        table.setStyle(TableStyle(table_style))
        
        story.append(table)
        story.append(Spacer(1, 20))
    
    def _add_summary_section(self, story: list):
        story.append(Paragraph("Summary", self.styles['section_header']))
        story.append(Spacer(1, 20))
    
    def create_country_report(self, country_code: str, data_loader) -> Path:
        output_file = self.output_dir / f"{country_code}_forecast_report_v3.pdf"
        doc = SimpleDocTemplate(str(output_file), pagesize=A4)
        
        story = []
        story.append(Paragraph(f"Conflict Forecast: {country_code}", self.styles['title']))
        story.append(Paragraph("Forecast Intervals: December 2025, March 2026, September 2026", self.styles['subtitle']))
        story.append(Spacer(1, 20))
        
        self._add_summary_section(story)
        result = self._add_model_outputs_section(story, country_code, data_loader)
        
        if result and len(result) == 4:
            valid_months, country_name, avg_prob, avg_fatalities = result
            if valid_months > 0:
                self._add_similar_countries_section(story, country_code, country_name, avg_prob, avg_fatalities, data_loader)
                self._add_temporal_context_section(story, country_code, country_name, data_loader)
        
        doc.build(story)
        return output_file