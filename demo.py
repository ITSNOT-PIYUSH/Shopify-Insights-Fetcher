#!/usr/bin/env python3
"""
Simple demo script for the Shopify Insights Fetcher API.
"""
import requests
import json
import time

def demo_shopify_insights():
    """Demonstrate the Shopify Insights Fetcher API."""
    
    print("🚀 Shopify Insights Fetcher - Demo")
    print("=" * 50)
    
    # API endpoint
    api_url = "http://localhost:8000"
    
    # Check if server is running
    try:
        health_response = requests.get(f"{api_url}/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ Server is running and healthy")
        else:
            print("❌ Server is not healthy")
            return
    except requests.exceptions.RequestException:
        print("❌ Server is not running. Please start it with: python run.py")
        return
    
    # Demo stores to test
    demo_stores = [
        "https://shop.polymer-project.org",
        "https://allbirds.com",
        "https://www.gymshark.com"
    ]
    
    print(f"\n🔍 Testing {len(demo_stores)} demo stores...")
    
    for i, store_url in enumerate(demo_stores, 1):
        print(f"\n[{i}/{len(demo_stores)}] Analyzing: {store_url}")
        print("-" * 40)
        
        # Make API request
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{api_url}/api/v1/fetch-insights",
                json={
                    "website_url": store_url,
                    "include_competitors": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Display results
                print(f"✅ Success! Processing time: {data.get('processing_time', 0):.2f}s")
                print(f"📦 Products found: {data.get('product_catalog', {}).get('total_products', 0)}")
                print(f"⭐ Featured products: {len(data.get('hero_products', []))}")
                print(f"❓ FAQs found: {len(data.get('faqs', []))}")
                
                contact_info = data.get('contact_info', {})
                print(f"📞 Contact info: {len(contact_info.get('emails', []))} emails, {len(contact_info.get('phone_numbers', []))} phones")
                
                social_handles = data.get('social_handles', {})
                total_social = sum(len(handles) for handles in social_handles.values())
                print(f"📱 Social handles: {total_social} found")
                
                if data.get('privacy_policy'):
                    print("📜 Privacy policy: Found")
                if data.get('return_refund_policy'):
                    print("📜 Return policy: Found")
                    
            else:
                print(f"❌ API Error: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Details: {error_data.get('detail', 'Unknown error')}")
                except:
                    print(f"   Details: {response.text}")
                    
        except requests.exceptions.Timeout:
            print("⏰ Request timed out (this can happen with complex stores)")
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
    
    print(f"\n🎉 Demo completed!")
    print(f"\n📖 For more details, visit: {api_url}/docs")

if __name__ == "__main__":
    demo_shopify_insights()
