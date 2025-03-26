# openai_integration/models.py
from enum import Enum

from pydantic import BaseModel
from typing import List, Optional


class GroceryProduct(BaseModel):
    """
    Model for a grocery product extracted from the leaflet.

    Attributes:
        product_name (str): The name of the product.
        original_price (Optional[str]): The original price of the product.
        discount_price (Optional[str]): The discounted price of the product.
        percentage_discount (Optional[float]): The discount percentage.
        discount_details (Optional[str]): Additional discount details, if any.
    """

    product_name: str
    original_price: Optional[str] = None
    discount_price: Optional[str] = None
    percentage_discount: Optional[float] = None
    discount_details: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.product_name}, {self.original_price}, {self.discount_price}, {self.percentage_discount}"


class Results(BaseModel):
    """
    Model for storing all extracted grocery products from the leaflet.

    Attributes:
        all_products (List[GroceryProduct]): List of extracted products.
    """

    all_products: List[GroceryProduct]

    def __str__(self) -> str:
        output = "product_name, original_price, discount_price, percentage_discount"
        for product in self.all_products:
            output = output + "\n" + product.__str__()

        return output


# Define the categories for Fleischsorte
class ProductCategory(Enum):
    GEFUEGEL = "Geflügel"
    SCHWEIN = "Schwein"
    RIND = "Rind"
    GEMISCHT = "Gemischt"
    KAESE = "Käse"
    FISCH_MEERESFRUECHTE = "Fisch & Meeresfrüchte"
    VEGETARISCH_VEGAN = "Vegetarisches oder veganes Ersatzprodukt"
    GRILLGEMUESE = "Grillgemüse"
    OTHERS = "other"


class FinalProductCategory(Enum):
    GEFUEGEL = "Geflügel"
    SCHWEIN = "Schwein"
    RIND = "Rind"
    GEMISCHT = "Gemischt"
    KAESE = "Käse"
    FISCH_MEERESFRUECHTE = "Fisch & Meeresfrüchte"
    VEGETARISCH_VEGAN = "Vegetarisches oder veganes Ersatzprodukt"
    GRILLGEMUeSE = "Grillgemüse"
    NO_GRILL_PRODUCT = "Kein Grillprodukt"


# Define the output class for the categorization result
class CategorizationResult(BaseModel):
    fleischsorte: ProductCategory  # Category from the ProductCategory Enum
    certainty_fleischsorte: (
        float  # Certainty percentage for Fleischsorte classification (0-100)
    )

class ClassificationIsGrillResult(BaseModel):
    is_grill: bool  # Whether the product is considered a grill product
    certainty_is_grill: (
        float  # Certainty percentage for is_grill classification (0-100)
    )


class CategorizationResponseFormat(BaseModel):
    results: List[CategorizationResult]  # List of categorization results (max 5)

class ClassificationIsGrillResponseFormat(BaseModel):
    results: List[ClassificationIsGrillResult]