import streamlit as st
import json
from pathlib import Path
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="BLUF A/B Test Evaluator", layout="wide")

def load_results(uploaded_file):
    return json.loads(uploaded_file.read())

def save_evaluations(results_data, evaluations):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = {
        "metadata": results_data["metadata"],
        "evaluations": evaluations
    }
    
    filename = f"evaluations_{timestamp}.json"
    json_str = json.dumps(output, indent=2, ensure_ascii=False)
    
    return filename, json_str

def display_context(forecast_data, country_name, month, year):
    st.subheader("Context")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Country:** {country_name}")
        st.write(f"**Month/Year:** {month}/{year}")
        st.write(f"**Probability:** {forecast_data['probability_percent']} ({forecast_data['prob_percentile']}th percentile)")
        st.write(f"**Predicted Fatalities:** {forecast_data['predicted_fatalities']} ({forecast_data['pred_percentile']}th percentile)")
        st.write(f"**Risk Category:** {forecast_data['risk_category']}")
        st.write(f"**Intensity Category:** {forecast_data['intensity_category']}")
    
    with col2:
        st.write(f"**Cohort Countries:** {forecast_data['cohort']}")
        st.write(f"**Historical Average:** {forecast_data['historical_avg']} fatalities")
        st.write(f"**Trend:** {forecast_data['trend_desc']}")
        st.write(f"**Forecast vs Historical:** {forecast_data['forecast_vs_historical']}")
        st.write(f"**Covariates:** {forecast_data['covariate_desc']}")

def main():
    st.title("BLUF A/B Test Evaluator")
    
    if 'results_data' not in st.session_state:
        st.session_state.results_data = None
    if 'current_index' not in st.session_state:
        st.session_state.current_index = 0
    if 'evaluations' not in st.session_state:
        st.session_state.evaluations = []
    
    uploaded_file = st.file_uploader("Upload A/B Test Results JSON", type=['json'])
    
    if uploaded_file and st.session_state.results_data is None:
        st.session_state.results_data = load_results(uploaded_file)
        st.session_state.evaluations = [None] * len(st.session_state.results_data['results'])
        st.success(f"Loaded {len(st.session_state.results_data['results'])} test cases")
    
    if st.session_state.results_data:
        results = st.session_state.results_data['results']
        current_idx = st.session_state.current_index
        
        if current_idx >= len(results):
            st.warning("No more test cases to evaluate")
            return
        
        test_case = results[current_idx]
        
        st.write(f"### Case {current_idx + 1} of {len(results)}")
        
        display_context(
            test_case['forecast_data'],
            test_case['country_name'],
            test_case['month'],
            test_case['year']
        )
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Variant 1 (v1_original)")
            v1_output = test_case['variants']['bluf_v1']['output']
            if v1_output:
                if st.button(v1_output, key="v1_select", use_container_width=True, type="secondary"):
                    st.session_state.evaluations[current_idx] = {
                        "country_code": test_case['country_code'],
                        "month": test_case['month'],
                        "year": test_case['year'],
                        "better_variant": "bluf_v1",
                        "both_correct": False,
                        "both_incorrect": False,
                        "comment": ""
                    }
                    st.session_state.current_index += 1
                    st.rerun()
            else:
                st.error("No output")
        
        with col2:
            st.subheader("Variant 2 (v2_system_user)")
            v2_output = test_case['variants']['bluf_v2']['output']
            if v2_output:
                if st.button(v2_output, key="v2_select", use_container_width=True, type="secondary"):
                    st.session_state.evaluations[current_idx] = {
                        "country_code": test_case['country_code'],
                        "month": test_case['month'],
                        "year": test_case['year'],
                        "better_variant": "bluf_v2",
                        "both_correct": False,
                        "both_incorrect": False,
                        "comment": ""
                    }
                    st.session_state.current_index += 1
                    st.rerun()
            else:
                st.error("No output")
        
        st.divider()
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col3:
            pass
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            both_correct = st.checkbox("Both Correct")
        
        with col2:
            both_incorrect = st.checkbox("Both Incorrect")
        
        comment = st.text_area("Optional Comment", height=100)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("← Previous", disabled=current_idx == 0):
                st.session_state.current_index -= 1
                st.rerun()
        
        with col2:
            if st.button("Skip →"):
                st.session_state.current_index += 1
                st.rerun()
        
        with col3:
            if st.button("Save with Comment"):
                st.session_state.evaluations[current_idx] = {
                    "country_code": test_case['country_code'],
                    "month": test_case['month'],
                    "year": test_case['year'],
                    "better_variant": None,
                    "both_correct": both_correct,
                    "both_incorrect": both_incorrect,
                    "comment": comment
                }
                st.session_state.current_index += 1
                st.rerun()
        
        with col4:
            if st.button("Export Results"):
                completed = [e for e in st.session_state.evaluations if e is not None]
                if completed:
                    output_path = save_evaluations(
                        st.session_state.results_data,
                        completed
                    )
                    st.success(f"Exported {len(completed)} evaluations to {output_path.name}")
                else:
                    st.warning("No evaluations to export")
        
        progress = len([e for e in st.session_state.evaluations if e is not None])
        st.progress(progress / len(results), text=f"Progress: {progress}/{len(results)} evaluated")

if __name__ == "__main__":
    main()