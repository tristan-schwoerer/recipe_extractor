"""
Recipe extraction engine using Google's LangExtract.

This module handles the core extraction logic, converting unstructured
recipe text into structured Recipe objects.
"""
import json
import re
from typing import Optional

import langextract as lx
from langextract import tokenizer

from ..models.recipe import Recipe, Ingredient
from .prompts import EXTRACTION_PROMPT
from .examples import RECIPE_EXAMPLES


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
        # Use UnicodeTokenizer for multi-language support (fixes alignment warnings)
        self.tokenizer = tokenizer.UnicodeTokenizer()
    
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
        if len(text.strip()) < 100:
            return None
        
        ingredient_groups = self._parse_ingredient_groups(text)
        
        try:
            result = lx.extract(
                text_or_documents=text,
                prompt_description=EXTRACTION_PROMPT,
                model_id=self.model,
                examples=RECIPE_EXAMPLES,
                tokenizer=self.tokenizer,  # Use UnicodeTokenizer for multi-language support
                api_key=self.api_key
            )
            
            if result and hasattr(result, 'extractions') and result.extractions:
                # New approach: extract individual title and ingredient entities with attributes
                title = None
                ingredients = []
                
                for extraction in result.extractions:
                    if extraction.extraction_class == "title":
                        title = extraction.extraction_text
                    
                    elif extraction.extraction_class == "ingredient":
                        # Get attributes from the extraction
                        attrs = extraction.attributes or {}
                        name = attrs.get('name', extraction.extraction_text)
                        
                        # Parse quantity - can be string or None
                        quantity_str = attrs.get('quantity')
                        quantity = None
                        if quantity_str is not None:
                            try:
                                quantity = float(quantity_str)
                            except (ValueError, TypeError):
                                quantity = None
                        
                        unit = attrs.get('unit')
                        group = attrs.get('group')
                        
                        # Apply ingredient group mapping if available
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
                
                # Create recipe if we have title and ingredients
                if title and ingredients:
                    recipe = Recipe(
                        title=title,
                        ingredients=ingredients
                    )
                    return recipe
                
                return None
            
            return None
            
        except Exception as e:
            return None
