"""
Test script to list available models in google-generativeai SDK
Run this to see which models support generateContent
"""
import google.generativeai as genai
import os

# Configure with API key
api_key = os.getenv('GEMINI_API_KEY') or input('Enter your Gemini API key: ')
genai.configure(api_key=api_key)

print("=" * 80)
print("MODELS THAT SUPPORT generateContent:")
print("=" * 80)

for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"\n✅ {model.name}")
        print(f"   Display Name: {model.display_name}")
        print(f"   Description: {model.description[:100]}...")
        print(f"   Supported methods: {model.supported_generation_methods}")

print("\n" + "=" * 80)
