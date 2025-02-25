import streamlit as st
import os
import pandas as pd
from main_pipeline import URL, PDF_DIR, parse_arguments, initialize_components, download_pdfs, \
    process_pdfs, process_all_directories, save_results
from result_saver import ResultSaver


def run_pipeline():
    st.write("Processing started...")
    args = parse_arguments()
    leaflet_reader, openai_client, result_saver, categorizer = initialize_components(args)

    download_pdfs(leaflet_reader)
    if process_pdfs(leaflet_reader, result_saver):
        process_all_directories(openai_client, categorizer, result_saver)
        st.session_state["results"] = save_results(result_saver)
    st.write("Processing finished")


# Streamlit UI
st.logo(
    'WWF_Logo.svg.png',
    size="Large"
)
st.title("BBQ GPT")
st.write("This tool processes supermarket leaflets and extracts all products with a categorization if they are grillable or not.")

st.write(f"Pdfs are taken from {URL}")

if st.button("Process Leaflets"):
    run_pipeline()

# Display results if available
if "results" in st.session_state:

    # Enable file download
    output_file = os.path.join(PDF_DIR, "results.xlsx")
    if os.path.exists(output_file):
        with open(output_file, "rb") as f:
            st.download_button(
                label="Download Results",
                data=f,
                file_name="processed_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
