from typing import List
from unittest.mock import MagicMock

from .openai_client import OpenAIClient
from .models import (
    Results,
    CategorizationResult,
    GroceryProduct,
    ProductCategory,
    ClassificationResponseFormat,
)


class MockLLM:
    def __init__(self):
        self._client = OpenAIClient("fake-key")
        self._client.extract = MagicMock(return_value=self._results())
        self._client.validate_product_data = MagicMock(return_value=self._results())
        self._client.validate_product_data = MagicMock(return_value=self._results())
        self._client.categorize_products = MagicMock(
            side_effect=self._categorization_results
        )
        self._num_items_seen = 0

    def _results(self) -> Results:
        p1 = GroceryProduct(
            product_name="meat",
            original_price="1.99",
            discount_price="1.59",
            percentage_discount=20,
            discount_details="pro 100g",
        )
        p2 = GroceryProduct(
            product_name="cheese",
            original_price="2.99",
            discount_price="1.49",
            percentage_discount=50,
        )
        return Results(all_products=[p1, p2])

    def _categorization_results(self, products: List[str]) -> ClassificationResponseFormat:
        results = []
        for _ in products:
            results.append(
                CategorizationResult(
                    fleischsorte=list(ProductCategory)[
                        self._num_items_seen % len(ProductCategory)
                    ],
                    certainty_fleischsorte=(self._num_items_seen % len(ProductCategory))
                    * 10,
                    is_grill=self._num_items_seen % 2,
                    certainty_is_grill=(self._num_items_seen % len(ProductCategory))
                    * 10,
                )
            )
            self._num_items_seen += 1
        return ClassificationResponseFormat(results=results)

    def __getattr__(self, name):
        # Delegate attribute access to the MagicMock
        return getattr(self._client, name)
