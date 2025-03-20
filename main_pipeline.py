import os
import time

import argparse
from datetime import datetime
from natsort import natsorted
import pandas as pd
import streamlit as st

from categorization.product_categorizer import ProductCategorizer
from file_downloaders import NoopDownloader
from leaflet_reader import LeafletReader
from llms.openai_client import OpenAIClient
from llms.mock_client import MockLLM
from result_saver import ResultSaver
from settings import NUMBER_OF_CHATGPT_VALIDATIONS
from utils import get_api_key
from validation.validation_comparison import compare_validation


PDF_DIR = "pdf-files"
DO_CATEGORIZE = True
USE_TEST_LLM_CLIENT = True
SLEEP_TIME = 0  # TODO: test that we're not being rate limited using their API key


def append_metadata(df: pd.DataFrame):
    df["date_collected"] = datetime.now().strftime("%Y-%m-%d")
    df["calendar_week"] = datetime.now().isocalendar().week


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Runs the main script to download PDFs, split them, and write the results."
    )
    parser.add_argument(
        "--overwrite-results",
        action="store_true",
        help="Overwrite existing results if they exist.",
    )
    return vars(parser.parse_args())


def initialize_components(args):
    leaflet_reader = LeafletReader(file_downloader=NoopDownloader())
    openai_client = (
        MockLLM() if USE_TEST_LLM_CLIENT else OpenAIClient(api_key=get_api_key())
    )
    result_saver = ResultSaver(overwrite_results=args["overwrite_results"])
    categorizer = ProductCategorizer()
    return leaflet_reader, openai_client, result_saver, categorizer


def process_pdfs(leaflet_reader, result_saver):
    if result_saver.results_exist_and_should_be_kept(PDF_DIR):
        log_message(
            f"Already found a results file: [{os.path.join(PDF_DIR, result_saver.output_file_name)}], nothing to do.",
            display_mode=False,
        )
        log_message(
            "If you'd like new results, delete or rename the results file and rerun the script.",
            display_mode=False,
        )
        return False

    for filename in os.listdir(PDF_DIR):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(PDF_DIR, filename)
            pdf_name, _ = os.path.splitext(os.path.basename(filename))
            output_dir = os.path.join(PDF_DIR, pdf_name)
            if result_saver.results_exist_and_should_be_kept(output_dir):
                log_message(
                    f"Already have results for {filename}, skipping...",
                    display_mode=False,
                )
                continue
            log_message(f"Processing {pdf_path}.", display_mode=False)
            leaflet_reader.convert_pdf_to_images(pdf_path, output_dir)
    return True


def process_all_directories(
    openai_client, categorizer, result_saver, display_mode=False
):
    all_directories = [entry.path for entry in os.scandir(PDF_DIR) if entry.is_dir()]
    for directory in all_directories:
        process_directory(
            directory, directory, openai_client, categorizer, result_saver, display_mode
        )
    # For any images that were added individually
    if len(get_all_image_paths(PDF_DIR)) > 0:
        process_directory(
            PDF_DIR, PDF_DIR, openai_client, categorizer, result_saver, display_mode
        )


def save_results(result_saver):
    result_saver.save_results(PDF_DIR)


def main(
    leaflet_reader: LeafletReader,
    openai_client: OpenAIClient,
    result_saver: ResultSaver,
    categorizer: ProductCategorizer,
    display_mode=False,
):
    leaflet_reader.download_leaflets(PDF_DIR)
    if process_pdfs(leaflet_reader, result_saver):
        process_all_directories(openai_client, categorizer, result_saver, display_mode)
        return save_results(result_saver)
    return None


def get_all_image_paths(directory: str):
    paths = []
    for file in os.listdir(directory):
        if file.lower().endswith((".png", ".jpg", ".jpeg")):
            paths.append(os.path.join(directory, file))
    return natsorted(paths)


