# Patent Document Analyse Service

REST API service for extracting text from patent documents using MinerU OCR.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the API Server

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

### 3. Start the Streamlit Frontend (optional)

```bash
streamlit run app/streamlit_app.py
```

The Streamlit UI will open at `http://localhost:8501`

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info |
| `/health` | GET | Health check |
| `/extract` | POST | Extract from single file |
| `/extract/all` | POST | Extract from all document types |

## Usage Examples

### Using curl

```bash
# Extract from description only
curl -X POST -F "description_file=@patent.pdf" http://localhost:8000/extract

# Extract from all documents
curl -X POST \
  -F "description_file=@description.pdf" \
  -F "claims_file=@claims.pdf" \
  -F "drawings_file=@drawings.pdf" \
  http://localhost:8000/extract/all
```

### Using Python

```python
import requests

files = {
    "description_file": open("patent.pdf", "rb")
}

response = requests.post("http://localhost:8000/extract", files=files)
result = response.json()
print(result["description_text"])
```

## Project Structure

```
patent_document_text_extract_service/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── mineru_wrapper.py    # MinerU wrapper
│   ├── pdf_extractor.py    # PDF handling
│   ├── docx_extractor.py   # DOCX handling
│   ├── docx_image_ocr.py   # DOCX image OCR
│   ├── image_ocr.py        # Image OCR
│   └── streamlit_app.py    # Streamlit frontend
│
├── storage/
│   ├── input_docs/
│   └── extracted_output/
│
├── config/
│   └── settings.py
│
├── logs/
├── requirements.txt
└── README.md
```
