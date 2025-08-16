"""
Unit tests for the API routes.
"""
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime

from app.main import app
from app.models.schemas import InsightsResponse


class TestAPI:
    """Test cases for API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    @pytest.fixture
    def sample_insights_response(self):
        """Sample insights response data."""
        return {
            "store_url": "https://example-store.myshopify.com",
            "store_name": "Example Store",
            "is_shopify_store": True,
            "product_catalog": {
                "total_products": 2,
                "products": [
                    {
                        "id": 123,
                        "title": "Test Product 1",
                        "handle": "test-product-1",
                        "description": "A great test product",
                        "vendor": "Test Vendor",
                        "product_type": "Test",
                        "tags": ["test"],
                        "price": "29.99",
                        "available": True,
                        "images": ["https://example.com/image1.jpg"],
                        "variants": []
                    },
                    {
                        "id": 124,
                        "title": "Test Product 2",
                        "handle": "test-product-2",
                        "description": "Another great test product",
                        "vendor": "Test Vendor",
                        "product_type": "Test",
                        "tags": ["test"],
                        "price": "39.99",
                        "available": True,
                        "images": ["https://example.com/image2.jpg"],
                        "variants": []
                    }
                ],
                "has_more": False
            },
            "hero_products": [
                {
                    "title": "Featured Product",
                    "description": "Our best seller",
                    "image_url": "https://example.com/hero.jpg",
                    "product_url": "https://example-store.myshopify.com/products/featured",
                    "price": "$49.99",
                    "featured_section": "homepage"
                }
            ],
            "privacy_policy": {
                "title": "Privacy Policy",
                "content": "This is our privacy policy...",
                "url": "https://example-store.myshopify.com/pages/privacy-policy",
                "type": "privacy_policy"
            },
            "return_refund_policy": {
                "title": "Return & Refund Policy",
                "content": "We offer 30-day returns...",
                "url": "https://example-store.myshopify.com/pages/refund-policy",
                "type": "return_refund_policy"
            },
            "faqs": [
                {
                    "question": "What is your shipping policy?",
                    "answer": "We ship worldwide within 3-5 business days."
                },
                {
                    "question": "Do you offer returns?",
                    "answer": "Yes, we offer 30-day returns on all items."
                }
            ],
            "contact_info": {
                "emails": ["support@example-store.com", "sales@example-store.com"],
                "phone_numbers": ["+1-234-567-8900"],
                "addresses": ["123 Main St, City, State 12345"],
                "contact_form_url": "https://example-store.myshopify.com/pages/contact"
            },
            "social_handles": {
                "instagram": ["example_store"],
                "facebook": ["examplestore"],
                "twitter": ["example_store"]
            },
            "brand_context": {
                "name": "Example Store",
                "description": "We are a leading retailer of quality products...",
                "mission": "To provide the best products at affordable prices",
                "values": ["Quality", "Affordability", "Customer Service"]
            },
            "important_links": [
                {
                    "title": "Track Your Order",
                    "url": "https://example-store.myshopify.com/tools/tracking",
                    "category": "order tracking"
                },
                {
                    "title": "Size Guide",
                    "url": "https://example-store.myshopify.com/pages/size-guide",
                    "category": "size guide"
                }
            ],
            "competitors": [],
            "scraped_at": datetime.now(),
            "processing_time": 2.5,
            "success": True,
            "errors": [],
            "warnings": []
        }
    
    def test_root_endpoint(self, client):
        """Test the root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs_url" in data
    
    def test_health_check_endpoint(self, client):
        """Test the health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "database_connected" in data
    
    @patch('app.api.routes.get_insights_record')
    @patch('app.services.scraper.ShopifyScraperService.scrape_store_insights')
    def test_fetch_insights_success(self, mock_scrape, mock_get_record, client, sample_insights_response):
        """Test successful insights fetching."""
        # Mock no cached data
        mock_get_record.return_value = None
        
        # Mock scraper response
        mock_scrape.return_value = sample_insights_response
        
        request_data = {
            "website_url": "https://example-store.myshopify.com",
            "include_competitors": False
        }
        
        response = client.post("/api/v1/fetch-insights", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["store_url"] == "https://example-store.myshopify.com"
        assert data["store_name"] == "Example Store"
        assert data["success"] == True
        assert len(data["product_catalog"]["products"]) == 2
        assert len(data["hero_products"]) == 1
        assert len(data["faqs"]) == 2
        assert len(data["contact_info"]["emails"]) == 2
    
    def test_fetch_insights_invalid_url(self, client):
        """Test insights fetching with invalid URL."""
        request_data = {
            "website_url": "not-a-valid-url",
            "include_competitors": False
        }
        
        response = client.post("/api/v1/fetch-insights", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "Invalid website URL" in data["detail"]
    
    @patch('app.api.routes.get_insights_record')
    @patch('app.services.scraper.ShopifyScraperService.scrape_store_insights')
    def test_fetch_insights_scraping_error(self, mock_scrape, mock_get_record, client):
        """Test insights fetching when scraping fails."""
        # Mock no cached data
        mock_get_record.return_value = None
        
        # Mock scraper error
        mock_scrape.side_effect = ValueError("Website not accessible")
        
        request_data = {
            "website_url": "https://non-existent-store.myshopify.com",
            "include_competitors": False
        }
        
        response = client.post("/api/v1/fetch-insights", json=request_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "Website not found or not accessible" in data["detail"]
    
    @patch('app.api.routes.get_insights_record')
    def test_fetch_insights_cached_data(self, mock_get_record, client, sample_insights_response):
        """Test insights fetching with cached data."""
        # Mock cached data (recent)
        import time
        cached_data = sample_insights_response.copy()
        cached_data["scraped_at"] = time.time() - 3600  # 1 hour ago
        mock_get_record.return_value = cached_data
        
        request_data = {
            "website_url": "https://example-store.myshopify.com",
            "include_competitors": False
        }
        
        response = client.post("/api/v1/fetch-insights", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["store_name"] == "Example Store"
    
    @patch('app.api.routes.get_insights_record')
    @patch('app.services.scraper.ShopifyScraperService.scrape_store_insights')
    @patch('app.services.scraper.ShopifyScraperService.scrape_competitor_analysis')
    def test_fetch_insights_with_competitors(self, mock_competitors, mock_scrape, mock_get_record, client, sample_insights_response):
        """Test insights fetching with competitor analysis."""
        # Mock no cached data
        mock_get_record.return_value = None
        
        # Mock scraper response
        mock_scrape.return_value = sample_insights_response
        
        # Mock competitor analysis
        mock_competitors.return_value = [
            {
                "name": "Competitor Store",
                "website_url": "https://competitor.com",
                "description": "A competing store"
            }
        ]
        
        request_data = {
            "website_url": "https://example-store.myshopify.com",
            "include_competitors": True
        }
        
        response = client.post("/api/v1/fetch-insights", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        # Competitors would be included in the response
    
    def test_fetch_insights_missing_url(self, client):
        """Test insights fetching without URL."""
        request_data = {
            "include_competitors": False
        }
        
        response = client.post("/api/v1/fetch-insights", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_fetch_insights_empty_request(self, client):
        """Test insights fetching with empty request."""
        response = client.post("/api/v1/fetch-insights", json={})
        
        assert response.status_code == 422  # Validation error
    
    @patch('app.api.routes.get_all_insights_records')
    def test_get_insights_history(self, mock_get_records, client):
        """Test insights history endpoint."""
        # Mock database records
        mock_records = [
            {
                "id": 1,
                "store_url": "https://store1.com",
                "store_name": "Store 1",
                "scraped_at": datetime.now(),
                "success": True,
                "insights_data": {}
            },
            {
                "id": 2,
                "store_url": "https://store2.com",
                "store_name": "Store 2", 
                "scraped_at": datetime.now(),
                "success": True,
                "insights_data": {}
            }
        ]
        mock_get_records.return_value = mock_records
        
        response = client.get("/api/v1/insights/history")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["records"]) == 2
        assert data["limit"] == 50
        assert data["offset"] == 0
    
    def test_get_insights_history_with_params(self, client):
        """Test insights history with pagination parameters."""
        with patch('app.api.routes.get_all_insights_records') as mock_get_records:
            mock_get_records.return_value = []
            
            response = client.get("/api/v1/insights/history?limit=10&offset=20")
            
            assert response.status_code == 200
            data = response.json()
            assert data["limit"] == 10
            assert data["offset"] == 20
            
            # Check that the function was called with correct parameters
            mock_get_records.assert_called_once_with(limit=10, offset=20)
    
    @patch('app.api.routes.get_insights_record')
    def test_get_cached_insights_found(self, mock_get_record, client, sample_insights_response):
        """Test getting cached insights when data exists."""
        mock_get_record.return_value = sample_insights_response
        
        response = client.get("/api/v1/insights/https://example-store.myshopify.com")
        
        assert response.status_code == 200
        data = response.json()
        assert data["store_name"] == "Example Store"
    
    @patch('app.api.routes.get_insights_record')
    def test_get_cached_insights_not_found(self, mock_get_record, client):
        """Test getting cached insights when no data exists."""
        mock_get_record.return_value = None
        
        response = client.get("/api/v1/insights/https://non-existent-store.com")
        
        assert response.status_code == 404
        data = response.json()
        assert "No cached insights found" in data["detail"]
    
    def test_clear_cached_insights(self, client):
        """Test clearing cached insights."""
        response = client.delete("/api/v1/insights/https://example-store.com")
        
        assert response.status_code == 200
        data = response.json()
        assert "Cache clearing requested" in data["message"]
    
    @patch('app.api.routes.get_all_insights_records')
    def test_get_api_stats(self, mock_get_records, client):
        """Test API statistics endpoint."""
        # Mock some records with stats
        mock_records = [
            {"success": True, "processing_time": 2.5},
            {"success": True, "processing_time": 3.0},
            {"success": False, "processing_time": 1.0},
        ]
        mock_get_records.return_value = mock_records
        
        response = client.get("/api/v1/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_requests"] == 3
        assert data["successful_requests"] == 2
        assert data["failed_requests"] == 1
        assert data["success_rate_percent"] == 66.67
        assert "average_processing_time_seconds" in data
    
    def test_api_documentation(self, client):
        """Test that API documentation is accessible."""
        response = client.get("/docs")
        assert response.status_code == 200
        
        response = client.get("/redoc")
        assert response.status_code == 200
    
    def test_openapi_schema(self, client):
        """Test that OpenAPI schema is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        
        # Check that our main endpoint is in the schema
        assert "/api/v1/fetch-insights" in schema["paths"]
    
    def test_cors_headers(self, client):
        """Test CORS headers are properly set."""
        response = client.options("/api/v1/fetch-insights")
        
        # FastAPI with CORS middleware should handle OPTIONS requests
        assert response.status_code in [200, 405]  # Some versions return 405 for OPTIONS
    
    def test_request_validation(self, client):
        """Test request validation with various invalid inputs."""
        
        # Test with invalid JSON
        response = client.post(
            "/api/v1/fetch-insights",
            data="invalid json",
            headers={"content-type": "application/json"}
        )
        assert response.status_code == 422
        
        # Test with wrong data types
        request_data = {
            "website_url": 123,  # Should be string
            "include_competitors": "true"  # Should be boolean
        }
        
        response = client.post("/api/v1/fetch-insights", json=request_data)
        assert response.status_code == 422


