
import os
import time

from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing. Check your .env file.")

client = genai.Client(api_key=GEMINI_API_KEY)


def _generate_ai_response(prompt: str) -> str:
    """Generate text using Gemini with retry handling."""

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )

            if not response.text:
                raise ValueError("Gemini returned an empty response.")

            return response.text.strip()

        except Exception:
            if attempt == 2:
                raise

            time.sleep(2 ** attempt)


def generate_part_description(
    part_name: str,
    category: str,
    manufacturer: str
) -> str:
    """Generate a professional technical description for a part."""

    prompt = f"""
You are a Product Lifecycle Management (PLM) technical assistant.

Generate a professional and concise technical description
for the following product part.

Part Name: {part_name}
Category: {category}
Manufacturer: {manufacturer}

Requirements:
- Write 3 to 5 sentences.
- Explain the likely purpose and application.
- Use professional technical language.
- Do not invent exact specifications or certifications.
- Return only the description.
"""

    return _generate_ai_response(prompt)


def summarize_document(document_text: str) -> str:
    """Generate a concise summary of an extracted PDF document."""

    prompt = f"""
You are an AI document analysis assistant for a Product Lifecycle
Management (PLM) system.

Analyze the document text below and create a clear summary.

Requirements:
- Identify the document's main purpose.
- Summarize the most important topics.
- Highlight important instructions, requirements, or findings.
- Use clear headings and bullet points.
- Do not invent information that is not in the document.
- Keep the summary concise and easy to understand.

DOCUMENT TEXT:
{document_text}

Return only the summary.
"""

    return _generate_ai_response(prompt)


def extract_technical_information(document_text: str) -> str:
    """Extract important technical information from a PDF document."""

    prompt = f"""
You are a technical document analysis assistant in a PLM system.

Analyze the following document and extract relevant information.

Organize your response under these headings where applicable:

1. Document Purpose
2. Key Topics
3. Technical Requirements
4. Specifications and Measurements
5. Tools, Software, or Components Mentioned
6. Important Instructions
7. Risks, Warnings, or Limitations
8. Key Takeaways

Instructions:
- Extract only information actually present in the document.
- Do not invent specifications, values, or requirements.
- If a section has no relevant information, write "Not specified".
- Use clear and concise bullet points.

DOCUMENT TEXT:
{document_text}

Return the extracted information in a structured, readable format.
"""

    return _generate_ai_response(prompt)
