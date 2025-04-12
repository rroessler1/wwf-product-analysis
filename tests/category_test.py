import os
import pandas as pd


import utils
from categorization.product_categorizer import ProductCategorizer
from llms.openai_client import OpenAIClient

TEST_DATA_DIR = "tests/data/"
TEST_FILE = os.path.join(TEST_DATA_DIR, "category_test.csv")


def read_file() -> pd.DataFrame:
    return pd.read_csv(TEST_FILE)

def categorize(df: pd.DataFrame) -> pd.DataFrame:
    categorizer = ProductCategorizer()
    openai_client = OpenAIClient(api_key=utils.get_api_key())
    categorized_df = categorizer.categorize_products(
        df, openai_client
    )
    return categorized_df

def check_results(categorized_df: pd.DataFrame) -> pd.DataFrame:
    categorized_df["check_category"] = categorized_df["category"] == categorized_df["solution_category"]
    categorized_df["check_is_grill"] = categorized_df["is_grill"] == categorized_df["solution_is_grill"]
    return categorized_df

def calculate_statistics(df: pd.DataFrame):
    def print_match_stats(label, series):
        total = len(series)
        correct = series.sum()
        accuracy = correct / total if total > 0 else 0
        print(f"{label}: {correct}/{total} correct ({accuracy:.2%})")

    print("=== Overall Match Stats ===")
    print_match_stats("Category Match", df["check_category"])
    print_match_stats("Is Grill Match", df["check_is_grill"])
    print()

    print("=== Conditional on solution_is_grill == True ===")
    df_true = df[df["solution_is_grill"] == True]
    print_match_stats("Category Match", df_true["check_category"])
    print_match_stats("Is Grill Match", df_true["check_is_grill"])
    print()

    print("=== Conditional on solution_is_grill == False ===")
    df_false = df[df["solution_is_grill"] == False]
    print_match_stats("Category Match", df_false["check_category"])
    print_match_stats("Is Grill Match", df_false["check_is_grill"])


def show_mismatches(df):
    answer = input("Do you want to see rows with mismatches? (yes/no): ").strip().lower()

    if answer in ["yes", "y"]:
        mismatches = df[(df["check_category"] == False) | (df["check_is_grill"] == False)]
        if mismatches.empty:
            print("No mismatches found.")
        else:
            mismatches = mismatches.sort_values(
                by=["check_category", "check_is_grill"],
                ascending=[True, True]  # False (mismatch) comes first
            )

            print(f"\nShowing {len(mismatches)} mismatched rows:\n")
            print(mismatches[["extracted_product_name", "category", "is_grill", "solution_category" ,"solution_is_grill", "check_category", "check_is_grill"]])
    else:
        print("Okay, not showing mismatches.")


def run():
    df = read_file()
    categorized_df = categorize(df)
    categorized_df = check_results(categorized_df)
    calculate_statistics(categorized_df)
    show_mismatches(categorized_df)

def convert_excel_to_csv():
    df = pd.read_excel("tests/data/category_test.xlsx")
    df.to_csv(TEST_FILE, index=False)

if __name__ == "__main__":
    convert_excel_to_csv()
    run()