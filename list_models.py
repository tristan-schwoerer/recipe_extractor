#!/usr/bin/env python3
"""List available Gemini models."""
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("LANGEXTRACT_API_KEY")
if not api_key:
    print("Error: LANGEXTRACT_API_KEY not found in environment")
    exit(1)

genai.configure(api_key=api_key)

print("Available Gemini models:")
print("-" * 60)
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"Model: {model.name}")
        print(f"  Display Name: {model.display_name}")
        print(f"  Description: {model.description}")
        print(f"  Supported methods: {model.supported_generation_methods}")
        print("-" * 60)
