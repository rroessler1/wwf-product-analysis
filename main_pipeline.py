import os
import time

import argparse
from datetime import datetime
from natsort import natsorted
import pandas as pd
import streamlit as st

from categorization.product_categorizer import ProductCategorizer
from leaflet_reader import LeafletReader
from llms.openai_client import OpenAIClient
from llms.mock_client import MockLLM
from result_saver import ResultSaver
from settings import NUMBER_OF_CHATGPT_VALIDATIONS
from utils import get_api_key
from validation.validation_comparison import compare_validation


PDF_DIR = "pdf-files"
URL = "https://drive.google.com/drive/folders/1AR2_592V_x4EF97FHv4UPN5zdLTXpVB3"
DO_DOWNLOAD = False  # just used for testing, saves time
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
        help="Overwrite existing results if they exist."
    )
    return parser.parse_args()


def initialize_components(args):
    leaflet_reader = LeafletReader(download_url=URL)
    openai_client = MockLLM() if USE_TEST_LLM_CLIENT else OpenAIClient(api_key=get_api_key())
    result_saver = ResultSaver(overwrite_results=args.overwrite_results)
    categorizer = ProductCategorizer()
    return leaflet_reader, openai_client, result_saver, categorizer


def download_pdfs(leaflet_reader):
    if DO_DOWNLOAD:
        leaflet_reader.download_leaflets(PDF_DIR)


def process_pdfs(leaflet_reader, result_saver):
    if result_saver.results_exist_and_should_be_kept(PDF_DIR):
        print(f"Already found a results file: [{os.path.join(PDF_DIR, result_saver.output_file_name)}], nothing to do.")
        print("If you'd like new results, delete or rename the results file and rerun the script.")
        return False

    for filename in os.listdir(PDF_DIR):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(PDF_DIR, filename)
            pdf_name, _ = os.path.splitext(os.path.basename(filename))
            output_dir = os.path.join(PDF_DIR, pdf_name)
            if result_saver.results_exist_and_should_be_kept(PDF_DIR):
                print(f"Already have results for {filename}, skipping...")
                continue
            print(f"Processing {pdf_path}.")
            leaflet_reader.convert_pdf_to_images(pdf_path, output_dir)
    return True


def process_all_directories(openai_client, categorizer, result_saver):
    all_directories = [entry.path for entry in os.scandir(PDF_DIR) if entry.is_dir()]
    for directory in all_directories:
        process_directory(directory, directory, openai_client, categorizer, result_saver)


def save_results(result_saver):
    result_saver.save_results(PDF_DIR)


def main():
    args = parse_arguments()
    leaflet_reader, openai_client, result_saver, categorizer = initialize_components(args)

    download_pdfs(leaflet_reader)
    if process_pdfs(leaflet_reader, result_saver):
        process_all_directories(openai_client, categorizer, result_saver)
        save_results(result_saver)


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
    displaymood=False,
):
    if result_saver.results_exist_and_should_be_kept(PDF_DIR):
        if displaymood:
            st.write(f"Results already exist for {directory}, skipping...")
        else:
            print(f"Already have results for {directory}, skipping...")
        # Construct the path to the CSV file
        csv_path = os.path.join(directory, "results.csv")
        # Read the CSV file into a DataFrame
        csv_df = pd.read_csv(csv_path)
        return True, csv_df

    image_paths = get_all_image_paths(directory)
    all_products = []

    if displaymood:
        progress_bar = st.progress(0)
        total_directories = len(image_paths)

    all_validation_results = [[] for i in range(NUMBER_OF_CHATGPT_VALIDATIONS)]
    # Call LLMs for all images for one PDF at a time
    for i, image_path in enumerate(image_paths):
        with open(image_path, "rb") as image_file:
            if displaymood:
                st.write(f"Extracting data from {image_path}")
            else:
                print(f"Extracting data from {image_path}")
            response = openai_client.extract(image_file.read())
            time.sleep(SLEEP_TIME)

            # Validate each extracted product from the response
            for i in range(NUMBER_OF_CHATGPT_VALIDATIONS):  # Number of Checkings
                print(f"Running validation: {i}")
                # Validate the product data
                image_file.seek(0)  # Reset file pointer to beginning for reuse
                validation_response = openai_client.validate_product_data(
                    response, image_file.read()
                )
                time.sleep(SLEEP_TIME)

                # Append the validation result to the validation_results list
                if validation_response:
                    for validation in validation_response.all_products:
                        validation_as_dict = validation.model_dump()
                        all_validation_results[i].append(validation_as_dict)

            for product in response.all_products:
                product_as_dict = product.model_dump()
                # TODO: might need a better way to identify this than just folder
                # or at least, make sure the folder isn't just "Denner", but has a date or calendar week
                product_as_dict["folder"] = os.path.basename(directory)
                product_as_dict["page_number"] = os.path.basename(image_path)
                all_products.append(product_as_dict)

        if displaymood:
            progress_bar.progress((i) / total_directories)

    # Create a DataFrame for extracted results
    extracted_df = pd.DataFrame(all_products)
    extracted_df = extracted_df.add_prefix(
        "extracted_"
    )  # Prefix columns with 'extracted_'

    # Add validation results to the DataFrame
    for i in range(NUMBER_OF_CHATGPT_VALIDATIONS):
        validation_df = pd.DataFrame(all_validation_results[i])
        validation_df = validation_df.add_prefix(
            f"validated{i + 1}_"
        )  # Prefix columns with 'validatedX_'

        # Combine extracted data with validation data
        extracted_df = pd.concat([extracted_df, validation_df], axis=1)

    if NUMBER_OF_CHATGPT_VALIDATIONS > 0:
        compare_validation(extracted_df)

    output_path = result_saver.save(extracted_df, output_dir)
    print(f"Results from {directory} saved at: {output_path}")

    if DO_CATEGORIZE:
        # Categorize products
        print(f"Categorizing products for {directory}")
        categorized_df = categorizer.categorize_products(extracted_df, openai_client)
        append_metadata(categorized_df)

        # Save categorized products to an Excel file
        output_path = result_saver.save(categorized_df, output_dir)
        print(f"Categorized results from {directory} saved at: {output_path}")
        return True, categorized_df

    return True, extracted_df


if __name__ == "__main__":
    main()
