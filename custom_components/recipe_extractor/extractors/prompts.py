"""
Prompts and examples for recipe extraction using LangExtract.
"""

EXTRACTION_PROMPT = """
Extract recipe information from the provided text in any language (English, German, Danish, etc.). 

Identify and extract:
1. The recipe title
2. The number of servings/portions (if specified) - IMPORTANT: Look for patterns like:
   - "Servings: 4", "Serves: 4", "Yield: 4"
   - "Portionen: 4", "Für 4 Portionen", "4 Portionen"
   - "4 persons", "For 4 people"
   - "Makes 12 cookies", "Ergibt 8 Stücke"
   - Extract ONLY the number (e.g., extract "4" from "Für 4 Portionen")
3. ALL ingredients with their quantities and units

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
        \\"servings\\": 4,
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

Note: The servings field should be an integer representing the number of portions/servings the recipe yields. If not specified in the recipe, set it to null.
"""
