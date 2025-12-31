from utils import get_api_key

API_KEY_ENV_VAR_NAME = "OPENAI_API_KEY"
EXTRACTED_DATA_COLUMNS = [
    "product_name",
    "original_price",
    "discount_price",
    "percentage_discount",
]
NUMBER_OF_CHATGPT_VALIDATIONS = 0
PDF_FILES_DIR = "pdf-files"

IMAGE_MODEL_SETTING_KEY = "image_model"
TEXT_MODEL_SETTING_KEY = "text_model"
API_KEY_SETTING_KEY = "api_key"

DEFAULT_SETTINGS = {
    IMAGE_MODEL_SETTING_KEY: "gpt-5-mini",
    TEXT_MODEL_SETTING_KEY: "gpt-5-mini",
    API_KEY_SETTING_KEY: get_api_key(),
}
