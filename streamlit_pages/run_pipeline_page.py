import os
import streamlit as st

from file_downloaders import StreamlitDownloader
from leaflet_reader import LeafletReader
from main_pipeline import Pipeline
from settings import PDF_FILES_DIR
from ui import texts


def run_pipeline(zipfile):
    st.write("Processing started...")
    args = {"overwrite_results": True, "use_test_client": False, "no_categorize": False}
    pipeline = Pipeline(
        args,
        leaflet_reader=LeafletReader(StreamlitDownloader(zipfile)),
        pdf_dir=PDF_FILES_DIR,
        display_mode=True,
    )

    st.session_state["results"] = pipeline.main()
    st.write("Processing finished")


# Streamlit UI
def show_run_page():
    # st.logo("ui/WWF_Logo.svg.png", size="Large")
    st.title(texts.UI_TITLE)
    st.write(texts.UI_SUBTITLE)
    st.write(texts.INSTRUCTIONS)

    uploaded_file = st.file_uploader("Upload your zipfile", type=["zip"])
    if uploaded_file and st.button("Process Leaflets"):
        run_pipeline(uploaded_file)

    # Display results if available
    if "results" in st.session_state:

        # Enable file download
        output_file = os.path.join(PDF_FILES_DIR, "results.xlsx")
        if os.path.exists(output_file):
            with open(output_file, "rb") as f:
                st.download_button(
                    label="Download Results",
                    data=f,
                    file_name="processed_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
