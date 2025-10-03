from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import re
import io
import hashlib
from typing import Dict, Any, Optional
import pypdf
import pdfplumber

app = FastAPI(
    title="PDF Data Extractor",
    description="Extract structured data from PDFs using regex patterns",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory template storage
TEMPLATES = {
    "invoice_v1": {
        "name": "invoice_v1",
        "fields": {
            "invoice_number": {
                "pattern": r"(?:Invoice\s*(?:No\.?|#)\s*)\s*(?P<value>[A-Z0-9\-_/]{3,})",
                "postprocess": "strip",
                "required": True
            },
            "invoice_date": {
                "pattern": r"(?:Date)[:\s]*?(?P<value>\d{2}[/-]\d{2}[/-]\d{4}|\d{4}[/-]\d{2}[/-]\d{2})",
                "postprocess": "date",
                "required": True
            },
            "total_amount": {
                "pattern": r"(?:Total)[:\s]*?(?P<value>[\p{Sc}]?\s?\d{1,3}(?:[\s,]\d{3})*(?:\.\d{2})?)",
                "postprocess": "currency",
                "required": True
            },
            "currency": {
                "pattern": r"(?P<value>USD|EUR|GBP|\$|€|£)",
                "postprocess": "strip",
                "required": False
            }
        }
    },
    "receipt_v1": {
        "name": "receipt_v1",
        "fields": {
            "store_name": {
                "pattern": r"(?P<value>[A-Za-z\s&.,]{2,50})",
                "postprocess": "strip",
                "required": True
            },
            "total_amount": {
                "pattern": r"(?:Total|Amount)[:\s]*?(?P<value>[\p{Sc}]?\s?\d{1,3}(?:[\s,]\d{3})*(?:\.\d{2})?)",
                "postprocess": "currency",
                "required": True
            },
            "date": {
                "pattern": r"(?P<value>\d{2}[/-]\d{2}[/-]\d{4}|\d{4}[/-]\d{2}[/-]\d{2})",
                "postprocess": "date",
                "required": True
            }
        }
    }
}

def postprocess_value(value: str, postprocess_type: str) -> str:
    """Apply post-processing to extracted value"""
    if postprocess_type == "strip":
        return value.strip()
    elif postprocess_type == "date":
        # Simple date normalization
        date_match = re.search(r'(\d{2})[/-](\d{2})[/-](\d{4})', value)
        if date_match:
            month, day, year = date_match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        return value
    elif postprocess_type == "currency":
        # Remove currency symbols and normalize
        value = re.sub(r'[\p{Sc}]', '', value)
        value = re.sub(r'[,\s]', '', value)
        return value
    return value

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF using pypdf and pdfplumber as fallback"""
    try:
        # Try pypdf first
        pdf_reader = pypdf.PdfReader(io.BytesIO(file_content))
        text_parts = []
        for page in pdf_reader.pages:
            try:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            except:
                continue
        
        full_text = '\n'.join(text_parts)
        
        # If pypdf didn't extract much, try pdfplumber
        if len(full_text.strip()) < 100:
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                text_parts = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                full_text = '\n'.join(text_parts)
        
        return full_text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not extract text from PDF: {str(e)}")

def extract_fields(text: str, template: Dict[str, Any]) -> Dict[str, Any]:
    """Extract fields from text using template patterns"""
    fields = {}
    confidences = []
    
    for field_name, field_config in template["fields"].items():
        pattern = field_config["pattern"]
        postprocess = field_config.get("postprocess", "strip")
        required = field_config.get("required", True)
        
        try:
            # Compile regex with case-insensitive and multiline flags
            regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            match = regex.search(text)
            
            if match:
                # Extract value from named group or first group
                if 'value' in match.groupdict():
                    value = match.group('value')
                elif match.groups():
                    value = match.group(1)
                else:
                    value = match.group(0)
                
                # Apply post-processing
                processed_value = postprocess_value(value, postprocess)
                
                # Simple confidence calculation
                confidence = 0.8 if len(pattern) > 30 else 0.6
                if re.match(r'^[A-Z0-9\-_/]{3,}$', processed_value):  # Looks like ID
                    confidence += 0.1
                elif re.match(r'^\d{4}-\d{2}-\d{2}$', processed_value):  # Looks like date
                    confidence += 0.1
                elif re.match(r'^\d+(\.\d{2})?$', processed_value):  # Looks like currency
                    confidence += 0.1
                
                fields[field_name] = {
                    "value": processed_value,
                    "confidence": min(1.0, confidence)
                }
                confidences.append(confidence)
            else:
                if required:
                    fields[field_name] = {
                        "value": "",
                        "confidence": 0.0
                    }
                    confidences.append(0.0)
        except Exception:
            if required:
                fields[field_name] = {
                    "value": "",
                    "confidence": 0.0
                }
                confidences.append(0.0)
    
    return fields, sum(confidences) / len(confidences) if confidences else 0.0

@app.get("/")
async def root():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/templates")
async def get_templates():
    """Get list of available templates"""
    return {"templates": list(TEMPLATES.keys())}

@app.post("/extract")
async def extract_data(
    file: UploadFile = File(...),
    template_name: str = Form(...)
):
    """Extract data from PDF using a template"""
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('application/pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Check file size (limit to 10MB)
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB")
    
    # Get template
    if template_name not in TEMPLATES:
        raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")
    
    template = TEMPLATES[template_name]
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Calculate file hash
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # Extract text from PDF
        text = extract_text_from_pdf(file_content)
        
        if len(text.strip()) < 10:
            raise HTTPException(status_code=400, detail="PDF appears to be empty or unreadable")
        
        # Extract fields using template
        fields, confidence_avg = extract_fields(text, template)
        
        return {
            "template_used": template_name,
            "fields": fields,
            "raw_text_chars": len(text),
            "confidence_avg": confidence_avg,
            "file_hash": file_hash
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/extract-custom")
async def extract_custom(
    file: UploadFile = File(...),
    template_json: str = Form(...)
):
    """Extract data from PDF using a custom template"""
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('application/pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Check file size (limit to 10MB)
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB")
    
    try:
        # Parse template JSON
        template = json.loads(template_json)
        
        # Basic template validation
        if "name" not in template or "fields" not in template:
            raise HTTPException(status_code=400, detail="Template must have 'name' and 'fields'")
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in template")
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Calculate file hash
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # Extract text from PDF
        text = extract_text_from_pdf(file_content)
        
        if len(text.strip()) < 10:
            raise HTTPException(status_code=400, detail="PDF appears to be empty or unreadable")
        
        # Extract fields using template
        fields, confidence_avg = extract_fields(text, template)
        
        return {
            "template_used": template["name"],
            "fields": fields,
            "raw_text_chars": len(text),
            "confidence_avg": confidence_avg,
            "file_hash": file_hash
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
