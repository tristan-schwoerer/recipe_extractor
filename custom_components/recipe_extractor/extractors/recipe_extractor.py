"""
Recipe extraction engine using Google's LangExtract.

This module handles the core extraction logic, converting unstructured
recipe text into structured Recipe objects.
"""
import json
import logging
import re
from typing import Optional

import langextract as lx
from langextract.data import ExampleData, Extraction

from ..models.recipe import Recipe, Ingredient

_LOGGER = logging.getLogger(__name__)


class RecipeExtractor:
    """Extracts structured recipe data from unstructured text using LangExtract."""
    
    def __init__(self, api_key: str, model: str = "gemini-2.5-pro"):
        """Initialize the recipe extractor.
        
        Args:
            api_key: API key for the language model
            model: The model to use for extraction
        """
        self.api_key = api_key
        self.model = model
        _LOGGER.info(f"Initialized RecipeExtractor with model: {model}")
    
    def _parse_ingredient_groups(self, text: str) -> dict:
        """Parse ingredient group structure from formatted text.
        
        This only works with specially formatted text (from site-specific scrapers)
        that has "Ingredients:" followed by group headers with colons and indented
        ingredient lines starting with "  -".
        
        Args:
            text: Formatted recipe text with group headers
            
        Returns:
            Dict mapping ingredient names to their group names, or empty dict if no structured format detected
        """
        if '\nIngredients:\n' not in text:
            return {}
        
        ingredient_to_group = {}
        current_group = None
        in_ingredients_section = False
        
        for line in text.split('\n'):
            line_stripped = line.strip()
            
            if line_stripped == 'Ingredients:':
                in_ingredients_section = True
                continue
            
            if in_ingredients_section and line_stripped.lower().startswith('instructions'):
                break
            
            if not in_ingredients_section:
                continue
            
            if line_stripped and line_stripped.endswith(':') and not line.startswith('  ') and not line_stripped.startswith('-'):
                current_group = line_stripped.rstrip(':')
                continue
            
            if line.startswith('  -'):
                ingredient_line = line_stripped.lstrip('- ').strip()
                parts = ingredient_line.split()
                if len(parts) >= 2:
                    ingredient_name = ' '.join(parts[1:]) if len(parts) > 1 else parts[0]
                    if current_group and ingredient_name:
                        ingredient_to_group[ingredient_name.lower()] = current_group
        
        return ingredient_to_group
    
    def extract_recipe(self, text: str) -> Optional[Recipe]:
        """Extract recipe information from text.
        
        Args:
            text: The raw recipe text
            
        Returns:
            A Recipe object with extracted information, or None if extraction fails
        """
        _LOGGER.info(f"Extracting recipe from text (length: {len(text)} chars)")
        
        if len(text.strip()) < 100:
            _LOGGER.warning("Text too short for meaningful recipe extraction")
            return None
        
        ingredient_groups = self._parse_ingredient_groups(text)
        
        try:
            prompt_description = """
Extract recipe information from the provided text in any language (English, German, Danish, etc.). 

Identify and extract:
1. The recipe title
2. ALL ingredients with their quantities and units

For each ingredient, break it down into:
- name: the ingredient name INCLUDING any preparation notes or annotations (e.g., "Salz, gehäuft", "Peperoni, eingelegte", "Wasser, lauwarmes", "butter, softened", "Salz und Pfeffer")
- quantity: the numeric amount (e.g., 2.5, 250, 0.5), or null if not specified
- unit: ONLY the base measurement unit WITHOUT annotations (e.g., "g", "ml", "TL", "EL", "Pck.", "cups", "tsp"), or null if not specified
  Do NOT include preparation notes in the unit field (e.g., use "TL" not "TL, gehäuft")
- group: optional group/section name if ingredients are organized into clear subsections (e.g., "For the dough", "Für den Boden"). Use null if not applicable.

CRITICAL RULES:
- DO NOT TRANSLATE INGREDIENTS - Keep ingredient names in their ORIGINAL LANGUAGE as written in the recipe
- If the recipe is in Danish, keep ingredient names in Danish (e.g., "krustader", "ørredrogn", "rejer")
- If the recipe is in German, keep ingredient names in German (e.g., "Mehl", "Zucker", "Eier")
- Annotations like "gehäuft" (heaped), "eingelegt" (pickled), "gerieben" (grated), "lauwarm" (lukewarm) should be part of the ingredient NAME, not the unit
- The unit field should contain ONLY standard measurement units  
- Extract EVERY ingredient from the ingredient list, even if they don't have a quantity or unit
- For ingredients without quantity/unit, set both to null
- Keep the full specific ingredient name as written in the recipe
- Extract each ingredient ONLY ONCE - do not create duplicate entries or translated versions
- IMPORTANT: If an ingredient line contains BOTH metric and imperial measurements (e.g., "1.75kg/ 3.5lb" or "20g/ 1 tbsp"), extract ONLY the FIRST measurement listed (metric). Do NOT create separate entries for each unit system.

Return the extracted information in the following JSON structure:
{
  "extractions": [
    {
      "extraction_class": "Recipe",
      "extraction_text": "{
        \\"title\\": \\"Recipe Title\\",
        \\"ingredients\\": [
          {
            \\"name\\": \\"ingredient name\\",
            \\"quantity\\": 2.0,
            \\"unit\\": \\"cups\\",
            \\"group\\": \\"For the dough\\"
          }
        ]
      }"
    }
  ]
}
"""
            
            examples = [
                ExampleData(
                    text="""
Chocolate Chip Cookies

Ingredients:
- 2 1/4 cups all-purpose flour
- 1 tsp baking soda
- 1 tsp salt
- 1 cup butter, softened
- 3/4 cup granulated sugar
- 2 large eggs
- 2 cups chocolate chips
- Powdered Sugar
- Baking paper
""",
                    extractions=[
                        Extraction(
                            extraction_class="Recipe",
                            extraction_text="""{
  "title": "Chocolate Chip Cookies",
  "ingredients": [
    {"name": "all-purpose flour", "quantity": 2.25, "unit": "cups", "group": null},
    {"name": "baking soda", "quantity": 1.0, "unit": "tsp", "group": null},
    {"name": "salt", "quantity": 1.0, "unit": "tsp", "group": null},
    {"name": "butter, softened", "quantity": 1.0, "unit": "cup", "group": null},
    {"name": "granulated sugar", "quantity": 0.75, "unit": "cup", "group": null},
    {"name": "eggs", "quantity": 2.0, "unit": "large", "group": null},
    {"name": "chocolate chips", "quantity": 2.0, "unit": "cups", "group": null},
    {"name": "Powdered Sugar", "quantity": null, "unit": null, "group": null},
    {"name": "Baking paper", "quantity": null, "unit": null, "group": null}
  ]
}"""
                        )
                    ]
                ),
                ExampleData(
                    text="""
Gewürzkuchen

Zutaten:
- 4 Ei(er)
- 300 g Zucker
- 350 g Mehl
- 1 Pck. Backpulver
- 250 ml Olivenöl
- 1 TL, gehäuft Salz
- 2 Paprikaschote(n), rote
- Petersilie
- Salz und Pfeffer
- Oregano
""",
                    extractions=[
                        Extraction(
                            extraction_class="Recipe",
                            extraction_text="""{
  "title": "Gewürzkuchen",
  "ingredients": [
    {"name": "Ei(er)", "quantity": 4.0, "unit": null, "group": null},
    {"name": "Zucker", "quantity": 300.0, "unit": "g", "group": null},
    {"name": "Mehl", "quantity": 350.0, "unit": "g", "group": null},
    {"name": "Backpulver", "quantity": 1.0, "unit": "Pck.", "group": null},
    {"name": "Olivenöl", "quantity": 250.0, "unit": "ml", "group": null},
    {"name": "Salz, gehäuft", "quantity": 1.0, "unit": "TL", "group": null},
    {"name": "Paprikaschote(n), rote", "quantity": 2.0, "unit": null, "group": null},
    {"name": "Petersilie", "quantity": null, "unit": null, "group": null},
    {"name": "Salz und Pfeffer", "quantity": null, "unit": null, "group": null},
    {"name": "Oregano", "quantity": null, "unit": null, "group": null}
  ]
}"""
                        )
                    ]
                ),
                ExampleData(
                    text="""
Recipe: Pizza Dough

Ingredients:

For the dough:
  - 500g Flour
  - 300ml Water, lukewarm
  - 1TL Salt
  - 7g Yeast

For the topping:
  - 200g Tomato sauce
  - 300g Mozzarella
  - Basil
  - Olive oil
""",
                    extractions=[
                        Extraction(
                            extraction_class="Recipe",
                            extraction_text="""{
  "title": "Pizza Dough",
  "ingredients": [
    {"name": "Flour", "quantity": 500.0, "unit": "g", "group": "For the dough"},
    {"name": "Water, lukewarm", "quantity": 300.0, "unit": "ml", "group": "For the dough"},
    {"name": "Salt", "quantity": 1.0, "unit": "TL", "group": "For the dough"},
    {"name": "Yeast", "quantity": 7.0, "unit": "g", "group": "For the dough"},
    {"name": "Tomato sauce", "quantity": 200.0, "unit": "g", "group": "For the topping"},
    {"name": "Mozzarella", "quantity": 300.0, "unit": "g", "group": "For the topping"},
    {"name": "Basil", "quantity": null, "unit": null, "group": "For the topping"},
    {"name": "Olive oil", "quantity": null, "unit": null, "group": "For the topping"}
  ]
}"""
                        )
                    ]
                ),
                ExampleData(
                    text="""
Recipe: Beef Stew

Ingredients:
- 1.5kg/ 3.3lb beef chuck, cubed
- 500ml/ 2 cups beef broth
- 3 tbsp/ 45g butter
- 2 large onions
- Salt and pepper

For serving:
- Fresh parsley
""",
                    extractions=[
                        Extraction(
                            extraction_class="Recipe",
                            extraction_text="""{
  "title": "Beef Stew",
  "ingredients": [
    {"name": "beef chuck, cubed", "quantity": 1.5, "unit": "kg", "group": null},
    {"name": "beef broth", "quantity": 500.0, "unit": "ml", "group": null},
    {"name": "butter", "quantity": 3.0, "unit": "tbsp", "group": null},
    {"name": "onions", "quantity": 2.0, "unit": "large", "group": null},
    {"name": "Salt and pepper", "quantity": null, "unit": null, "group": null},
    {"name": "Fresh parsley", "quantity": null, "unit": null, "group": "For serving"}
  ]
}"""
                        )
                    ]
                )
            ]
            
            result = lx.extract(
                text_or_documents=text,
                prompt_description=prompt_description,
                model_id=self.model,
                examples=examples,
                api_key=self.api_key
            )
            
            if result and hasattr(result, 'extractions') and result.extractions:
                main_recipe = None
                max_ingredients = 0
                all_recipes = []
                
                for extraction in result.extractions:
                    if extraction.extraction_class == "Recipe":
                        try:
                            extraction_text = extraction.extraction_text
                            
                            try:
                                recipe_data = json.loads(extraction_text)
                            except json.JSONDecodeError as e:
                                _LOGGER.warning(f"JSON parse error, attempting to fix: {e}")
                                fixed_text = extraction_text
                                
                                fixed_text = re.sub(
                                    r'("(?:quantity|unit|name)":\s*(?:null|"[^"]*"|\d+(?:\.\d+)?))\s*\n\s*\]',
                                    r'\1}\n  ]',
                                    fixed_text
                                )
                                
                                try:
                                    recipe_data = json.loads(fixed_text)
                                    _LOGGER.info("Successfully repaired malformed JSON (incomplete object)")
                                except json.JSONDecodeError:
                                    open_brackets = fixed_text.count('[')
                                    close_brackets = fixed_text.count(']')
                                    open_braces = fixed_text.count('{')
                                    close_braces = fixed_text.count('}')
                                    
                                    if close_braces < open_braces:
                                        fixed_text += '}' * (open_braces - close_braces)
                                    if close_brackets < open_brackets:
                                        fixed_text += ']' * (open_brackets - close_brackets)
                                    
                                    try:
                                        recipe_data = json.loads(fixed_text)
                                        _LOGGER.info("Successfully repaired malformed JSON (missing closures)")
                                    except:
                                        _LOGGER.error("Could not repair JSON, skipping this extraction")
                                        raise
                            
                            if not recipe_data.get('title'):
                                _LOGGER.debug("Skipping partial extraction without title")
                                continue
                            
                            ingredients = []
                            for ing in recipe_data.get('ingredients', []):
                                name = ing.get('name', '')
                                quantity = ing.get('quantity')
                                unit = ing.get('unit')
                                group = ing.get('group')
                                
                                if unit and ',' in unit:
                                    parts = unit.split(',', 1)
                                    base_unit = parts[0].strip()
                                    annotation = parts[1].strip()
                                    
                                    if annotation and annotation.lower() not in name.lower():
                                        name = f"{name}, {annotation}"
                                    unit = base_unit
                                
                                if unit:
                                    unit = unit.replace('(n)', '').replace('(', '').replace(')', '')
                                
                                if not group and ingredient_groups:
                                    name_lower = name.lower()
                                    for parsed_name, parsed_group in ingredient_groups.items():
                                        if parsed_name in name_lower or name_lower.startswith(parsed_name.split(',')[0].strip()):
                                            group = parsed_group
                                            break
                                
                                ingredient = Ingredient(
                                    name=name,
                                    quantity=quantity,
                                    unit=unit,
                                    group=group
                                )
                                ingredients.append(ingredient)
                            
                            recipe = Recipe(
                                title=recipe_data.get('title', ''),
                                ingredients=ingredients
                            )
                            
                            _LOGGER.info(f"Found recipe: {recipe.title}")
                            _LOGGER.info(f"  - {len(recipe.ingredients)} ingredients")
                            
                            if len(recipe.ingredients) == 0 or len(recipe.title) > 100:
                                continue
                            
                            all_recipes.append(recipe)
                            
                            if len(recipe.ingredients) > max_ingredients:
                                main_recipe = recipe
                                max_ingredients = len(recipe.ingredients)
                            
                        except Exception as e:
                            _LOGGER.error(f"Error parsing recipe extraction: {e}")
                            _LOGGER.error(f"Extraction text: {extraction.extraction_text}")
                
                if main_recipe and len(all_recipes) > 1:
                    _LOGGER.info(f"Multiple extractions found: {len(all_recipes)} recipe extractions")
                    _LOGGER.info(f"Main recipe (selected): '{main_recipe.title}' with {len(main_recipe.ingredients)} ingredients")
                elif main_recipe:
                    _LOGGER.info(f"Selected recipe: {main_recipe.title} with {len(main_recipe.ingredients)} ingredients")
                
                return main_recipe
            
            _LOGGER.warning("No recipe extractions found in the result")
            return None
            
        except Exception as e:
            _LOGGER.error(f"Error during recipe extraction: {str(e)}", exc_info=True)
            return None
