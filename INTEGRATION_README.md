# Home Assistant Recipe Extractor Integration

This directory contains a complete Home Assistant custom integration for extracting recipe ingredients from websites.

## Quick Start

1. **Copy to Home Assistant:**
   ```bash
   cp -r custom_components/recipe_extractor /config/custom_components/
   ```

2. **Add to configuration.yaml:**
   ```yaml
   recipe_extractor:
     api_key: "YOUR_GOOGLE_API_KEY"
     model: "gemini-2.5-flash-lite"
   ```

3. **Restart Home Assistant**

4. **Use the service:**
   ```yaml
   service: recipe_extractor.extract
   data:
     url: "https://www.chefkoch.de/rezepte/..."
   ```

For complete documentation, see [custom_components/recipe_extractor/README.md](custom_components/recipe_extractor/README.md)

## What Changed from the Original Script?

### Structure Changes:
- Moved to Home Assistant's `custom_components` structure
- Split scraping logic into separate `scraper.py` module
- Added Home Assistant service registration
- Added event-driven architecture

### Key Files:
- `__init__.py` - Integration setup and service registration
- `manifest.json` - Integration metadata and dependencies
- `const.py` - Constants and configuration keys
- `services.yaml` - Service definitions for UI
- `extractors/recipe_extractor.py` - Core extraction logic (adapted from original)
- `extractors/scraper.py` - Web scraping utilities (adapted from original)
- `models/recipe.py` - Pydantic data models (unchanged)

### Usage Differences:

**Original Script:**
```bash
python recipe_converter.py "https://example.com/recipe"
```

**Home Assistant Integration:**
```yaml
service: recipe_extractor.extract
data:
  url: "https://example.com/recipe"
```

The integration fires events (`recipe_extractor_recipe_extracted`) that you can use in automations to:
- Send recipes to your phone
- Add ingredients to shopping lists
- Store recipes in files or databases
- Integrate with other Home Assistant services
