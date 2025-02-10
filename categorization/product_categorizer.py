# categorization/product_categorizer.py

import pandas as pd

from llms.models import ProductCategory, FinalProductCategory
from llms.openai_client import OpenAIClient


class ProductCategorizer:
    def __init__(self):
        self.categorization_columns = []

    def categorize_products(
        self, data: pd.DataFrame, openai_client: OpenAIClient
    ) -> pd.DataFrame:
        """
        Categorizes products
        Parameters:
            image (Image): Image data for potential future use (e.g., OCR or visual categorization).
            data (pd.DataFrame): DataFrame containing product information from OpenAI extraction.
            openai_client (OpenAIClient): OpenAI Client for interacting with OpenAI API.

        Returns:
            pd.DataFrame: DataFrame with an added 'Category' ,'is_grill' ,'certainty_fleischsorte' ,'certainty_is_grill' column for product categorization.
        """

        product_categories: list[ProductCategory] = []
        product_names = list(data["extracted_product_name"])
        step_size = 5
        for i in range(0, len(product_names), step_size):
            categorization_results = openai_client.categorize_products(
                product_names[i : i + step_size]
            )
            product_categories.extend(categorization_results)

        res_df = []

        for _, results in product_categories:
            for result in results:
                res_df.append(
                    {
                        "category": result.fleischsorte.value,  # Using .value to get the string representation of the category
                        "certainty_fleischsorte": result.certainty_fleischsorte,
                        "is_grill": result.is_grill,
                        "certainty_is_grill": result.certainty_is_grill,
                    }
                )

        if len(data.index) == len(res_df):
            res_df = pd.DataFrame(res_df)

            data = pd.concat([data, res_df], axis=1)
            self.categorization_columns.append("category")
            self.categorization_columns.append("is_grill")
            self.categorization_columns.append("certainty_fleischsorte")
            self.categorization_columns.append("certainty_is_grill")

        else:
            # TODO: maybe we should also have ChatGPT return the original product name,
            # so if the length doesn't match, we can still include the data for most of them.
            print(
                f"Length of the data {len(data.index)} and the assigned categories {len(product_categories)} do not match!"
            )

        self.reduce_categorization_dimensions(data)

        return data

    def reduce_categorization_dimensions(self, data):
        data["final_category"] = data.apply(
            lambda row: self.convert_two_column_categorization_to_one_column_categorization(
                row
            ),
            axis=1,
        )
        data["final_certainty"] = data.apply(
            lambda row: self.convert_two_column_certainty_to_one_column_certainty(row),
            axis=1,
        )

    @staticmethod
    def convert_two_column_categorization_to_one_column_categorization(
        row: pd.Series,
    ) -> FinalProductCategory:
        if (not row["is_grill"]) or row["category"] == ProductCategory.OTHERS:
            return FinalProductCategory.NO_GRILL_PRODUCT.value
        else:
            return FinalProductCategory(row["category"]).value

    @staticmethod
    def convert_two_column_certainty_to_one_column_certainty(row: pd.Series) -> float:
        return min(row["certainty_fleischsorte"], row["certainty_is_grill"])


def main():
    data = pd.read_csv("test_LLM/prompt_tuning_results.csv")
    print("len input Data is", data.shape)
    data["extracted_product_name"] = data["Produkt"]
    test_data = data.iloc[:5].reset_index(drop=True)
    PC = ProductCategorizer()

    api_key_path = "openai_api_key.txt"
    with open(api_key_path, "r") as file:
        api_key = file.readline().strip()

    openai_client = OpenAIClient(api_key=api_key)

    cat_data = PC.categorize_products(test_data, openai_client)
    cat_data.to_csv("test_LLM/prompt_tuning_results344.csv")
