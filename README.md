# Shopify Insights Fetcher

A comprehensive **FastAPI-based application** for extracting insights from Shopify stores. This tool provides detailed analysis including product catalogs, policies, FAQs, contact information, social media handles, and more.

## 🚀 Features

### Core Functionality
- **Product Catalog Extraction**: Complete product listings from `/products.json`
- **Hero Products**: Featured products from store homepage
- **Store Policies**: Privacy, return/refund, terms of service, shipping policies
- **FAQ Extraction**: Comprehensive FAQ collection from various page formats
- **Contact Information**: Emails, phone numbers, physical addresses
- **Social Media Handles**: Instagram, Facebook, Twitter, TikTok, YouTube, LinkedIn, Pinterest
- **Brand Context**: About information, mission, values, brand story
- **Important Links**: Order tracking, contact pages, blogs, support links

### Bonus Features
- **MySQL Persistence**: SQLAlchemy ORM with MySQL for data storage
- **Competitor Analysis**: Basic competitor discovery and analysis
- **Caching System**: Intelligent caching to avoid redundant scraping
- **RESTful API**: Clean, well-documented API with OpenAPI/Swagger documentation
- **Error Handling**: Comprehensive error handling with appropriate HTTP status codes

## 📋 Requirements

- Python 3.8+
- MySQL 5.7+ (optional, for persistence)
- OpenAI API key (optional, for advanced text processing)

## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd shopify-extractor
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

5. **Set up MySQL database (optional):**
   ```sql
   CREATE DATABASE shopify_insights;
   CREATE USER 'shopify_user'@'localhost' IDENTIFIED BY 'your_password';
   GRANT ALL PRIVILEGES ON shopify_insights.* TO 'shopify_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

## 🏃‍♂️ Running the Application

### Development Mode
```bash
python -m app.main
```

### Production Mode
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Using Docker (optional)
```bash
# Build the image
docker build -t shopify-insights-fetcher .

# Run the container
docker run -p 8000:8000 shopify-insights-fetcher
```

## 📖 API Documentation

Once the application is running, you can access:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

### Main Endpoints

#### POST `/api/v1/fetch-insights`
Extract comprehensive insights from a Shopify store.

**Request:**
```json
{
  "website_url": "https://example-store.myshopify.com",
  "include_competitors": false
}
```

**Response:**
```json
{
  "store_url": "https://example-store.myshopify.com",
  "store_name": "Example Store",
  "is_shopify_store": true,
  "product_catalog": {
    "total_products": 150,
    "products": [...],
    "has_more": false
  },
  "hero_products": [...],
  "privacy_policy": {...},
  "return_refund_policy": {...},
  "faqs": [...],
  "contact_info": {...},
  "social_handles": {...},
  "brand_context": {...},
  "important_links": [...],
  "competitors": [...],
  "processing_time": 3.45,
  "success": true
}
```

#### GET `/health`
Health check endpoint for monitoring.

#### GET `/api/v1/insights/history`
Retrieve historical insights with pagination.

#### GET `/api/v1/stats`
Get API usage statistics.

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_api.py

# Run with verbose output
pytest -v
```

## 📁 Project Structure

```
shopify-extractor/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py           # API route definitions
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Configuration settings
│   │   └── utils.py            # Utility functions
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic models
│   ├── services/
│   │   ├── __init__.py
│   │   └── scraper.py          # Web scraping service
│   └── db/
│       ├── __init__.py
│       └── database.py         # Database models and operations
├── tests/
│   ├── __init__.py
│   ├── test_api.py             # API endpoint tests
│   └── test_scraper.py         # Scraper service tests
├── requirements.txt            # Python dependencies
├── pytest.ini                 # Test configuration
├── env.example                 # Environment variables template
└── README.md                   # This file
```

## ⚙️ Configuration

The application uses environment variables for configuration. Key settings:

- `DEBUG`: Enable debug mode
- `DATABASE_URL`: Complete database URL
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`: Individual database settings
- `OPENAI_API_KEY`: For advanced text processing
- `REQUEST_TIMEOUT`: HTTP request timeout in seconds
- `MAX_RETRIES`: Maximum retry attempts for failed requests

## 🔍 Scraping Strategy

The application uses a multi-layered scraping approach:

1. **JSON API First**: Attempts to use Shopify's JSON endpoints when available
2. **HTML Parsing**: Falls back to HTML parsing using BeautifulSoup
3. **Pattern Matching**: Uses regex patterns for extracting structured data
4. **Intelligent Selectors**: Multiple CSS selectors for different store themes
5. **Error Recovery**: Graceful handling of missing or inaccessible content

## 🚨 Error Handling

The API provides clear error responses:

- **401**: Website not found or not accessible
- **422**: Invalid request parameters
- **500**: Internal server error
- **503**: Service temporarily unavailable

## 🔒 Security Considerations

- Rate limiting recommended for production use
- Input validation and sanitization
- SQL injection protection through SQLAlchemy ORM
- XSS protection in data processing
- CORS configuration for production environments

## 📈 Performance

- Asynchronous processing for I/O operations
- Intelligent caching to reduce redundant requests
- Database connection pooling
- Request timeouts and retry mechanisms
- Background task processing for non-critical operations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **FastAPI** for the excellent web framework
- **BeautifulSoup** for HTML parsing capabilities
- **SQLAlchemy** for database ORM
- **Pydantic** for data validation
- **pytest** for testing framework

## 📞 Support

For support, email support@yourcompany.com or create an issue in the repository.

---

Built with ❤️ for comprehensive Shopify store analysis.
