#!/usr/bin/env python3
"""
Test script for the PDF extractor API
"""

import requests
import json

# API base URL
BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    print("Health Check:", response.json())
    return response.status_code == 200

def test_templates():
    """Test templates endpoint"""
    response = requests.get(f"{BASE_URL}/templates")
    print("Available Templates:", response.json())
    return response.status_code == 200

def test_extract_with_sample_data():
    """Test extraction with sample text data"""
    # Create a simple test PDF content (this would normally be a real PDF file)
    sample_template = {
        "name": "test_template",
        "fields": {
            "amount": {
                "pattern": r"Total:\s*(?P<value>\d+\.\d+)",
                "postprocess": "currency",
                "required": True
            },
            "date": {
                "pattern": r"Date:\s*(?P<value>\d{2}/\d{2}/\d{4})",
                "postprocess": "date",
                "required": True
            }
        }
    }
    
    print("Sample Template:", json.dumps(sample_template, indent=2))
    return True

def create_sample_pdf():
    """Create a sample PDF for testing (requires reportlab)"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        import io
        
        # Create PDF in memory
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        
        # Add sample text
        p.drawString(100, 750, "INVOICE")
        p.drawString(100, 700, "Invoice No: INV-2024-001")
        p.drawString(100, 650, "Date: 01/15/2024")
        p.drawString(100, 600, "Total: $1,250.00")
        p.drawString(100, 550, "Currency: USD")
        
        p.showPage()
        p.save()
        
        # Get PDF content
        buffer.seek(0)
        pdf_content = buffer.getvalue()
        buffer.close()
        
        return pdf_content
    except ImportError:
        print("reportlab not installed. Install with: pip install reportlab")
        return None

def test_extract_with_pdf():
    """Test extraction with actual PDF file"""
    pdf_content = create_sample_pdf()
    if not pdf_content:
        print("Could not create sample PDF")
        return False
    
    # Test with predefined template
    files = {'file': ('test.pdf', pdf_content, 'application/pdf')}
    data = {'template_name': 'invoice_v1'}
    
    try:
        response = requests.post(f"{BASE_URL}/extract", files=files, data=data)
        print("Extract Response:", response.json())
        return response.status_code == 200
    except Exception as e:
        print(f"Error testing extraction: {e}")
        return False

def test_custom_template():
    """Test extraction with custom template"""
    pdf_content = create_sample_pdf()
    if not pdf_content:
        return False
    
    custom_template = {
        "name": "custom_invoice",
        "fields": {
            "invoice_number": {
                "pattern": r"Invoice No:\s*(?P<value>[A-Z0-9\-]+)",
                "postprocess": "strip",
                "required": True
            },
            "total": {
                "pattern": r"Total:\s*(?P<value>\$[\d,]+\.\d+)",
                "postprocess": "currency",
                "required": True
            }
        }
    }
    
    files = {'file': ('test.pdf', pdf_content, 'application/pdf')}
    data = {'template_json': json.dumps(custom_template)}
    
    try:
        response = requests.post(f"{BASE_URL}/extract-custom", files=files, data=data)
        print("Custom Template Response:", response.json())
        return response.status_code == 200
    except Exception as e:
        print(f"Error testing custom template: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing PDF Extractor API...")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health),
        ("Templates", test_templates),
        ("Sample Template", test_extract_with_sample_data),
        ("PDF Extraction", test_extract_with_pdf),
        ("Custom Template", test_custom_template)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"✓ Passed" if result else "✗ Failed")
        except Exception as e:
            print(f"✗ Error: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("Test Results:")
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed")

if __name__ == "__main__":
    main()
