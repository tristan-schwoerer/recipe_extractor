"""Constants for the Recipe Extractor integration."""

DOMAIN = "recipe_extractor"

# Configuration and option keys (unified)
CONF_API_KEY = "api_key"
CONF_MODEL = "model"
CONF_TODO_ENTITY = "default_todo_entity"
CONF_DEFAULT_MODEL = "default_model"
CONF_CONVERT_UNITS = "convert_to_metric"

# Default values
DEFAULT_MODEL = "gemini-2.5-flash-lite"
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_TEXT_LENGTH = 8000

# Available models
AVAILABLE_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
]

# Service names
SERVICE_EXTRACT = "extract"
SERVICE_EXTRACT_TO_LIST = "extract_to_list"

# Event names
EVENT_RECIPE_EXTRACTED = "recipe_extractor_recipe_extracted"
EVENT_EXTRACTION_FAILED = "recipe_extractor_extraction_failed"

# Service data keys
DATA_URL = "url"
DATA_MODEL = "model"
DATA_RECIPE = "recipe"
DATA_ERROR = "error"
DATA_TODO_ENTITY = "todo_entity"
