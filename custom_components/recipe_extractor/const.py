"""Constants for the Recipe Extractor integration."""

DOMAIN = "recipe_extractor"

# Configuration keys
CONF_API_KEY = "api_key"
CONF_MODEL = "model"

# Default values
DEFAULT_MODEL = "gemini-2.5-flash-lite"

# Service names
SERVICE_EXTRACT = "extract"

# Event names
EVENT_RECIPE_EXTRACTED = "recipe_extractor_recipe_extracted"
EVENT_EXTRACTION_FAILED = "recipe_extractor_extraction_failed"

# Data keys
DATA_URL = "url"
DATA_MODEL = "model"
DATA_RECIPE = "recipe"
DATA_ERROR = "error"
