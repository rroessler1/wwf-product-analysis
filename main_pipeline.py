import os
import time

import argparse
from datetime import datetime
import pandas as pd
import streamlit as st

from categorization.product_categorizer import ProductCategorizer
from file_downloaders import NoopDownloader
from leaflet_reader import LeafletReader
from llms.openai_client import OpenAIClient
from llms.mock_client import MockLLM
from result_saver import ResultSaver
from settings import NUMBER_OF_CHATGPT_VALIDATIONS
import utils
from utils import log_message
from validation.validation_comparison import compare_validation


SLEEP_TIME = 0  # TODO: test that we're not being rate limited using their API key


class Pipeline:
    def __init__(
        self,
        args: dict,
        leaflet_reader: LeafletReader,
        pdf_dir: str = "pdf-files",
        display_mode: bool = False,
    ) -> None:
        self.args = args
        self.pdf_dir = pdf_dir
        self.display_mode = display_mode
        self.leaflet_reader = leaflet_reader
        self.openai_client = (
            MockLLM()
            if self.args["use_test_client"]
            else OpenAIClient(api_key=utils.get_api_key())
        )
        self.result_saver = ResultSaver(
            overwrite_results=self.args["overwrite_results"]
        )
        self.categorizer = ProductCategorizer()

    def append_metadata(self, df: pd.DataFrame):
        df["date_collected"] = datetime.now().strftime("%Y-%m-%d")
        df["calendar_week"] = datetime.now().isocalendar().week

    def process_pdfs(self):
        if self.result_saver.results_exist_and_should_be_kept(self.pdf_dir):
            log_message(
                f"Already found a results file: [{os.path.join(self.pdf_dir, self.result_saver.output_file_name)}], nothing to do.",
                display_mode=False,
            )
            log_message(
                "If you'd like new results, delete or rename the results file and rerun the script.",
                display_mode=False,
            )
            return False

        for filename in os.listdir(self.pdf_dir):
            if filename.endswith(".pdf"):
                pdf_path = os.path.join(self.pdf_dir, filename)
                pdf_name, _ = os.path.splitext(os.path.basename(filename))
                output_dir = os.path.join(self.pdf_dir, pdf_name)
                if self.result_saver.results_exist_and_should_be_kept(output_dir):
                    log_message(
                        f"Already have results for {filename}, skipping...",
                        display_mode=False,
                    )
                    continue
                log_message(f"Processing {pdf_path}.", display_mode=False)
                self.leaflet_reader.convert_pdf_to_images(pdf_path, output_dir)
        return True

    def process_all_directories(self):
        all_directories = [
            entry.path for entry in os.scandir(self.pdf_dir) if entry.is_dir()
        ]
        for directory in all_directories:
            self.process_directory(
                directory,
                directory,
            )
        # For any images that were added individually
        if len(utils.get_all_image_paths(self.pdf_dir)) > 0:
            self.process_directory(self.pdf_dir, self.pdf_dir)

    def main(self) -> pd.DataFrame | None:
        self.leaflet_reader.download_leaflets(self.pdf_dir)
        if self.process_pdfs():
            self.process_all_directories()
            return self.result_saver.save_results(self.pdf_dir)
        return None

    def process_directory(self, directory: str, output_dir: str):
        """Processes a directory by extracting product data, validating it, and optionally categorizing products."""

        if self.result_saver.results_exist_and_should_be_kept(self.pdf_dir):
            log_message(
                f"Results already exist for {directory}, skipping...", self.display_mode
            )
            return True, pd.read_csv(os.path.join(directory, "results.csv"))

        log_message(f"Processing {directory} ...", self.display_mode)

        image_paths = utils.get_all_image_paths(directory)
        all_products = []
        all_validation_results = [[] for _ in range(NUMBER_OF_CHATGPT_VALIDATIONS)]

        if self.display_mode:
            progress_bar = st.progress(0)

        # Process images and extract data
        for index, image_path in enumerate(image_paths):
            extracted_products, validation_results = self.process_image(image_path)
            all_products.extend(extracted_products)

            for i in range(NUMBER_OF_CHATGPT_VALIDATIONS):
                all_validation_results[i].extend(validation_results[i])

            if self.display_mode:
                progress_bar.progress((index + 1) / len(image_paths))

        extracted_df = self.create_results_dataframe(
            all_products, all_validation_results
        )

        if NUMBER_OF_CHATGPT_VALIDATIONS > 0:
            compare_validation(extracted_df)

        output_path = self.result_saver.save(extracted_df, output_dir)
        log_message(
            f"Results from {directory} saved at: {output_path}", self.display_mode
        )

        return self.categorize_results(directory, extracted_df, output_dir)

    def process_image(self, image_path):
        """Processes a single image, extracts product data, and validates it."""

        log_message(f"Extracting data from {image_path}", display_mode=False)

        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
            response = self.openai_client.extract(image_data)
            time.sleep(SLEEP_TIME)

            validation_results = [
                self.validate_product_data(response, image_data, i)
                for i in range(NUMBER_OF_CHATGPT_VALIDATIONS)
            ]

        extracted_products = [
            self.enrich_product_data(product, image_path)
            for product in response.all_products
        ]

        return extracted_products, validation_results

    def validate_product_data(self, response, image_data, validation_index):
        """Runs a single validation cycle for extracted product data."""

        log_message(f"Running validation: {validation_index + 1}", display_mode=False)

        validation_response = self.openai_client.validate_product_data(
            response, image_data
        )
        time.sleep(SLEEP_TIME)

        return [
            validation.model_dump()
            for validation in (validation_response.all_products or [])
        ]  # returns list of dictionaries with extracted data

    def enrich_product_data(self, product, image_path):
        """Adds additional metadata to extracted product data."""
        return {
            **product.model_dump(),
            "folder": os.path.basename(os.path.dirname(image_path)),
            "page_number": os.path.basename(image_path),
        }

    def create_results_dataframe(self, all_products, all_validation_results):
        """Creates and combines extracted and validated results into a single DataFrame."""

        extracted_df = pd.DataFrame(all_products).add_prefix("extracted_")

        for i, validation_data in enumerate(all_validation_results):
            validation_df = pd.DataFrame(validation_data).add_prefix(
                f"validated{i + 1}_"
            )
            extracted_df = pd.concat([extracted_df, validation_df], axis=1)

        return extracted_df

    def categorize_results(self, directory, extracted_df, output_dir):
        """Handles product categorization if enabled."""

        if self.args["no_categorize"]:
            return True, extracted_df

        log_message(f"Categorizing products for {directory}", display_mode=False)
        categorized_df = self.categorizer.categorize_products(
            extracted_df, self.openai_client
        )
        self.append_metadata(categorized_df)

        output_path = self.result_saver.save(categorized_df, output_dir)
        log_message(
            f"Categorized results from {directory} saved at: {output_path}",
            self.display_mode,
        )

        return True, categorized_df


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Runs the main script to download PDFs, split them, and write the results."
    )
    parser.add_argument(
        "--overwrite-results",
        action="store_true",
        help="Overwrite existing results if they exist.",
    )
    parser.add_argument(
        "--no-categorize",
        action="store_true",
        help="Disable product categorization.",
    )
    parser.add_argument(
        "--use-test-client",
        action="store_true",
        help="Overwrite existing results if they exist.",
    )
    # This does convert the dashes to underscores
    return vars(parser.parse_args())


if __name__ == "__main__":
    pipeline = Pipeline(
        args=parse_arguments(),
        leaflet_reader=LeafletReader(file_downloader=NoopDownloader()),
    )
    pipeline.main()
