# PDF Data Extractor - Minimal Version

A simple FastAPI application for extracting structured data from PDFs using regex patterns.

## Features

- Extract data from PDFs using predefined or custom templates
- Built-in templates for invoices and receipts
- Confidence scoring for extracted fields
- File validation and error handling
- Ready for deployment to RapidAPI

## API Endpoints

### GET /
Returns basic API information

### GET /health
Health check endpoint

### GET /templates
Returns list of available templates

### POST /extract
Extract data using a predefined template

**Parameters:**
- `file`: PDF file (multipart/form-data)
- `template_name`: Name of the template to use (form data)

**Available templates:**
- `invoice_v1`: Extracts invoice number, date, total amount, currency
- `receipt_v1`: Extracts store name, total amount, date

### POST /extract-custom
Extract data using a custom template

**Parameters:**
- `file`: PDF file (multipart/form-data)
- `template_json`: Custom template JSON (form data)

## Template Format

```json
{
  "name": "template_name",
  "fields": {
    "field_name": {
      "pattern": "regex_pattern",
      "postprocess": "strip|date|currency",
      "required": true
    }
  }
}
```

## Example Usage

### Using predefined template:
```bash
curl -X POST "http://localhost:8000/extract" \
  -F "file=@invoice.pdf" \
  -F "template_name=invoice_v1"
```

### Using custom template:
```bash
curl -X POST "http://localhost:8000/extract-custom" \
  -F "file=@document.pdf" \
  -F "template_json={\"name\":\"custom\",\"fields\":{\"amount\":{\"pattern\":\"Total: (?P<value>\\d+\\.\\d+)\",\"postprocess\":\"currency\",\"required\":true}}}"
```

## Response Format

```json
{
  "template_used": "invoice_v1",
  "fields": {
    "invoice_number": {
      "value": "INV-2024-001",
      "confidence": 0.9
    },
    "total_amount": {
      "value": "1250.00",
      "confidence": 0.85
    }
  },
  "raw_text_chars": 1234,
  "confidence_avg": 0.875,
  "file_hash": "sha256_hash"
}
```

## Deployment

### Local Development
```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

### Docker
```bash
docker build -t pdf-extractor .
docker run -p 8000:8000 pdf-extractor
```

### RapidAPI Deployment
1. Push code to GitHub repository
2. Connect repository to RapidAPI
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
5. Deploy!

## Limitations

- Maximum file size: 10MB
- No OCR support (text-based PDFs only)
- No authentication (add API key validation if needed)
- No rate limiting (add if needed for production)
- No database persistence (results not stored)

## Post-processing Types

- `strip`: Remove whitespace and control characters
- `date`: Normalize to YYYY-MM-DD format
- `currency`: Remove currency symbols and separators
