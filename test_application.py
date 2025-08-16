#!/usr/bin/env python3
"""
Quick test script to verify the Shopify Insights Fetcher application works.
"""
import asyncio
import requests
import json
from app.services.scraper import ShopifyScraperService
from app.core.utils import normalize_url, extract_emails, extract_social_handles


async def test_scraper_service():
    """Test the scraper service directly."""
    print("🧪 Testing Scraper Service...")
    
    scraper = ShopifyScraperService()
    
    # Test a mock Shopify store (using a safe example)
    test_url = "https://shop.polymer-project.org"  # Google's example store
    
    try:
        print(f"📊 Scraping insights from: {test_url}")
        insights = await scraper.scrape_store_insights(test_url)
        
        print(f"✅ Success: {insights['success']}")
        print(f"🏪 Store Name: {insights.get('store_name', 'Unknown')}")
        print(f"📦 Products Found: {insights['product_catalog']['total_products']}")
        print(f"⭐ Hero Products: {len(insights['hero_products'])}")
        print(f"❓ FAQs Found: {len(insights['faqs'])}")
        print(f"📧 Contact Emails: {len(insights['contact_info']['emails'])}")
        print(f"📱 Social Handles: {sum(len(handles) for handles in insights['social_handles'].values())}")
        print(f"⏱️  Processing Time: {insights['processing_time']:.2f}s")
        
        if insights['errors']:
            print(f"⚠️  Errors: {insights['errors']}")
        if insights['warnings']:
            print(f"⚠️  Warnings: {insights['warnings']}")
            
    except Exception as e:
        print(f"❌ Error testing scraper: {e}")


def test_utility_functions():
    """Test utility functions."""
    print("\n🔧 Testing Utility Functions...")
    
    # Test URL normalization
    test_urls = [
        "example.com",
        "https://example.com",
        "http://example.com/path"
    ]
    
    for url in test_urls:
        normalized = normalize_url(url)
        print(f"🔗 {url} → {normalized}")
    
    # Test email extraction
    test_text = "Contact us at support@example.com or sales@test.com for assistance."
    emails = extract_emails(test_text)
    print(f"📧 Extracted emails: {emails}")
    
    # Test social handle extraction
    social_text = "Follow us @teststore on Instagram and twitter.com/teststore"
    social_html = '<a href="https://facebook.com/teststore">Facebook</a>'
    handles = extract_social_handles(social_text, social_html)
    print(f"📱 Extracted social handles: {handles}")


def test_api_endpoints():
    """Test API endpoints if the server is running."""
    print("\n🌐 Testing API Endpoints...")
    
    base_url = "http://localhost:8000"
    
    try:
        # Test health endpoint
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health Check: {health_data['status']}")
            print(f"💾 Database Connected: {health_data['database_connected']}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    
    except requests.exceptions.ConnectionError:
        print("⚠️  Server not running. Start with: python run.py")
    except Exception as e:
        print(f"❌ Error testing API: {e}")


def test_models():
    """Test Pydantic models."""
    print("\n📋 Testing Pydantic Models...")
    
    from app.models.schemas import InsightsRequest, Product, HeroProduct
    
    # Test request model
    try:
        request = InsightsRequest(
            website_url="example.com",
            include_competitors=True
        )
        print(f"✅ Request model: {request.website_url}")
    except Exception as e:
        print(f"❌ Request model error: {e}")
    
    # Test product model
    try:
        product = Product(
            title="Test Product",
            price="29.99",
            available=True
        )
        print(f"✅ Product model: {product.title}")
    except Exception as e:
        print(f"❌ Product model error: {e}")
    
    # Test hero product model
    try:
        hero = HeroProduct(
            title="Featured Product",
            price="$49.99",
            featured_section="homepage"
        )
        print(f"✅ Hero product model: {hero.title}")
    except Exception as e:
        print(f"❌ Hero product model error: {e}")


async def main():
    """Run all tests."""
    print("🚀 Starting Shopify Insights Fetcher Tests\n")
    
    # Test utility functions first
    test_utility_functions()
    
    # Test models
    test_models()
    
    # Test scraper service
    await test_scraper_service()
    
    # Test API (if server is running)
    test_api_endpoints()
    
    print("\n✨ Test completed!")
    print("\n🔧 To run the application:")
    print("   python run.py")
    print("\n📖 API Documentation:")
    print("   http://localhost:8000/docs")
    print("\n🧪 Run unit tests:")
    print("   pytest")


if __name__ == "__main__":
    asyncio.run(main())