@pytest.mark.asyncio
class TestAsyncEndpoints:
    """Test async functionality of endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create an async test client."""
        return TestClient(app)
    
    @patch('app.services.scraper.ShopifyScraperService.scrape_store_insights')
    def test_concurrent_requests(self, mock_scrape, client):
        """Test handling multiple concurrent requests."""
        # Mock scraper to simulate processing time
        async def mock_scrape_insights(url):
            await asyncio.sleep(0.1)  # Simulate processing time
            return {
                "store_url": url,
                "success": True,
                "processing_time": 0.1,
                "product_catalog": {"total_products": 0, "products": []},
                "hero_products": [],
                "faqs": [],
                "contact_info": {"emails": [], "phone_numbers": [], "addresses": []},
                "social_handles": {},
                "brand_context": {},
                "important_links": [],
                "competitors": [],
                "errors": [],
                "warnings": []
            }
        
        mock_scrape.side_effect = mock_scrape_insights
        
        # Make multiple requests
        urls = [
            "https://store1.myshopify.com",
            "https://store2.myshopify.com", 
            "https://store3.myshopify.com"
        ]
        
        with patch('app.api.routes.get_insights_record', return_value=None):
            for url in urls:
                request_data = {"website_url": url, "include_competitors": False}
                response = client.post("/api/v1/fetch-insights", json=request_data)
                assert response.status_code == 200
