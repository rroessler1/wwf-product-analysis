import os
from io import BytesIO

import pandas as pd
import streamlit as st
from PIL import Image

from llms.models import FinalProductCategory


category_options: list[str] = [cat.value for cat in FinalProductCategory]


def get_results(result_csv_path: str) -> pd.DataFrame:
    # Ensure 'extracted_folder', 'extracted_page_number', and 'categorization_all_same' columns are present
    if os.path.exists(result_csv_path):
        data = pd.read_csv(result_csv_path)
    else:
        st.error(f"There is no results file at the path {result_csv_path}.")
        st.stop()

    if not "data_checked" in data.columns:
        data["data_checked"] = False
    if not "category_checked" in data.columns:
        data["category_checked"] = False
    return data


def check_result_columns(data: pd.DataFrame, required_columns: list[str]) -> None:
    # check columns
    if not all(col in data.columns for col in required_columns):
        st.error(f"The dataframe must have {required_columns} columns.")
        st.stop()


def reset_state_values() -> None:
    st.session_state.current_page_index = 0
    st.session_state.missing_product_counter = 0


def get_unique_images(data: pd.DataFrame) -> pd.DataFrame:
    return data[["extracted_folder", "extracted_page_number"]].drop_duplicates()


def get_filtered_data_by_selection(data: pd.DataFrame) -> pd.DataFrame:
    return data[get_mask_selection(data)]


def get_filtered_page_data(
    data: pd.DataFrame, current_folder: str, current_page_number: int
) -> pd.DataFrame:
    # Filter the dataframe based on the current folder, page number, and categorization_all_same == True
    return data[get_mask_page(data, current_folder, current_page_number)]


def show_current_image(current_folder: str, current_page_number: int) -> None:
    # Load the image corresponding to the current folder and page number
    try:
        image_path = f"{current_folder}/{current_page_number}"
        image = Image.open(image_path)
        st.sidebar.image(
            image,
            caption=f"Image for {current_folder}, Page {current_page_number}",
            use_container_width=True,
        )
    except FileNotFoundError:
        st.sidebar.warning(
            f"Image not found for {current_folder}, Page {current_page_number}"
        )


def show_edit_options(
    data: pd.DataFrame, filtered_page_data: pd.DataFrame, result_path: str
) -> None:
    # Display filtered rows and provide options for editing them
    if not filtered_page_data.empty:
        for idx in filtered_page_data.index:
            if st.session_state.only_categories:
                edit_product_category(idx, data, result_path)
            else:
                edit_product_data(idx, data, result_path)
    else:
        st.write("No rows available for the current image")


def edit_product_category(index: int, data: pd.DataFrame, storage_path: str) -> None:
    with st.form(key=f"form_{index}"):
        # st.write(f"Editing Row {index + 1} (Category confidence = {data.loc[index, "final_certainty"]})")

        col1, col2 = st.columns([2, 1])

        with col1:
            product_name = st.text_input(
                "Product Name", value=str(data.loc[index, "extracted_product_name"])
            )
        with col2:
            final_category = st.selectbox(
                label="Category",
                options=category_options,
                index=category_options.index(data.loc[index, "final_category"]),
            )

        # Button to save the changes for this row
        submitted = st.form_submit_button("Save Changes")

        if submitted:
            data.loc[index, "final_category"] = final_category
            data.loc[index, "extracted_product_name"] = product_name
            data.loc[index, "category_checked"] = True

            data.to_csv(storage_path, index=False)
            st.success(f"Row {index + 1} updated successfully!")


