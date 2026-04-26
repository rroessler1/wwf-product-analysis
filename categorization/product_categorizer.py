# categorization/product_categorizer.py

import pandas as pd
from collections import defaultdict


from categorization.classification_is_grill_system_prompt import (
    CLASSIFICATION_IS_GRILL_SYSTEM_PROMPT_GEFLUEGEL,
    CLASSIFICATION_IS_GRILL_SYSTEM_PROMPT_SCHWEIN,
    CLASSIFICATION_IS_GRILL_SYSTEM_PROMPT_RIND,
    CLASSIFICATION_IS_GRILL_SYSTEM_PROMPT_GEMISCHT,
    CLASSIFICATION_IS_GRILL_SYSTEM_PROMPT_KAESE,
    CLASSIFICATION_IS_GRILL_SYSTEM_PROMPT_FISCH,
    CLASSIFICATION_IS_GRILL_SYSTEM_PROMPT_VEGAN,
    CLASSIFICATION_IS_GRILL_SYSTEM_PROMPT_GEMUESE,
    CLASSIFICATION_IS_GRILL_SYSTEM_PROMPT_OTHERS,
)
from llms.models import ProductCategory, FinalProductCategory
from llms.openai_client import OpenAIClient
from typing import Any, cast

from utils import run_parallel_batches_with_retry


