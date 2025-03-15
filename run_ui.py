import streamlit as st
import os

from ui import texts
from main_pipeline import URL, PDF_DIR, main


def run_pipeline():
    st.write("Processing started...")
    st.session_state["results"] = main(display_mode=True)
    st.write("Processing finished")


# Streamlit UI
st.logo("ui/WWF_Logo.svg.png", size="Large")
st.title(texts.UI_TITLE)
st.write(texts.UI_SUBTITLE)

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
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