def edit_product_data(index: int, data: pd.DataFrame, storage_path: str) -> None:
    with st.form(key=f"form_{index}"):
        confidence = data.loc[index, "final_certainty"]
        st.write(f"Editing Row {index + 1}. Category confidence: {confidence}")

        # Create editable input fields for each relevant column in the row
        col1, col2 = st.columns([2, 1])

        with col1:
            product_name = st.text_input(
                "Product Name", value=str(data.loc[index, "extracted_product_name"])
            )
        with col2:
            final_category = st.selectbox(
                label="Category",
                options=category_options,
                index=category_options.index(data.loc[index, "final_category"]),
            )

        col3, col4, col5 = st.columns(3)
        with col3:
            original_price = st.number_input(
                "Original Price",
                value=float(data.loc[index, "extracted_original_price"]),
                format="%0.2f",
                step=0.1,
            )
        with col4:
            discount_price = st.number_input(
                "Discount Price",
                value=float(data.loc[index, "extracted_discount_price"]),
                format="%0.2f",
                step=0.1,
            )
        with col5:
            percentage_discount = st.number_input(
                "Percentage Discount",
                value=float(data.loc[index, "extracted_percentage_discount"]),
                format="%0.0f",
                step=1.0,
            )

        # Button to save the changes for this row
        submitted = st.form_submit_button("Save Changes")

        if submitted:
            # Update the dataframe with the new values
            data.loc[index, "extracted_product_name"] = product_name
            data.loc[index, "extracted_original_price"] = original_price
            data.loc[index, "extracted_discount_price"] = discount_price
            data.loc[index, "extracted_percentage_discount"] = percentage_discount
            data.loc[index, "final_category"] = final_category
            data.loc[index, "data_checked"] = True
            data.loc[index, "category_checked"] = True

            data.to_csv(storage_path, index=False)
            st.success(f"Row {index + 1} updated successfully!")


def show_mark_products_as_checked(
    data: pd.DataFrame, current_folder: str, current_page_number: int, storage_path: str
) -> None:
    if st.button("Mark Products as Checked", key="mark_products_as_checked"):
        current_data_mask = get_mask_page(data, current_folder, current_page_number)
        data.loc[current_data_mask, "category_checked"] = True
        if not st.session_state.only_categories:
            data.loc[current_data_mask, "data_checked"] = True
        data.to_csv(storage_path, index=False)


def show_add_missing_product(
    data: pd.DataFrame,
    current_folder: str,
    current_page_number: int,
    storage_path: str,
    missing_product_counter: int = 0,
) -> None:
    if "missing_product_counter" not in st.session_state:
        st.session_state.missing_product_counter = 0

    # Button to show the form
    if st.button(
        "Add missing product", key=f"Missing_product_button_{missing_product_counter}"
    ):
        st.session_state.missing_product_counter += 1

    # Conditionally display the form based on session state
    if st.session_state.missing_product_counter > missing_product_counter:
        with st.form(key=f"form_missing_product_{missing_product_counter}"):
            st.write("Add Missing Row:")

            # Create editable input fields for each relevant column in the row
            col1, col2 = st.columns([2, 1])

            with col1:
                product_name = st.text_input("Product Name")
            with col2:
                final_category = st.selectbox(
                    label="Category", options=(["Select Category"] + category_options)
                )

            col3, col4, col5 = st.columns(3)
            with col3:
                original_price = st.number_input(
                    "Original Price", format="%0.2f", step=0.1
                )
            with col4:
                discount_price = st.number_input(
                    "Discount Price", format="%0.2f", step=0.1
                )
            with col5:
                percentage_discount = st.number_input(
                    "Percentage Discount", format="%0.0f", step=1.0
                )

            # Button to save the changes for this row
            submitted = st.form_submit_button("Save New Product")

            if submitted:
                error_messages = []
                if product_name == "":
                    error_messages.append("Product Name is required.")
                if final_category == "Select Category":
                    error_messages.append("Category must be selected")

                if error_messages:
                    for error in error_messages:
                        st.error(error)
                else:

                    # Create a new product DataFrame to append to the existing data
                    new_product = pd.DataFrame(
                        [
                            {
                                "extracted_product_name": product_name,
                                "extracted_original_price": original_price,
                                "extracted_discount_price": discount_price,
                                "extracted_percentage_discount": percentage_discount,
                                "final_category": final_category,
                                "data_checked": True,
                                "extracted_folder": current_folder,
                                "extracted_page_number": current_page_number,
                                "category_checked": True,
                                "final_certainty": 100,
                            }
                        ]
                    )

                    # Find reference row in the original data to get additional columns if they exist
                    reference_row = data[
                        (data["extracted_folder"] == current_folder)
                        & (data["extracted_page_number"] == current_page_number)
                    ]
                    if not reference_row.empty:
                        new_product.loc[0, "date_collected"] = reference_row.iloc[0][
                            "date_collected"
                        ]
                        new_product.loc[0, "calendar_week"] = reference_row.iloc[0][
                            "calendar_week"
                        ]

                    # Append the new product row to the original DataFrame and save it
                    data = pd.concat([data, new_product], ignore_index=True)
                    data.to_csv(storage_path, index=False)

                    # Notify the user and reset the form state to allow adding more products
                    st.success("Missing product added!")

        # Recursive call to show the add button again after submission
        show_add_missing_product(
            data,
            current_folder,
            current_page_number,
            storage_path,
            missing_product_counter + 1,
        )


