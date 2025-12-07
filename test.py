from recipe_extractor.scrapers.web_scraper import fetch_recipe_text
from recipe_extractor.parsers.ai_parser import AIRecipeParser
from recipe_extractor.parsers.jsonld_parser import JSONLDRecipeParser
from dotenv import load_dotenv
import os
import sys
sys.path.insert(0, r'c:\Users\trist\repos\recipe_extractor\custom_components')


# Load environment variables from .env file
load_dotenv()

# Fetch and extract a random recipe
text, is_jsonld = fetch_recipe_text(
    "https://www.chefkoch.de/rezepte/1521751257407008/Afrikanische-Haehnchenkeulen.html")
print(f"JSON-LD detected: {is_jsonld}")

if is_jsonld:
    print("Using direct JSON-LD parsing (no AI)")
    jsonld_parser = JSONLDRecipeParser()
    recipe = jsonld_parser.parse_recipe(text)
else:
    print("Using AI extraction")
    ai_parser = AIRecipeParser(api_key=os.getenv("LANGEXTRACT_API_KEY"))
    recipe = ai_parser.parse_recipe(text)

print(f"Title: {recipe.title}")
for ing in recipe.ingredients:
    print(f"  {ing.quantity} {ing.unit} {ing.name}")
