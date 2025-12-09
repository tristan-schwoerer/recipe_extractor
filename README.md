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

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=tristan-schwoerer&repository=recipe_extractor&category=integration)

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
   - **Model**: Choose the AI model (default: gemini-2.5-flash)
   - **Convert Units**: Enable/disable automatic unit conversion (default: enabled)
5. Click **Submit** to complete the setup

You can reconfigure these options anytime by clicking **Configure** on the integration card.

> **Note:** This integration only supports configuration through the UI. YAML configuration is not supported.

### Available Models
In my testing I could use pretty much any gemini model with the free tier. This may not always be the case though 
- `gemini-2.5-flash-lite` - Fast and cost-effective
- `gemini-2.5-flash` (default) - Balanced speed and accuracy
- `gemini-2.5-pro` - More accurate and comprehensive
- `gemini-2.5-pro` - More accurate but slower and more expensive

## Usage

### Custom Lovelace Card

A companion custom card is available in a separate repository: [Recipe Extractor Card](https://github.com/tristan-schwoerer/recipe_extractor_card)

Install it via HACS → Frontend → Custom repositories to get a simple UI for extracting recipes directly from your dashboard.

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
