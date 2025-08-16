"""
Unit tests for the scraper service.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup
import requests

from app.services.scraper import ShopifyScraperService
from app.models.schemas import Product, HeroProduct, FAQ, Policy
from app.core.utils import extract_emails, extract_phone_numbers, extract_social_handles


class TestShopifyScraperService:
    """Test cases for ShopifyScraperService."""
    
    @pytest.fixture
    def scraper(self):
        """Create a scraper instance for testing."""
        return ShopifyScraperService()
    
    @pytest.fixture
    def mock_response(self):
        """Create a mock HTTP response."""
        response = Mock()
        response.status_code = 200
        response.content = b"""
        <html>
            <head><title>Test Store</title></head>
            <body>
                <h1>Welcome to Test Store</h1>
                <div class="hero-product">
                    <h3>Featured Product</h3>
                    <img src="/image.jpg" alt="Product Image">
                    <span class="price">$29.99</span>
                </div>
                <footer>
                    <a href="mailto:contact@teststore.com">Email Us</a>
                    <a href="tel:+1234567890">Call Us</a>
                    <a href="https://instagram.com/teststore">Instagram</a>
                </footer>
            </body>
        </html>
        """
        return response
    
    @pytest.fixture
    def sample_product_json(self):
        """Sample product JSON data."""
        return {
            "products": [
                {
                    "id": 123456,
                    "title": "Test Product",
                    "handle": "test-product",
                    "body_html": "<p>Test product description</p>",
                    "vendor": "Test Vendor",
                    "product_type": "Test Type",
                    "tags": ["test", "product"],
                    "variants": [
                        {
                            "id": 789,
                            "price": "29.99",
                            "compare_at_price": "39.99",
                            "available": True
                        }
                    ],
                    "images": [
                        {"src": "https://example.com/image.jpg"}
                    ],
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z"
                }
            ]
        }
    
    def test_create_session(self, scraper):
        """Test session creation with proper configuration."""
        session = scraper._create_session()
        
        assert isinstance(session, requests.Session)
        assert 'User-Agent' in session.headers
        assert session.headers['User-Agent'] == scraper.session.headers['User-Agent']
    
    @patch('app.services.scraper.requests.Session.get')
    def test_make_request_success(self, mock_get, scraper):
        """Test successful HTTP request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = scraper._make_request("https://example.com")
        
        assert result == mock_response
        mock_get.assert_called_once()
    
    @patch('app.services.scraper.requests.Session.get')
    def test_make_request_failure(self, mock_get, scraper):
        """Test failed HTTP request."""
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")
        
        result = scraper._make_request("https://example.com")
        
        assert result is None
    
    def test_get_soup_success(self, scraper, mock_response):
        """Test successful HTML parsing."""
        with patch.object(scraper, '_make_request', return_value=mock_response):
            soup = scraper._get_soup("https://example.com")
            
            assert isinstance(soup, BeautifulSoup)
            assert soup.find('title').get_text() == "Test Store"
    
    def test_get_soup_failure(self, scraper):
        """Test failed HTML parsing."""
        with patch.object(scraper, '_make_request', return_value=None):
            soup = scraper._get_soup("https://example.com")
            
            assert soup is None
    
    def test_extract_store_name(self, scraper, mock_response):
        """Test store name extraction."""
        soup = BeautifulSoup(mock_response.content, 'html.parser')
        store_name = scraper._extract_store_name(soup)
        
        assert store_name == "Test Store"
    
    def test_parse_product_json(self, scraper, sample_product_json):
        """Test product JSON parsing."""
        product_data = sample_product_json["products"][0]
        product = scraper._parse_product_json(product_data)
        
        assert isinstance(product, Product)
        assert product.id == 123456
        assert product.title == "Test Product"
        assert product.handle == "test-product"
        assert product.vendor == "Test Vendor"
        assert product.price == "29.99"
        assert product.compare_at_price == "39.99"
        assert product.available == True
        assert len(product.images) == 1
        assert len(product.variants) == 1
    
    def test_parse_hero_product(self, scraper, mock_response):
        """Test hero product parsing."""
        soup = BeautifulSoup(mock_response.content, 'html.parser')
        product_elem = soup.select_one('.hero-product')
        
        hero_product = scraper._parse_hero_product(product_elem)
        
        assert isinstance(hero_product, HeroProduct)
        assert hero_product.title == "Featured Product"
        assert hero_product.price == "$29.99"
        assert hero_product.featured_section == "homepage"
    
    @pytest.mark.asyncio
    async def test_scrape_product_catalog_success(self, scraper, sample_product_json):
        """Test successful product catalog scraping."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_product_json
        
        insights = {"product_catalog": {}, "warnings": [], "errors": []}
        
        with patch.object(scraper, '_make_request', return_value=mock_response):
            await scraper._scrape_product_catalog(insights)
        
        assert insights["product_catalog"]["total_products"] == 1
        assert len(insights["product_catalog"]["products"]) == 1
        assert insights["product_catalog"]["products"][0]["title"] == "Test Product"
    
    @pytest.mark.asyncio
    async def test_scrape_product_catalog_failure(self, scraper):
        """Test failed product catalog scraping."""
        insights = {"product_catalog": {}, "warnings": [], "errors": []}
        
        with patch.object(scraper, '_make_request', return_value=None):
            await scraper._scrape_product_catalog(insights)
        
        assert len(insights["warnings"]) > 0
        assert "Product catalog not accessible" in insights["warnings"]
    
    @pytest.mark.asyncio
    async def test_scrape_hero_products(self, scraper, mock_response):
        """Test hero products scraping."""
        soup = BeautifulSoup(mock_response.content, 'html.parser')
        insights = {"hero_products": [], "errors": []}
        
        await scraper._scrape_hero_products(soup, insights)
        
        assert len(insights["hero_products"]) >= 1
        assert insights["hero_products"][0]["title"] == "Featured Product"
    
    def test_parse_faqs_from_page(self, scraper):
        """Test FAQ parsing from HTML."""
        html_content = """
        <div class="faq-item">
            <h3 class="faq-question">What is your return policy?</h3>
            <div class="faq-answer">We offer 30-day returns.</div>
        </div>
        <div class="faq-item">
            <h4 class="question">How do I track my order?</h4>
            <p class="answer">Use our tracking system.</p>
        </div>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        faqs = scraper._parse_faqs_from_page(soup)
        
        assert len(faqs) >= 1
        assert isinstance(faqs[0], FAQ)
        assert "return policy" in faqs[0].question.lower()
    
    @pytest.mark.asyncio
    async def test_scrape_contact_info(self, scraper, mock_response):
        """Test contact information scraping."""
        soup = BeautifulSoup(mock_response.content, 'html.parser')
        insights = {"contact_info": {}, "errors": []}
        
        await scraper._scrape_contact_info(soup, insights)
        
        contact_info = insights["contact_info"]
        assert "contact@teststore.com" in contact_info["emails"]
        assert any("1234567890" in phone for phone in contact_info["phone_numbers"])
    
    @pytest.mark.asyncio
    async def test_scrape_social_handles(self, scraper, mock_response):
        """Test social media handles scraping."""
        soup = BeautifulSoup(mock_response.content, 'html.parser')
        insights = {"social_handles": {}, "errors": []}
        
        await scraper._scrape_social_handles(soup, insights)
        
        social_handles = insights["social_handles"]
        assert "instagram" in social_handles
        assert "teststore" in social_handles["instagram"][0]
    
    def test_categorize_link(self, scraper):
        """Test link categorization."""
        patterns = {
            'contact': ['contact', 'support'],
            'blog': ['blog', 'news'],
            'tracking': ['track', 'order']
        }
        
        # Test contact link
        category = scraper._categorize_link("Contact Us", "/contact", patterns)
        assert category == "contact"
        
        # Test blog link
        category = scraper._categorize_link("Our Blog", "/blog", patterns)
        assert category == "blog"
        
        # Test tracking link
        category = scraper._categorize_link("Track Order", "/tracking", patterns)
        assert category == "tracking"
        
        # Test unknown link
        category = scraper._categorize_link("Random Page", "/random", patterns)
        assert category is None
    
    @pytest.mark.asyncio
    async def test_scrape_store_insights_integration(self, scraper):
        """Integration test for full store insights scraping."""
        website_url = "https://example-store.myshopify.com"
        
        # Mock all the HTTP requests
        mock_main_response = Mock()
        mock_main_response.content = b"""
        <html>
            <head><title>Example Store</title></head>
            <body>
                <h1>Welcome to Example Store</h1>
                <div class="featured-product">
                    <h3>Best Seller</h3>
                    <span class="price">$49.99</span>
                </div>
            </body>
        </html>
        """
        
        mock_products_response = Mock()
        mock_products_response.status_code = 200
        mock_products_response.json.return_value = {"products": []}
        
        def mock_request_side_effect(url, **kwargs):
            if 'products.json' in url:
                return mock_products_response
            else:
                return mock_main_response
        
        with patch.object(scraper, '_make_request', side_effect=mock_request_side_effect):
            insights = await scraper.scrape_store_insights(website_url)
        
        # Verify basic structure
        assert insights["store_url"] == website_url
        assert insights["store_name"] == "Example Store"
        assert insights["success"] == True
        assert "processing_time" in insights
        assert isinstance(insights["hero_products"], list)
        assert isinstance(insights["product_catalog"], dict)


class TestUtilityFunctions:
    """Test utility functions used by the scraper."""
    
    def test_extract_emails(self):
        """Test email extraction."""
        text = "Contact us at support@example.com or sales@example.com for help."
        emails = extract_emails(text)
        
        assert "support@example.com" in emails
        assert "sales@example.com" in emails
        assert len(emails) == 2
    
    def test_extract_phone_numbers(self):
        """Test phone number extraction."""
        text = "Call us at +1-234-567-8900 or (555) 123-4567 for support."
        phones = extract_phone_numbers(text)
        
        assert len(phones) > 0
        # Check that some digits are found
        assert any(char.isdigit() for phone in phones for char in phone)
    
    def test_extract_social_handles(self):
        """Test social media handle extraction."""
        text = "Follow us @teststore on Instagram and twitter.com/teststore"
        html = '<a href="https://facebook.com/teststore">Facebook</a>'
        
        handles = extract_social_handles(text, html)
        
        assert "instagram" in handles or "twitter" in handles or "facebook" in handles
