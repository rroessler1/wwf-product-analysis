"""
Tests how many products are extracted per page.
"""

import os
import pandas as pd

from file_downloaders import NoopDownloader
from leaflet_reader import LeafletReader
from main_pipeline import Pipeline

TEST_DATA_DIR = "tests/data/"
RESULTS_FILE = os.path.join(TEST_DATA_DIR, "items_per_page_expected_results.csv")


def load_gt(path: str) -> pd.DataFrame:
    """Load ground truth file and do any necessary preprocessing."""
    df = pd.read_csv(path)
    df.set_index("extracted_page_number", inplace=True)
    return df


def get_image_results_df() -> pd.DataFrame:
    """
    Runs the actual pipeline only for the image extraction step.
    """
    args = {"overwrite_results": True, "use_test_client": False, "no_categorize": True}
    pipeline = Pipeline(
        args,
        leaflet_reader=LeafletReader(file_downloader=NoopDownloader()),
        pdf_dir=TEST_DATA_DIR,
        display_mode=False,
    )
    return pipeline.main()


def calculate_results(actual: pd.DataFrame, expected: pd.DataFrame) -> None:
    """
    This knows how to compare the actual results with the expected results.
    It prints the user-friendly results.
    """
    columns = ["extracted_product_name", "extracted_page_number"]
    actual_counts = actual[columns].groupby("extracted_page_number").count()

    actual_counts, expected = actual_counts.align(expected, fill_value=0)
    differences = actual_counts.subtract(expected, fill_value=0)
    total_absolute_difference = differences.abs().sum().sum()

    total_num_products = expected["extracted_product_name"].sum()
    print("Statistics:")
    print(f"{total_absolute_difference} mistakes, {total_num_products} products")
    print(
        f"Error percentage: {total_absolute_difference / total_num_products * 100:.2f}%"
    )
    print("Differences:")
    print(differences)


def run():
    """Run test."""
    gt = load_gt(RESULTS_FILE)
    results = get_image_results_df()
    calculate_results(results, gt)


if __name__ == "__main__":
    run()
