[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![GitHub issues](https://img.shields.io/github/issues/tristan-schwoerer/recipe_extractor?style=for-the-badge)](https://github.com/tristan-schwoerer/recipe_extractor/issues)
[![Version](https://img.shields.io/github/v/release/tristan-schwoerer/recipe_extractor?style=for-the-badge)](https://github.com/tristan-schwoerer/recipe_extractor/releases)

# Recipe Extractor

A Home Assistant custom integration that extracts structured recipe data (ingredients with quantities and units) from recipe websites using AI-powered extraction via Google's LangExtract library.

### Requirements

- Tested with Home Assistant version: `2025.11.2`
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/tristan-schwoerer/recipe_extractor`
6. Select category: "Integration"
7. Click "Add"
8. Search for "Recipe Extractor" and install it
9. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/recipe_extractor` folder to your Home Assistant `config/custom_components/` directory:

```bash
cd /config
mkdir -p custom_components
cp -r /path/to/custom_components/recipe_extractor custom_components/
```

2. Restart Home Assistant

## Setup

### Add Integration via UI

1. Go to **Settings** → **Devices & Services**
2. Click **+ ADD INTEGRATION**
3. Search for **"Recipe Extractor"**
4. Click to add it and configure in the setup dialog:
   - **API Key** (Required): Your Google Gemini API key
   - **Todo Entity** (Optional): Select a todo list to add ingredients to
   - **Model**: Choose the AI model (default: gemini-2.5-flash-lite)
   - **Convert Units**: Enable/disable automatic unit conversion (default: enabled)
5. Click **Submit** to complete the setup

You can reconfigure these options anytime by clicking **Configure** on the integration card.

### Alternative: Configure via configuration.yaml

You can also configure the integration via `configuration.yaml`. An API key must be configured either through the UI or in configuration.yaml. Note that UI configuration takes precedence over YAML configuration.

**Step 1:** Add your API key to `secrets.yaml`:

```yaml
# secrets.yaml
gemini_api_key: "your_google_api_key_here"
```

**Step 2:** Reference the secret in `configuration.yaml`:

```yaml
# configuration.yaml
recipe_extractor:
  api_key: !secret gemini_api_key
  model: "gemini-2.5-flash-lite"  # Optional: default AI model to use
  convert_units: true  # Optional: enable automatic unit conversion (default: true)
  todo_entity: "todo.shopping_list"  # Optional: default todo list entity for ingredients
```

**Configuration Options:**

- `api_key` (string, **required**): Your Google Gemini API key. Must be configured either here or in the UI. **Best practice:** Store in `secrets.yaml` and reference with `!secret`.
- `model` (string, optional): Default AI model. Options: `gemini-2.5-flash-lite`, `gemini-2.5-pro`, `gemini-2.0-flash-exp`. Default: `gemini-2.5-flash-lite`
- `convert_units` (boolean, optional): Automatically convert units to metric/imperial based on your Home Assistant settings. Default: `true`
- `todo_entity` (string, optional): Entity ID of a todo list to add ingredients to. Example: `todo.shopping_list`


### Available Models
In my testing I could use pretty much any gemini model with the free tier. This may not always be the case though 
- `gemini-2.5-flash-lite` (default) - Fast and cost-effective
- `gemini-2.5-pro` - More accurate but slower and more expensive

## Usage

### Service: `recipe_extractor.extract`

Extract a recipe from a URL.

**Service Data:**

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `url` | Yes | Recipe website URL | `https://www.chefkoch.de/rezepte/...` |
| `model` | No | AI model to use (uses configured default if not specified) | `gemini-2.5-pro` |

**Example Service Call (uses configured default model):**

```yaml
service: recipe_extractor.extract
data:
  url: "https://www.chefkoch.de/rezepte/187591080204663/Gewuerzkuchen-auf-m-Blech.html"
```

**Example Service Call (override with specific model):**

```yaml
service: recipe_extractor.extract
data:
  url: "https://www.valdemarsro.dk/krustader-med-rejesalat/"
  model: "gemini-2.5-pro"
```

### Events

The integration fires the following events:

#### `recipe_extractor_recipe_extracted`

Fired when a recipe is successfully extracted.

**Event Data:**

```yaml
url: "https://example.com/recipe"
recipe:
  title: "Chocolate Chip Cookies"
  ingredients:
    - name: "all-purpose flour"
      quantity: 2.25
      unit: "cups"
      group: null
    - name: "butter, softened"
      quantity: 1.0
      unit: "cup"
      group: null
    - name: "chocolate chips"
      quantity: 2.0
      unit: "cups"
      group: null
```

#### `recipe_extractor_extraction_failed`

Fired when recipe extraction fails.

**Event Data:**

```yaml
url: "https://example.com/recipe"
error: "Failed to extract recipe from URL"
```

## Automation Examples

### Example 1: Extract Recipe and Send to Telegram

```yaml
automation:
  - alias: "Extract Recipe from Telegram URL"
    trigger:
      - platform: event
        event_type: telegram_command
        event_data:
          command: '/recipe'
    action:
      - service: recipe_extractor.extract
        data:
          url: "{{ trigger.event.data.args }}"
      - wait_for_trigger:
          - platform: event
            event_type: recipe_extractor_recipe_extracted
        timeout: "00:02:00"
      - service: notify.telegram
        data:
          message: |
            **{{ wait.trigger.event.data.recipe.title }}**
            
            Ingredients ({{ wait.trigger.event.data.recipe.ingredients | length }}):
            {% for ingredient in wait.trigger.event.data.recipe.ingredients %}
            - {{ ingredient.quantity }} {{ ingredient.unit }} {{ ingredient.name }}
            {% endfor %}
```

### Example 2: Save Recipe to Shopping List

```yaml
automation:
  - alias: "Add Recipe Ingredients to Shopping List"
    trigger:
      - platform: event
        event_type: recipe_extractor_recipe_extracted
    action:
      - repeat:
          count: "{{ trigger.event.data.recipe.ingredients | length }}"
          sequence:
            - service: shopping_list.add_item
              data:
                name: "{{ trigger.event.data.recipe.ingredients[repeat.index - 1].quantity }} {{ trigger.event.data.recipe.ingredients[repeat.index - 1].unit }} {{ trigger.event.data.recipe.ingredients[repeat.index - 1].name }}"
```



## Supported Websites

The integration works with most recipe websites that use:
- Schema.org Recipe structured data (JSON-LD)
- Standard HTML recipe markup
- Common recipe container elements

## Development

### Adding Site-Specific Scrapers

To add a scraper for a specific website, edit `extractors/scraper.py`:

```python
def fetch_recipe_text(url: str) -> str:
    # Add your site check
    if 'yoursite.com' in url:
        return _fetch_yoursite_recipe(url)
    
    # ... rest of the function
```

### Testing

You can test the extraction outside of Home Assistant using the provided `test.py` script:

**Step 1:** Copy `.env.example` to `.env` and add your API key:

```bash
cp .env.example .env
# Edit .env and add your Google Gemini API key
```

**Step 2:** Run the test script:

```bash
python test.py
```

The script will extract a recipe and print the title and ingredients. You can modify the URL in `test.py` to test different recipe websites.

**Manual Testing:**

```python
import os
from dotenv import load_dotenv
from custom_components.recipe_extractor.extractors import RecipeExtractor, fetch_recipe_text

load_dotenv()

text = fetch_recipe_text("https://example.com/recipe")
extractor = RecipeExtractor(api_key=os.getenv("LANGEXTRACT_API_KEY"))
recipe = extractor.extract_recipe(text)

print(f"Title: {recipe.title}")
for ing in recipe.ingredients:
    print(f"  {ing.quantity} {ing.unit} {ing.name}")
```

## Dependencies

The integration automatically installs these Python packages:
- `langextract>=0.1.0` - AI-powered extraction
- `pydantic>=2.0.0` - Data validation
- `beautifulsoup4>=4.12.0` - HTML parsing
- `requests>=2.31.0` - HTTP requests
- `lxml>=4.9.0` - Fast XML/HTML processing

## Contributing

Contributions are welcome! Please check submit a pull request.

## Credits

Built with:
- [LangExtract](https://github.com/google/langextract) - AI extraction library
- [Home Assistant](https://www.home-assistant.io/) - Home automation platform
- [Google Gemini](https://ai.google.dev/) - AI models

## License

This integration is provided as-is under the MIT License.
