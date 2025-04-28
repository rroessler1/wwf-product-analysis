import os

import streamlit as st
import pandas as pd

from settings import PDF_FILES_DIR
from streamlit_pages.helper_functions import (
    get_results,
    get_unique_images,
    check_result_columns,
    get_filtered_data_by_selection,
    show_current_image,
    get_filtered_page_data,
    show_edit_options,
    show_page_results_df,
    show_download,
    show_add_missing_product,
    reset_state_values,
    show_forward_backward_buttons,
    show_mark_products_as_checked,
)
from streamlit_pages.helper_strings import (
    HELP_INCLUDE_CHECKED_PROD,
    HELP_STRING_BBQ_PROD,
    HELP_STRING_NON_BBQ_PROD,
    HELP_LLM_CONFIDENCE,
    HELP_ONLY_CATEGORIES,
)

result_csv_path = os.path.join(PDF_FILES_DIR, "results.csv")
required_columns = [
    "extracted_folder",
    "extracted_page_number",
    "extracted_product_name",
    "extracted_original_price",
    "extracted_discount_price",
    "extracted_percentage_discount",
    "final_category",
]


def show_check_results_page():
    # Load the data from csv file
    data = get_results(result_csv_path)
    check_result_columns(data, required_columns)

    st.write("### What do you want to check?")
    col1, col2, col3 = st.columns(3)  # Adjust column width proportions as needed
    with col1:
        st.session_state.bbq_products = st.checkbox(
            "BBQ products",
            value=True,
            on_change=reset_state_values,
            help=HELP_STRING_BBQ_PROD,
        )
        st.session_state.non_bbq_products = st.checkbox(
            "Non-BBQ products",
            on_change=reset_state_values,
            help=HELP_STRING_NON_BBQ_PROD,
        )
    with col2:
        st.session_state.include_checked_products = st.checkbox(
            "Include checked products?",
            on_change=reset_state_values,
            help=HELP_INCLUDE_CHECKED_PROD,
        )
        st.session_state.only_categories = st.checkbox(
            "Only Categories?", help=HELP_ONLY_CATEGORIES
        )
    with col3:
        st.session_state.max_llm_confidence = st.slider(
            "LLM confidence lower than: ",
            min_value=0,
            max_value=100,
            value=100,
            step=10,
            on_change=reset_state_values,
            help=HELP_LLM_CONFIDENCE,
        )
    show_check_results_frame(data)


def show_check_results_frame(data: pd.DataFrame) -> None:

    filtered_data = get_filtered_data_by_selection(data)
    # Get the unique combinations of folder and page number
    unique_images = get_unique_images(filtered_data)

    # Initialize session state for current page index if not already set
    if "current_page_index" not in st.session_state:
        st.session_state.current_page_index = 0
    if len(unique_images) > 0:
        show_forward_backward_buttons(len(unique_images), "Top")

        # Get the current folder and page number based on session state index
        if len(unique_images) == st.session_state.current_page_index:
            st.session_state.current_page_index -= 1
        current_image = unique_images.iloc[st.session_state.current_page_index]
        current_folder = current_image["extracted_folder"]
        current_page_number = current_image["extracted_page_number"]

        filtered_page_data = get_filtered_page_data(
            data, current_folder, current_page_number
        )

        # Hack to handle individual images
        current_folder = (
            os.path.join(PDF_FILES_DIR, current_folder)
            if current_folder != PDF_FILES_DIR
            else PDF_FILES_DIR
        )
        show_current_image(current_folder, current_page_number)
        show_edit_options(data, filtered_page_data, result_csv_path)

        show_mark_products_as_checked(
            data, current_folder, current_page_number, result_csv_path
        )
        show_add_missing_product(
            data, current_folder, current_page_number, result_csv_path
        )

        show_forward_backward_buttons(len(unique_images), "Bottom")
        show_page_results_df(data, current_folder, current_page_number)
        show_download(data)
    else:
        st.write("Everything is already checked with this type of check!")
