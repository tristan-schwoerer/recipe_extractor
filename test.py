import os
from dotenv import load_dotenv
from custom_components.recipe_extractor.extractors import RecipeExtractor, fetch_recipe_text

# Load environment variables from .env file
load_dotenv()

# Fetch and extract a random recipe
text, is_jsonld = fetch_recipe_text(
    "https://www.chefkoch.de/rezepte/1521751257407008/Afrikanische-Haehnchenkeulen.html")
print(f"JSON-LD detected: {is_jsonld}")

if is_jsonld:
    # Import the direct parser
    from custom_components.recipe_extractor import _parse_jsonld_recipe
    print("Using direct JSON-LD parsing (no AI)")
    recipe = _parse_jsonld_recipe(text)
else:
    print("Using AI extraction")
    extractor = RecipeExtractor(api_key=os.getenv("LANGEXTRACT_API_KEY"))
    recipe = extractor.extract_recipe(text)

print(f"Title: {recipe.title}")
for ing in recipe.ingredients:
    print(f"  {ing.quantity} {ing.unit} {ing.name}")
