# RapidAPI Deployment Guide

## Quick Deployment Steps

### 1. Prepare Your Repository
1. Create a new GitHub repository
2. Upload all files from `pdf-extractor-minimal/` to the repository
3. Make sure the repository is public or you have access to connect it to RapidAPI

### 2. Deploy to RapidAPI
1. Go to [RapidAPI Hub](https://rapidapi.com/hub)
2. Click "Add New API" → "Deploy from GitHub"
3. Connect your GitHub repository
4. Configure the deployment:

**Build Settings:**
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Python Version: 3.11

**Environment Variables:**
- No additional environment variables needed for basic deployment

### 3. Test Your Deployment
Once deployed, test your API:

```bash
# Health check
curl https://your-api-url.rapidapi.com/health

# Get templates
curl https://your-api-url.rapidapi.com/templates

# Test extraction (replace with your actual PDF file)
curl -X POST "https://your-api-url.rapidapi.com/extract" \
  -F "file=@your-invoice.pdf" \
  -F "template_name=invoice_v1"
```

## API Documentation

Your API will automatically generate OpenAPI documentation at:
`https://your-api-url.rapidapi.com/docs`

## Pricing and Limits

For RapidAPI deployment, consider:
- File size limits (currently set to 10MB)
- Request rate limits
- Memory usage limits

## Monitoring

Monitor your API through:
- RapidAPI dashboard
- Application logs
- Health check endpoint

## Scaling Considerations

If you need to scale:
1. Add rate limiting
2. Implement caching
3. Add database for result storage
4. Consider async processing for large files

## Security

For production use, consider adding:
- API key authentication
- Request validation
- File type restrictions
- Rate limiting
