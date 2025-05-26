import os

import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_gemini():
    """Test Gemini API connection"""
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key or api_key == "your-google-api-key-here":
        print("❌ No Gemini API key configured")
        return False

    try:
        # Configure Gemini
        genai.configure(api_key=api_key)

        # Initialize model
        model = genai.GenerativeModel('gemini-2.0-flash')

        # Test with a simple prompt
        response = model.generate_content("Hello! Please respond with just 'Hello from Gemini!'")

        print(f"✅ Gemini API working!")
        print(f"Response: {response.text}")
        return True

    except Exception as e:
        print(f"❌ Gemini API error: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing Gemini API connection...")
    test_gemini()
