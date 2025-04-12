import streamlit as st

from streamlit_pages.check_results_page import show_check_results_page
from streamlit_pages.run_pipeline_page import show_run_page
from ui import texts

# Set up the Streamlit page title
st.logo("ui/WWF_Logo.svg.png", size="Large")
# Sidebar navigation
st.sidebar.title(texts.NAVIGATION)
navigation = st.sidebar.radio(
    "Go to", [texts.RUN_DATA_EXTRACTION, texts.MANUAL_ERROR_CHECK]
)

# Show the selected page
if navigation == texts.RUN_DATA_EXTRACTION:
    show_run_page()
elif navigation == texts.MANUAL_ERROR_CHECK:
    show_check_results_page()