class ProductCategorizer:

    def __init__(self):
        self.categorization_columns = []

    def classify_is_grill_batch(
        self,
        product_names: list[str],
        category: str,
        openai_client: OpenAIClient,
    ) -> list[dict]:
        """
        Classifies a batch of product names for 'is_grill' using a category-specific system prompt.

        For the given category (string), it determines the corresponding system prompt
        (expected to be defined as CLASSIFICATION_IS_GRILL_SYSTEM_PROMPT_{Category in CAPS})
        and then uses the ProductCategory's classify_products_is_grill() method to perform
        the classification.

        Parameters:
            product_names (list[str]): List of product names.
            category (str): The product category (string representation, e.g. "Geflügel").

        Returns:
            list[dict]: Each dictionary contains 'is_grill' (bool) and 'certainty_is_grill' (float).
        """
        # Map the category value to its corresponding system prompt.
        SYSTEM_PROMPT_MAPPING = {
            ProductCategory.GEFUEGEL.value: CLASSIFICATION_IS_GRILL_SYSTEM_PROMPT_GEFLUEGEL,
            ProductCategory.SCHWEIN.value: CLASSIFICATION_IS_GRILL_SYSTEM_PROMPT_SCHWEIN,
            ProductCategory.RIND.value: CLASSIFICATION_IS_GRILL_SYSTEM_PROMPT_RIND,
            ProductCategory.GEMISCHT.value: CLASSIFICATION_IS_GRILL_SYSTEM_PROMPT_GEMISCHT,
            ProductCategory.KAESE.value: CLASSIFICATION_IS_GRILL_SYSTEM_PROMPT_KAESE,
            ProductCategory.FISCH_MEERESFRUECHTE.value: CLASSIFICATION_IS_GRILL_SYSTEM_PROMPT_FISCH,
            ProductCategory.VEGETARISCH_VEGAN.value: CLASSIFICATION_IS_GRILL_SYSTEM_PROMPT_VEGAN,
            ProductCategory.GRILLGEMUESE.value: CLASSIFICATION_IS_GRILL_SYSTEM_PROMPT_GEMUESE,
            ProductCategory.OTHERS.value: CLASSIFICATION_IS_GRILL_SYSTEM_PROMPT_OTHERS,
        }
        system_prompt = SYSTEM_PROMPT_MAPPING.get(
            category, CLASSIFICATION_IS_GRILL_SYSTEM_PROMPT_OTHERS
        )

        # Call the classification method defined on the enum member.
        # This method is expected to return a ClassificationIsGrillResponseFormat instance.
        response = openai_client.classify_products_is_grill(
            product_names, system_prompt
        )

        # Extract and convert the results to a list of dictionaries.
        results = []
        for result in response.results:
            results.append(
                {
                    "is_grill": result.is_grill,
                    "certainty_is_grill": result.certainty_is_grill,
                }
            )
        return results

    def categorize_products(
        self, data: pd.DataFrame, openai_client: OpenAIClient
    ) -> pd.DataFrame:
        """
        Categorizes products in two steps:
          1. Batch categorization using OpenAI for determining the product category.
          2. For each category, group products in batches of up to 5 and use ChatGPT to determine 'is_grill'.

        Returns:
            pd.DataFrame: DataFrame with additional columns for 'category',
                        'certainty_fleischsorte', 'is_grill', and 'certainty_is_grill'.
        """
        product_names = list(data["extracted_product_name"])
        step_size = 5

        # Step 1: Categorize in parallel with deterministic batch IDs and 429 retry.
        category_batch_jobs = []
        for batch_number, i in enumerate(range(0, len(product_names), step_size)):
            names = product_names[i : i + step_size]
            category_batch_jobs.append(
                {
                    "batch_id": f"cat-{batch_number:06d}",
                    "indices": list(range(i, i + len(names))),
                    "names": names,
                }
            )

        def categorize_batch(job: dict):
            response = openai_client.categorize_products(job["names"])
            if len(response.results) != len(job["indices"]):
                raise ValueError(
                    f"Batch {job['batch_id']} returned {len(response.results)} "
                    f"results for {len(job['indices'])} inputs"
                )
            return response.results

        categorized_batches = run_parallel_batches_with_retry(
            category_batch_jobs,
            categorize_batch,
        )

        category_results: list[dict[str, Any] | None] = [None] * len(product_names)
        for job in category_batch_jobs:
            batch_results = cast(list, categorized_batches[job["batch_id"]])
            for idx, result in zip(job["indices"], batch_results):
                category_results[idx] = {
                    "category": result.fleischsorte.value,
                    "certainty_fleischsorte": result.certainty_fleischsorte,
                }

        if any(cat_info is None for cat_info in category_results):
            raise RuntimeError("Some category results are missing after categorization")

        # Check that the number of category results matches the input data.
        if len(data.index) != len(category_results):
            print(
                f"Length of the data {len(data.index)} and the assigned categories {len(category_results)} do not match!"
            )
            return data

        # Step 2: Group products by category to classify 'is_grill' in batches.
        category_groups = defaultdict(list)
        # Build groups: key = category, value = list of tuples (index, product_name)
        for idx, cat_info in enumerate(category_results):
            if cat_info is None:
                raise RuntimeError(f"Category result missing at index {idx}")
            category = cat_info["category"]
            category_groups[category].append((idx, product_names[idx]))

        grill_batch_jobs = []
        for batch_number, (category, items) in enumerate(category_groups.items()):
            for i in range(0, len(items), step_size):
                batch = items[i : i + step_size]
                indices, names = zip(*batch)
                grill_batch_jobs.append(
                    {
                        "batch_id": f"grill-{batch_number:06d}-{i:06d}",
                        "category": category,
                        "indices": list(indices),
                        "names": list(names),
                    }
                )

        def classify_is_grill(job: dict):
            batch_results = self.classify_is_grill_batch(
                job["names"], job["category"], openai_client
            )
            if len(batch_results) != len(job["indices"]):
                raise ValueError(
                    f"Batch {job['batch_id']} returned {len(batch_results)} "
                    f"results for {len(job['indices'])} inputs"
                )
            return batch_results

        grill_batches = run_parallel_batches_with_retry(
            grill_batch_jobs,
            classify_is_grill,
        )

        for job in grill_batch_jobs:
            batch_results = cast(list, grill_batches[job["batch_id"]])
            for idx_item, result in zip(job["indices"], batch_results):
                category_results[idx_item]["is_grill"] = result["is_grill"]
                category_results[idx_item]["certainty_is_grill"] = result[
                    "certainty_is_grill"
                ]

        # Merge the results with the original DataFrame.
        res_df = pd.DataFrame(category_results)
        data = pd.concat([data, res_df], axis=1)
        self.categorization_columns.extend(
            ["category", "certainty_fleischsorte", "is_grill", "certainty_is_grill"]
        )

        self.reduce_categorization_dimensions(data)
        return data

    def reduce_categorization_dimensions(self, data):
        data["final_category"] = data.apply(
            self.convert_two_column_categorization_to_one_column_categorization,
            axis=1,
        )
        data["final_certainty"] = data.apply(
            self.convert_two_column_certainty_to_one_column_certainty,
            axis=1,
        )

    @staticmethod
    def convert_two_column_categorization_to_one_column_categorization(
        row: pd.Series,
    ) -> str:
        if (not row["is_grill"]) or row["category"] == ProductCategory.OTHERS.value:
            return FinalProductCategory.NO_GRILL_PRODUCT.value
        else:
            return FinalProductCategory(row["category"]).value

    @staticmethod
    def convert_two_column_certainty_to_one_column_certainty(row: pd.Series) -> float:
        return min(row["certainty_fleischsorte"], row["certainty_is_grill"])
