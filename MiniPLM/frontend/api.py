import requests

# FastAPI backend address
BASE_URL = "http://127.0.0.1:8000"


def handle_response(response):
    """Check API response and return JSON data."""
    try:
        response.raise_for_status()
        if response.status_code == 204:
            return None
        return response.json()

    except requests.exceptions.HTTPError:
        try:
            error_detail = response.json().get("detail", response.text)
        except ValueError:
            error_detail = response.text

        raise Exception(f"API Error ({response.status_code}): {error_detail}")


def check_backend():
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    return handle_response(response)


# -------------------------
# PART MANAGEMENT
# -------------------------

def get_parts():
    response = requests.get(f"{BASE_URL}/parts/", timeout=10)
    return handle_response(response)


def search_parts(query):
    response = requests.get(
        f"{BASE_URL}/parts/search",
        params={"q": query},
        timeout=10
    )
    return handle_response(response)


def create_part(part_data):
    response = requests.post(
        f"{BASE_URL}/parts/",
        json=part_data,
        timeout=10
    )
    return handle_response(response)


def update_part(part_id, part_data):
    response = requests.put(
        f"{BASE_URL}/parts/{part_id}",
        json=part_data,
        timeout=10
    )
    return handle_response(response)


def delete_part(part_id):
    response = requests.delete(
        f"{BASE_URL}/parts/{part_id}",
        timeout=10
    )
    return handle_response(response)


# -------------------------
# DOCUMENT MANAGEMENT
# -------------------------

def get_documents():
    response = requests.get(f"{BASE_URL}/documents/", timeout=10)
    return handle_response(response)


def get_part_documents(part_id):
    response = requests.get(
        f"{BASE_URL}/documents/part/{part_id}",
        timeout=10
    )
    return handle_response(response)


def upload_document(part_id, uploaded_file):
    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            "application/pdf"
        )
    }

    response = requests.post(
        f"{BASE_URL}/documents/upload/{part_id}",
        files=files,
        timeout=60
    )
    return handle_response(response)


def summarize_document(document_id):
    response = requests.post(
        f"{BASE_URL}/documents/{document_id}/summarize",
        timeout=120
    )
    return handle_response(response)


def extract_document_info(document_id):
    response = requests.post(
        f"{BASE_URL}/documents/{document_id}/extract-info",
        timeout=120
    )
    return handle_response(response)


def index_document(document_id):
    response = requests.post(
        f"{BASE_URL}/documents/{document_id}/index",
        timeout=180
    )
    return handle_response(response)


def ask_document(document_id, question):
    response = requests.post(
        f"{BASE_URL}/documents/{document_id}/ask",
        json={"question": question},
        timeout=120
    )
    return handle_response(response)


def delete_document(document_id):
    response = requests.delete(
        f"{BASE_URL}/documents/{document_id}",
        timeout=15
    )
    return handle_response(response)
def generate_part_ai_description(part_id):
    response = requests.post(
        f"{BASE_URL}/parts/{part_id}/generate-description",
        timeout=120
    )
    return handle_response(response)

def get_document_download_url(document_id):
    return f"{BASE_URL}/documents/{document_id}/download"