def show_page_results_df(
    data: pd.DataFrame, current_folder: str, current_page_number: int
) -> None:
    # Display the updated dataframe after editing
    updated_data = data[
        get_mask_page_results(data, current_folder, current_page_number)
    ]
    if not updated_data.empty:
        st.write("### Updated Dataframe")
        st.dataframe(updated_data)


def show_download(data: pd.DataFrame) -> None:
    results_as_excel = to_excel(data)

    st.download_button(
        label="Download Results File",
        data=results_as_excel,
        file_name="results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def show_forward_backward_buttons(max_len: int, position: str) -> None:
    """
    Creates Previous and Next buttons for navigating through images.

    Parameters:
        max_len (int): the maximum length of images to show
        position (str): the position of the button on the streamlit page, can't be the same twice so that the button keys are different

    Effects:
        Modifies st.session_state.current_page_index based on button interaction.

    """
    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        if (
            st.button("Previous Image", key=f"Previous Image ({position})")
            and st.session_state.current_page_index > 0
        ):
            st.session_state.current_page_index -= 1
            st.session_state.missing_product_counter = 0

    with col3:
        if (
            st.button("Next Image", key=f"Next Image ({position})")
            and st.session_state.current_page_index < max_len - 1
        ):
            st.session_state.current_page_index += 1
            st.session_state.missing_product_counter = 0
        elif st.session_state.current_page_index == max_len - 1:
            st.write("Last image reached!")

    with col2:
        st.write(f"Current Image {st.session_state.current_page_index+1} / {max_len} ")

    if position == "Top":
        st.divider()


# Function to convert the DataFrame to an Excel file
def to_excel(dataframe):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="Results")
    processed_data = output.getvalue()
    return processed_data


### masking filter ###


def get_mask_bbq_products(data: pd.DataFrame) -> pd.Series:
    if st.session_state.bbq_products:
        return data["final_category"] != FinalProductCategory.NO_GRILL_PRODUCT.value
    else:
        return pd.Series([False] * len(data))


def get_mask_non_bbq_products(data: pd.DataFrame) -> pd.Series:
    if st.session_state.non_bbq_products:
        return data["final_category"] == FinalProductCategory.NO_GRILL_PRODUCT.value
    else:
        return pd.Series([False] * len(data))


def get_mask_included_checked_products(data: pd.DataFrame) -> pd.Series:
    if st.session_state.include_checked_products:
        return pd.Series([True] * len(data))
    elif st.session_state.only_categories:
        return data["category_checked"] == False
    else:
        return data["data_checked"] == False


def get_mask_current_image(
    data: pd.DataFrame, current_folder: str, current_page_number: int
) -> pd.Series:
    return (data["extracted_folder"] == current_folder) & (
        data["extracted_page_number"] == current_page_number
    )


def get_mask_max_llm_confidence(data: pd.DataFrame) -> pd.Series:
    if isinstance(st.session_state.max_llm_confidence, int) & (
        not st.session_state.include_checked_products
    ):
        return data["final_certainty"] <= st.session_state.max_llm_confidence
    else:
        return pd.Series([True] * len(data))


def get_mask_core(data: pd.DataFrame) -> pd.Series:
    return (
        get_mask_bbq_products(data) | get_mask_non_bbq_products(data)
    ) & get_mask_max_llm_confidence(data)


def get_mask_selection(data: pd.DataFrame) -> pd.Series:
    return get_mask_core(data) & get_mask_included_checked_products(data)


def get_mask_page(
    data: pd.DataFrame, current_folder: str, current_page_number: int
) -> pd.Series:
    return get_mask_selection(data) & get_mask_current_image(
        data, current_folder, current_page_number
    )


def get_mask_page_results(
    data: pd.DataFrame, current_folder: str, current_page_number: int
) -> pd.Series:
    return get_mask_core(data) & get_mask_current_image(
        data, current_folder, current_page_number
    )
