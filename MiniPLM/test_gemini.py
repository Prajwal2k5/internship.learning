
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL")

try:
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=model,
        contents="Explain what a PLM system is in two simple sentences."
    )

    print("Gemini API connection successful!")
    print("\nResponse:")
    print(response.text)

except Exception as e:
    print("Gemini API test failed:")
    print(e)
