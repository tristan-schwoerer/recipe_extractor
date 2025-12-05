[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![GitHub issues](https://img.shields.io/github/issues/tristan-schwoerer/recipe_extractor?style=for-the-badge)](https://github.com/tristan-schwoerer/recipe_extractor/issues)
[![Version](https://img.shields.io/github/v/release/tristan-schwoerer/recipe_extractor?style=for-the-badge)](https://github.com/tristan-schwoerer/recipe_extractor/releases)

# Recipe Extractor

A Home Assistant custom integration that extracts structured recipe data (ingredients with quantities and units) from recipe websites using AI-powered extraction via Google's LangExtract library.

### Requirements

- Minimum required Home Assistant version: `2023.1`
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

## Features

- 🥘 **Extract Structured Recipe Data**: Automatically extracts ingredients with quantities, units, and groups from recipe URLs
- 🌍 **Multi-Language Support**: Works with recipes in English, German, Danish, and more
- 🎯 **Site-Specific Scrapers**: Optimized scrapers for sites with poor HTML structure
- 🤖 **AI-Powered**: Uses Google's Gemini models for intelligent ingredient parsing
- 🔔 **Event-Driven**: Fires Home Assistant events when recipes are extracted
- 🔧 **Service Integration**: Easily callable from automations and scripts

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

### Step 1: Add Integration via UI

1. Go to **Settings** → **Devices & Services**
2. Click **+ ADD INTEGRATION**
3. Search for **"Recipe Extractor"**
4. Click to add it and follow the setup dialog

### Step 2: Configure API Key

Add the following to your `configuration.yaml`:

```yaml
recipe_extractor:
  api_key: "your_google_api_key_here"
  model: "gemini-2.5-flash-lite"  # Optional, this is the default
```

### Step 3: Restart Home Assistant

Restart Home Assistant to load the configuration.

### Getting a Google API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key (free tier available)
3. Copy the key and add it to your `configuration.yaml`

### Available Models

- `gemini-2.5-flash-lite` (default) - Fast and cost-effective
- `gemini-2.5-pro` - More accurate but slower and more expensive
- `gemini-2.0-flash-exp` - Experimental flash model

## Usage

### Service: `recipe_extractor.extract`

Extract a recipe from a URL.

**Service Data:**

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `url` | Yes | Recipe website URL | `https://www.chefkoch.de/rezepte/...` |
| `model` | No | AI model to use (default: gemini-2.5-flash-lite) | `gemini-2.5-pro` |

**Example Service Call:**

```yaml
service: recipe_extractor.extract
data:
  url: "https://www.chefkoch.de/rezepte/187591080204663/Gewuerzkuchen-auf-m-Blech.html"
```

**Example Service Call with Custom Model:**

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

### Example 3: Store Recipe in Text File

```yaml
automation:
  - alias: "Save Recipe to File"
    trigger:
      - platform: event
        event_type: recipe_extractor_recipe_extracted
    action:
      - service: shell_command.save_recipe
        data:
          title: "{{ trigger.event.data.recipe.title }}"
          ingredients: "{{ trigger.event.data.recipe.ingredients | tojson }}"

shell_command:
  save_recipe: >
    echo "{{ title }}" > /config/recipes/{{ title | slugify }}.txt &&
    echo "{{ ingredients }}" >> /config/recipes/{{ title | slugify }}.txt
```

### Example 4: Use with Input Text Helper

```yaml
# configuration.yaml
input_text:
  recipe_url:
    name: Recipe URL
    max: 255

# automation
automation:
  - alias: "Extract Recipe from Input"
    trigger:
      - platform: state
        entity_id: input_text.recipe_url
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.state | regex_match('https?://') }}"
    action:
      - service: recipe_extractor.extract
        data:
          url: "{{ states('input_text.recipe_url') }}"
```

## Supported Websites

The integration works with most recipe websites that use:
- Schema.org Recipe structured data (JSON-LD)
- Standard HTML recipe markup
- Common recipe container elements

### Sites with Specialized Scrapers:
- voresmad.dk
- More can be added by extending `extractors/scraper.py`

### Examples of Tested Sites:
- chefkoch.de
- valdemarsro.dk
- allrecipes.com
- bbc.co.uk/food
- food.com

## Troubleshooting

### Enable Debug Logging

Add to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.recipe_extractor: debug
```

### Common Issues

1. **"Failed to extract text from URL"**
   - The website may be blocking automated access
   - Try a different recipe URL
   - Check if the site requires JavaScript rendering

2. **"Failed to extract recipe structure"**
   - The AI model couldn't parse the recipe
   - Try using `gemini-2.5-pro` for better accuracy
   - The webpage might not contain a proper recipe

3. **Import errors after installation**
   - Restart Home Assistant completely
   - Check that all files are in the correct location
   - Verify file permissions

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

You can test the extraction outside of Home Assistant:

```python
from custom_components.recipe_extractor.extractors import RecipeExtractor, fetch_recipe_text

# Fetch and extract
text = fetch_recipe_text("https://example.com/recipe")
extractor = RecipeExtractor(api_key="your_key")
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

Contributions are welcome! Please check out the [issues](https://github.com/tristan-schwoerer/recipe_extractor/issues) page or submit a pull request.

If you have:
- 🐛 Found a bug → [Open an issue](https://github.com/tristan-schwoerer/recipe_extractor/issues/new)
- 💡 Feature suggestion → [Start a discussion](https://github.com/tristan-schwoerer/recipe_extractor/discussions)
- 🌐 A new site-specific scraper → [Submit a PR](https://github.com/tristan-schwoerer/recipe_extractor/pulls)

## Support

For questions and support:
- 📖 Check the documentation above
- 🐛 [Report bugs](https://github.com/tristan-schwoerer/recipe_extractor/issues)
- 💬 [Ask questions](https://github.com/tristan-schwoerer/recipe_extractor/discussions)
- 📝 Check the Home Assistant logs for error messages
- 🔍 Enable debug logging for detailed information

## Credits

Built with:
- [LangExtract](https://github.com/google/langextract) - AI extraction library
- [Home Assistant](https://www.home-assistant.io/) - Home automation platform
- [Google Gemini](https://ai.google.dev/) - AI models

## License

This integration is provided as-is under the MIT License.