def process_directory(
    directory: str,
    output_dir: str,
    openai_client: OpenAIClient,
    categorizer: ProductCategorizer,
    result_saver,
    display_mode=False,
):
    """Processes a directory by extracting product data, validating it, and optionally categorizing products."""

    if result_saver.results_exist_and_should_be_kept(PDF_DIR):
        log_message(f"Results already exist for {directory}, skipping...", display_mode)
        return True, pd.read_csv(os.path.join(directory, "results.csv"))

    log_message(f"Processing {directory} ...", display_mode)

    image_paths = get_all_image_paths(directory)
    all_products = []
    all_validation_results = [[] for _ in range(NUMBER_OF_CHATGPT_VALIDATIONS)]

    if display_mode:
        progress_bar = st.progress(0)

    # Process images and extract data
    for index, image_path in enumerate(image_paths):
        extracted_products, validation_results = process_image(
            image_path, openai_client
        )
        all_products.extend(extracted_products)

        for i in range(NUMBER_OF_CHATGPT_VALIDATIONS):
            all_validation_results[i].extend(validation_results[i])

        if display_mode:
            progress_bar.progress((index + 1) / len(image_paths))

    extracted_df = create_results_dataframe(all_products, all_validation_results)

    if NUMBER_OF_CHATGPT_VALIDATIONS > 0:
        compare_validation(extracted_df)

    output_path = result_saver.save(extracted_df, output_dir)
    log_message(f"Results from {directory} saved at: {output_path}", display_mode)

    return categorize_results(
        directory,
        extracted_df,
        categorizer,
        openai_client,
        result_saver,
        output_dir,
        display_mode,
    )


def process_image(image_path, openai_client):
    """Processes a single image, extracts product data, and validates it."""

    log_message(f"Extracting data from {image_path}", display_mode=False)

    with open(image_path, "rb") as image_file:
        image_data = image_file.read()
        response = openai_client.extract(image_data)
        time.sleep(SLEEP_TIME)

        validation_results = [
            validate_product_data(openai_client, response, image_data, i)
            for i in range(NUMBER_OF_CHATGPT_VALIDATIONS)
        ]

    extracted_products = [
        enrich_product_data(product, image_path) for product in response.all_products
    ]

    return extracted_products, validation_results


def validate_product_data(openai_client, response, image_data, validation_index):
    """Runs a single validation cycle for extracted product data."""

    log_message(f"Running validation: {validation_index + 1}", display_mode=False)

    validation_response = openai_client.validate_product_data(response, image_data)
    time.sleep(SLEEP_TIME)

    return [
        validation.model_dump()
        for validation in (validation_response.all_products or [])
    ]  # returns list of dictionaries with extracted data


def enrich_product_data(product, image_path):
    """Adds additional metadata to extracted product data."""
    return {
        **product.model_dump(),
        "folder": os.path.basename(os.path.dirname(image_path)),
        "page_number": os.path.basename(image_path),
    }


def create_results_dataframe(all_products, all_validation_results):
    """Creates and combines extracted and validated results into a single DataFrame."""

    extracted_df = pd.DataFrame(all_products).add_prefix("extracted_")

    for i, validation_data in enumerate(all_validation_results):
        validation_df = pd.DataFrame(validation_data).add_prefix(f"validated{i + 1}_")
        extracted_df = pd.concat([extracted_df, validation_df], axis=1)

    return extracted_df


def categorize_results(
    directory,
    extracted_df,
    categorizer,
    openai_client,
    result_saver,
    output_dir,
    display_mode,
):
    """Handles product categorization if enabled."""

    if not DO_CATEGORIZE:
        return True, extracted_df

    log_message(f"Categorizing products for {directory}", display_mode=False)
    categorized_df = categorizer.categorize_products(extracted_df, openai_client)
    append_metadata(categorized_df)

    output_path = result_saver.save(categorized_df, output_dir)
    log_message(
        f"Categorized results from {directory} saved at: {output_path}", display_mode
    )

    return True, categorized_df


def log_message(message, display_mode):
    """Logs messages to console or Streamlit depending on display mode."""
    if display_mode:
        st.write(message)
    print(message)


if __name__ == "__main__":
    arguments = parse_arguments()
    main(*initialize_components(arguments))
