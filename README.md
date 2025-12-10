[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![GitHub issues](https://img.shields.io/github/issues/tristan-schwoerer/recipe_extractor?style=for-the-badge)](https://github.com/tristan-schwoerer/recipe_extractor/issues)
[![Version](https://img.shields.io/github/v/release/tristan-schwoerer/recipe_extractor?style=for-the-badge)](https://github.com/tristan-schwoerer/recipe_extractor/releases)

# Recipe Extractor

A Home Assistant custom integration that extracts structured recipe data (ingredients with quantities and units) from recipe websites. It first attempts to parse [schema.org/Recipe](https://schema.org/Recipe) JSON-LD structured data, and falls back to AI-powered extraction via Google's LangExtract library when structured data is not available (which is unfortunately quite often the case).

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
   - **Default Todo List Entity** (Optional): Select a default todo list to add ingredients to
   - **Default AI Model**: Choose the AI model (default: gemini-2.5-flash)
   - **Convert to Metric Units**: Enable/disable automatic imperial to metric conversion (default: enabled)
5. Click **Submit** to complete the setup

You can reconfigure these options anytime by clicking **Configure** on the integration card.

> **Note:** This integration only supports configuration through the UI. YAML configuration is not supported.

### Available Models
In my testing I could use pretty much any gemini model with the free tier. This may not always be the case though.
- `gemini-2.5-flash-lite` - Fastest and cheapest (may occasionally struggle with output formatting)
- `gemini-2.5-flash` (default) - Balanced speed and accuracy
- `gemini-2.5-pro` - Most accurate but slower and more expensive

### Unit Conversion

When **Convert to Metric Units** is enabled (default), the integration automatically converts:
- **Volume**: cups, fluid ounces, pints, quarts, gallons → ml/liters
- **Weight**: ounces, pounds → grams/kilograms  
- **Temperature**: Fahrenheit → Celsius
- **Spoon measurements**: Normalized to standard abbreviations (tsp, tbsp) but NOT converted to ml
- **Multi-language normalization**: German (TL→tsp, EL→tbsp), Danish (tsk→tsp, spsk→tbsp), Swedish/Norwegian (msk→tbsp)

## Usage

### Custom Lovelace Card

A companion custom card is available in a separate repository: [Recipe Extractor Card](https://github.com/tristan-schwoerer/recipe_extractor_card)

Install it via HACS → Frontend → Custom repositories to get a simple UI for extracting recipes directly from your dashboard.

## Services

The integration provides three services for different use cases:

### Service: `recipe_extractor.extract`

Extract a recipe from a URL and return the structured data. Use this when you want to process the recipe data in automations or scripts.

**Service Data:**

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `url` | Yes | Recipe website URL | `https://www.chefkoch.de/rezepte/...` |
| `model` | No | AI model to use (uses configured default if not specified) | `gemini-2.5-pro` |

**Response Data:**

Returns a dictionary containing:
- `title`: Recipe name
- `servings`: Number of servings (if available)
- `ingredients`: List of ingredients with `name`, `quantity`, `unit`, and optional `group`

**Example Service Call:**

```yaml
service: recipe_extractor.extract
data:
  url: "https://www.chefkoch.de/rezepte/187591080204663/Gewuerzkuchen-auf-m-Blech.html"
response_variable: recipe_data
```

### Service: `recipe_extractor.extract_to_list`

Extract a recipe and automatically add ingredients to a todo list. This is a convenience service that combines extraction and adding to list in one call.

**Service Data:**

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `url` | Yes | Recipe website URL | `https://www.example.com/recipe` |
| `todo_entity` | No | Todo list entity ID (uses configured default if not specified) | `todo.shopping_list` |
| `target_servings` | No | Scale recipe to this number of servings | `6` |
| `model` | No | AI model to use (uses configured default if not specified) | `gemini-2.5-pro` |

**Example Service Call:**

```yaml
service: recipe_extractor.extract_to_list
data:
  url: "https://www.example.com/chocolate-chip-cookies"
  todo_entity: todo.shopping_list
  target_servings: 12
```

### Service: `recipe_extractor.add_to_list`

Add a pre-extracted recipe to a todo list. Use this when you already have recipe data from the `extract` service or an event.

**Service Data:**

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `recipe` | Yes | Recipe data dictionary from extraction | See example below |
| `todo_entity` | No | Todo list entity ID (uses configured default if not specified) | `todo.shopping_list` |
| `target_servings` | No | Scale recipe to this number of servings | `4` |

**Example Service Call:**

```yaml
service: recipe_extractor.add_to_list
data:
  recipe: "{{ recipe_data }}"
  todo_entity: todo.shopping_list
  target_servings: 4
```

## Events

The integration fires the following events that you can use in automations:

### `recipe_extractor_extraction_started`

Fired when recipe extraction begins.

**Event Data:**

```yaml
url: "https://example.com/recipe"
```

### `recipe_extractor_method_detected`

Fired when the extraction method is determined (JSON-LD structured data vs. AI extraction).

**Event Data:**

```yaml
url: "https://example.com/recipe"
extraction_method: "jsonld"  # or "ai"
message: "Found JSON-LD structured data"
used_ai: false
```

### `recipe_extractor_recipe_extracted`

Fired when a recipe is successfully extracted.

**Event Data:**

```yaml
url: "https://example.com/recipe"
recipe:
  title: "Chocolate Chip Cookies"
  servings: 24
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
# Optional: only present when added to list via extract_to_list service
todo_entity: "todo.shopping_list"
```

### `recipe_extractor_extraction_failed`

Fired when recipe extraction fails.

**Event Data:**

```yaml
url: "https://example.com/recipe"
error: "Failed to extract recipe from URL"
```

## Automation Examples

### Example 1: Extract Recipe and Add to Shopping List

Use the convenience service to extract and add in one call:

```yaml
automation:
  - alias: "Extract Recipe from URL Input"
    trigger:
      - platform: state
        entity_id: input_text.recipe_url
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.state | length > 0 }}"
    action:
      - service: recipe_extractor.extract_to_list
        data:
          url: "{{ states('input_text.recipe_url') }}"
          todo_entity: todo.shopping_list
          target_servings: 4  # Optional: scale to 4 servings
```

### Example 2: Extract Recipe with Response Variable

Extract a recipe and use the response data in your automation:

```yaml
automation:
  - alias: "Extract and Notify"
    trigger:
      - platform: event
        event_type: telegram_command
        event_data:
          command: '/recipe'
    action:
      - service: recipe_extractor.extract
        data:
          url: "{{ trigger.event.data.args }}"
        response_variable: recipe_data
      - service: notify.telegram
        data:
          message: |
            **{{ recipe_data.title }}**
            {% if recipe_data.servings %}Servings: {{ recipe_data.servings }}{% endif %}
            
            Ingredients ({{ recipe_data.ingredients | length }}):
            {% for ingredient in recipe_data.ingredients %}
            - {{ ingredient.quantity }} {{ ingredient.unit }} {{ ingredient.name }}
            {% endfor %}
```

### Example 3: Monitor Extraction Progress

React to different stages of recipe extraction:

```yaml
automation:
  - alias: "Recipe Extraction Status Updates"
    trigger:
      - platform: event
        event_type: 
          - recipe_extractor_extraction_started
          - recipe_extractor_method_detected
          - recipe_extractor_recipe_extracted
          - recipe_extractor_extraction_failed
    action:
      - choose:
          - conditions:
              - condition: template
                value_template: "{{ trigger.event.event_type == 'recipe_extractor_extraction_started' }}"
            sequence:
              - service: notify.mobile_app
                data:
                  message: "Extracting recipe from {{ trigger.event.data.url }}..."
          - conditions:
              - condition: template
                value_template: "{{ trigger.event.event_type == 'recipe_extractor_method_detected' }}"
            sequence:
              - service: notify.mobile_app
                data:
                  message: "{{ trigger.event.data.message }} (AI: {{ trigger.event.data.used_ai }})"
          - conditions:
              - condition: template
                value_template: "{{ trigger.event.event_type == 'recipe_extractor_recipe_extracted' }}"
            sequence:
              - service: notify.mobile_app
                data:
                  message: "Successfully extracted: {{ trigger.event.data.recipe.title }}"
          - conditions:
              - condition: template
                value_template: "{{ trigger.event.event_type == 'recipe_extractor_extraction_failed' }}"
            sequence:
              - service: notify.mobile_app
                data:
                  message: "Failed to extract recipe: {{ trigger.event.data.error }}"

```

### Example 4: Scale Recipe Based on Guest Count

Automatically scale recipes based on number of guests:

```yaml
automation:
  - alias: "Scale Recipe to Guest Count"
    trigger:
      - platform: state
        entity_id: input_text.recipe_url
    action:
      - service: recipe_extractor.extract_to_list
        data:
          url: "{{ states('input_text.recipe_url') }}"
          todo_entity: todo.shopping_list
          target_servings: "{{ states('input_number.guest_count') | int }}"
```



## Features

### Supported Websites

The integration works with most recipe websites:
- **Best performance**: Websites with [schema.org/Recipe](https://schema.org/Recipe) JSON-LD structured data (instant extraction, no AI needed)
- **AI fallback**: Any website with recipe content (uses AI to extract ingredients from HTML, takes ~10s)

### Recipe Scaling

All services that add ingredients to todo lists support the `target_servings` parameter:
- Automatically scales ingredient quantities based on recipe servings
- Works with fractional servings (e.g., 2.5 servings)
- Requires the original recipe to specify servings count

**Example:**
```yaml
# Original recipe: 4 servings with 2 cups flour
# target_servings: 8
# Result: 4 cups flour added to list
```

### Multi-Language Support

The integration handles recipes in multiple languages:
- **English**: Full support for US and UK measurements
- **German**: TL→tsp, EL→tbsp, Messerspitze→pinch
- **Danish**: tsk→tsp, spsk→tbsp, knsp→pinch  
- **Swedish/Norwegian**: msk→tbsp
- Unicode fractions: ½, ⅓, ⅔, ¼, ¾, etc.

## Development

### Testing

You can test the extraction outside of Home Assistant using the provided `test.py` script:

**Step 1:** Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Step 2:** Copy `.env.example` to `.env` and add your API key:

```bash
cp .env.example .env
# Edit .env and add your Google Gemini API key
```

**Step 3:** Run the test script:

```bash
python test.py
```

The script will extract a recipe and print the title and ingredients. You can modify the URL in `test.py` to test different recipe websites.


## Technical Details

### Dependencies

The integration automatically installs the Python packages listed in [`requirements.txt`](requirements.txt). Home Assistant itself is provided by the runtime environment and doesn't need to be installed separately.

### How It Works

1. **Web Scraping**: Downloads the recipe page HTML content
2. **JSON-LD Detection**: First attempts to find and parse structured Schema.org/Recipe data
3. **AI Fallback**: If no structured data found, uses LangExtract with Google Gemini to extract recipe information from HTML text
4. **Data Validation**: Validates and structures recipe data using Pydantic models
5. **Unit Conversion**: Optionally converts imperial units to metric
6. **Todo Integration**: Formats and adds ingredients to Home Assistant todo lists

## Contributing

Contributions are welcome! Please check submit a pull request.

## Credits

Built with:
- [LangExtract](https://github.com/google/langextract) - AI extraction library
- [Home Assistant](https://www.home-assistant.io/) - Home automation platform
- [Google Gemini](https://ai.google.dev/) - AI models

## License

This integration is provided as-is under the MIT License.
