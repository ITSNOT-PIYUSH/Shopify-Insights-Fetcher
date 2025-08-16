"""
Web scraping service for extracting insights from Shopify stores.
"""
import json
import logging
import re
import time
import asyncio
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.core.config import settings
from app.core.utils import (
    normalize_url, is_valid_url, is_shopify_store, extract_domain,
    extract_emails, extract_phone_numbers, extract_social_handles,
    clean_text, get_absolute_url
)
from app.models.schemas import (
    Product, ProductCatalog, HeroProduct, Policy, FAQ, ContactInfo,
    SocialHandles, ImportantLink, BrandContext, CompetitorInsight
)

logger = logging.getLogger(__name__)


class ShopifyScraperService:
    """Service for scraping Shopify store insights."""
    
    def __init__(self):
        """Initialize the scraper service."""
        self.session = self._create_session()
        self.base_url = ""
        self.domain = ""
    
    def _create_session(self) -> requests.Session:
        """Create a configured requests session with retries."""
        session = requests.Session()
        
        # Configure retries
        retry_strategy = Retry(
            total=settings.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],  # Updated parameter name
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set headers
        session.headers.update({
            'User-Agent': settings.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        return session
    
    def _make_request(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Make a HTTP request with error handling."""
        try:
            response = self.session.get(
                url, 
                timeout=settings.request_timeout,
                **kwargs
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            # Only log actual errors, not expected 404s for missing pages
            if not (hasattr(e, 'response') and e.response and e.response.status_code == 404):
                logger.warning(f"Request failed for {url}: {e}")
            return None
    
    def _get_soup(self, url: str) -> Optional[BeautifulSoup]:
        """Get BeautifulSoup object from URL."""
        response = self._make_request(url)
        if not response:
            return None
        
        try:
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            logger.error(f"Failed to parse HTML for {url}: {e}")
            return None
    
    async def scrape_store_insights(self, website_url: str) -> Dict[str, Any]:
        """
        Main method to scrape all insights from a Shopify store.
        
        Args:
            website_url: The store URL to scrape
            
        Returns:
            Dictionary containing all extracted insights
        """
        start_time = time.time()
        
        # Normalize and validate URL
        self.base_url = normalize_url(website_url)
        self.domain = extract_domain(self.base_url)
        
        if not is_valid_url(self.base_url):
            raise ValueError(f"Invalid URL: {website_url}")
        
        logger.info(f"🔍 Analyzing store: {self.base_url}")
        
        # Initialize results structure
        insights = {
            "store_url": self.base_url,
            "store_name": None,
            "is_shopify_store": is_shopify_store(self.base_url),
            "product_catalog": {"total_products": 0, "products": [], "has_more": False},
            "hero_products": [],
            "privacy_policy": None,
            "return_refund_policy": None,
            "terms_of_service": None,
            "shipping_policy": None,
            "other_policies": [],
            "faqs": [],
            "contact_info": {"emails": [], "phone_numbers": [], "addresses": []},
            "social_handles": {},
            "brand_context": {},
            "important_links": [],
            "competitors": [],
            "scraped_at": time.time(),
            "processing_time": 0,
            "success": True,
            "errors": [],
            "warnings": []
        }
        
        try:
            # Run scraping tasks
            await self._scrape_all_insights(insights)
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            insights["success"] = False
            insights["errors"].append(str(e))
        
        finally:
            insights["processing_time"] = time.time() - start_time
            logger.info(f"✅ Analysis completed in {insights['processing_time']:.2f} seconds")
        
        return insights
    
    async def _scrape_all_insights(self, insights: Dict[str, Any]) -> None:
        """Scrape all insights and populate the insights dictionary."""
        
        # Get the main page first to extract basic info
        soup = self._get_soup(self.base_url)
        if not soup:
            raise Exception("Failed to fetch the main page")
        
        # Extract store name
        insights["store_name"] = self._extract_store_name(soup)
        
        # Run all scraping tasks
        tasks = [
            self._scrape_product_catalog(insights),
            self._scrape_hero_products(soup, insights),
            self._scrape_policies(insights),
            self._scrape_faqs(insights),
            self._scrape_contact_info(soup, insights),
            self._scrape_social_handles(soup, insights),
            self._scrape_brand_context(soup, insights),
            self._scrape_important_links(soup, insights)
        ]
        
        # Execute tasks concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def _extract_store_name(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract store name from the homepage."""
        try:
            # Try different selectors for store name
            selectors = [
                'title',
                '.site-header__logo img',
                '.header__logo img',
                '.logo img',
                'h1.site-title',
                '.site-title',
                '.header-logo'
            ]
            
            for selector in selectors:
                element = soup.select_one(selector)
                if element:
                    if element.name == 'img' and element.get('alt'):
                        return clean_text(element.get('alt'))
                    elif element.get_text():
                        return clean_text(element.get_text())
            
            # Fallback to title tag
            title = soup.find('title')
            if title:
                return clean_text(title.get_text()).split(' - ')[0]
                
        except Exception as e:
            logger.warning(f"Failed to extract store name: {e}")
        
        return None
    
    async def _scrape_product_catalog(self, insights: Dict[str, Any]) -> None:
        """Scrape the product catalog using /products.json endpoint."""
        try:
            products_url = urljoin(self.base_url, '/products.json')
            response = self._make_request(products_url)
            
            if response and response.status_code == 200:
                try:
                    data = response.json()
                    products = data.get('products', [])
                    
                    catalog_products = []
                    for product_data in products:
                        product = self._parse_product_json(product_data)
                        if product:
                            catalog_products.append(product)
                    
                    insights["product_catalog"] = {
                        "total_products": len(catalog_products),
                        "products": catalog_products,
                        "has_more": len(products) >= 250  # Shopify default limit
                    }
                    
                    logger.info(f"📦 Found {len(catalog_products)} products")
                    
                except json.JSONDecodeError:
                    logger.warning("Failed to parse products.json")
                    insights["warnings"].append("Could not parse product catalog JSON")
            else:
                logger.warning("Products.json endpoint not accessible")
                insights["warnings"].append("Product catalog not accessible")
                
        except Exception as e:
            logger.error(f"Error scraping product catalog: {e}")
            insights["errors"].append(f"Product catalog error: {str(e)}")
    
    def _parse_product_json(self, product_data: Dict[str, Any]) -> Optional[Product]:
        """Parse product data from JSON API response."""
        try:
            images = []
            if product_data.get('images'):
                images = [img.get('src', '') for img in product_data['images'] if img.get('src')]
            
            variants = product_data.get('variants', [])
            price = None
            compare_at_price = None
            available = False
            
            if variants:
                # Get price from first variant
                first_variant = variants[0]
                price = str(first_variant.get('price', ''))
                compare_at_price = first_variant.get('compare_at_price')
                if compare_at_price:
                    compare_at_price = str(compare_at_price)
                
                # Check availability
                available = any(variant.get('available', False) for variant in variants)
            
            return Product(
                id=product_data.get('id'),
                title=clean_text(product_data.get('title', '')),
                handle=product_data.get('handle'),
                description=clean_text(product_data.get('body_html', '')),
                vendor=product_data.get('vendor'),
                product_type=product_data.get('product_type'),
                tags=product_data.get('tags', []),
                price=price,
                compare_at_price=compare_at_price,
                available=available,
                images=images,
                variants=variants,
                created_at=product_data.get('created_at'),
                updated_at=product_data.get('updated_at')
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse product: {e}")
            return None
    
    async def _scrape_hero_products(self, soup: BeautifulSoup, insights: Dict[str, Any]) -> None:
        """Scrape hero/featured products from the homepage."""
        try:
            hero_products = []
            
            # Common selectors for featured products
            selectors = [
                '.featured-product',
                '.hero-product',
                '.product-hero',
                '.featured-collection .product-item',
                '.collection-hero .product',
                '.homepage-product',
                '.product-card',
                '.grid-product'
            ]
            
            for selector in selectors:
                products = soup.select(selector)
                for product_elem in products[:5]:  # Limit to first 5
                    hero_product = self._parse_hero_product(product_elem)
                    if hero_product and hero_product not in hero_products:
                        hero_products.append(hero_product)
                
                if hero_products:
                    break  # Found products with this selector
            
            insights["hero_products"] = hero_products
            if hero_products:
                logger.info(f"⭐ Found {len(hero_products)} featured products")
            else:
                logger.info("⭐ No featured products found on homepage")
            
        except Exception as e:
            logger.error(f"Error scraping hero products: {e}")
            insights["errors"].append(f"Hero products error: {str(e)}")
    
    def _parse_hero_product(self, element: Tag) -> Optional[HeroProduct]:
        """Parse a hero product from HTML element."""
        try:
            # Extract title
            title_elem = element.select_one('.product-title, .product-name, h3, h2, a')
            title = clean_text(title_elem.get_text()) if title_elem else "Unknown Product"
            
            # Extract description
            desc_elem = element.select_one('.product-description, .product-summary, p')
            description = clean_text(desc_elem.get_text()) if desc_elem else None
            
            # Extract image
            img_elem = element.select_one('img')
            image_url = None
            if img_elem:
                image_url = img_elem.get('src') or img_elem.get('data-src')
                if image_url:
                    image_url = get_absolute_url(self.base_url, image_url)
            
            # Extract product URL
            link_elem = element.select_one('a')
            product_url = None
            if link_elem and link_elem.get('href'):
                product_url = get_absolute_url(self.base_url, link_elem.get('href'))
            
            # Extract price
            price_elem = element.select_one('.price, .product-price, .money')
            price = clean_text(price_elem.get_text()) if price_elem else None
            
            return HeroProduct(
                title=title,
                description=description,
                image_url=image_url,
                product_url=product_url,
                price=price,
                featured_section="homepage"
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse hero product: {e}")
            return None
    
    async def _scrape_policies(self, insights: Dict[str, Any]) -> None:
        """Scrape store policies (privacy, refund, terms, etc.)."""
        try:
            policy_urls = {
                'privacy_policy': ['/pages/privacy-policy', '/privacy-policy', '/pages/privacy'],
                'return_refund_policy': ['/pages/refund-policy', '/pages/returns', '/refund-policy', '/returns'],
                'terms_of_service': ['/pages/terms-of-service', '/terms-of-service', '/pages/terms'],
                'shipping_policy': ['/pages/shipping-policy', '/shipping-policy', '/pages/shipping']
            }
            
            for policy_type, possible_urls in policy_urls.items():
                policy = await self._scrape_policy(possible_urls, policy_type)
                if policy:
                    insights[policy_type] = policy
            
        except Exception as e:
            logger.error(f"Error scraping policies: {e}")
            insights["errors"].append(f"Policies error: {str(e)}")
    
    async def _scrape_policy(self, urls: List[str], policy_type: str) -> Optional[Policy]:
        """Scrape a specific policy from possible URLs."""
        for url_path in urls:
            full_url = urljoin(self.base_url, url_path)
            soup = self._get_soup(full_url)
            
            if soup:
                # Find main content
                content_selectors = [
                    '.page-content',
                    '.policy-content',
                    '.main-content',
                    '.content',
                    'main',
                    '.page'
                ]
                
                content = ""
                for selector in content_selectors:
                    content_elem = soup.select_one(selector)
                    if content_elem:
                        content = clean_text(content_elem.get_text())
                        break
                
                if content:
                    title_elem = soup.select_one('h1, .page-title, .policy-title')
                    title = clean_text(title_elem.get_text()) if title_elem else policy_type.replace('_', ' ').title()
                    
                    return Policy(
                        title=title,
                        content=content,
                        url=full_url,
                        type=policy_type
                    )
        
        return None
    
    async def _scrape_faqs(self, insights: Dict[str, Any]) -> None:
        """Scrape FAQ sections."""
        try:
            faq_urls = [
                '/pages/faq',
                '/pages/frequently-asked-questions',
                '/faq',
                '/help',
                '/support'
            ]
            
            faqs = []
            
            for url_path in faq_urls:
                full_url = urljoin(self.base_url, url_path)
                soup = self._get_soup(full_url)
                
                if soup:
                    page_faqs = self._parse_faqs_from_page(soup)
                    faqs.extend(page_faqs)
                    
                    if faqs:
                        break  # Found FAQs, no need to check other URLs
            
            insights["faqs"] = faqs
            if faqs:
                logger.info(f"❓ Found {len(faqs)} FAQs")
            else:
                logger.info("❓ No FAQ section found")
            
        except Exception as e:
            logger.error(f"Error scraping FAQs: {e}")
            insights["errors"].append(f"FAQs error: {str(e)}")
    
    def _parse_faqs_from_page(self, soup: BeautifulSoup) -> List[FAQ]:
        """Parse FAQs from a page."""
        faqs = []
        
        try:
            # Method 1: Look for accordion/collapsible FAQ sections
            accordion_items = soup.select('.accordion-item, .faq-item, .collapsible-item')
            for item in accordion_items:
                question_elem = item.select_one('.accordion-title, .faq-question, .question, h3, h4')
                answer_elem = item.select_one('.accordion-content, .faq-answer, .answer, .content')
                
                if question_elem and answer_elem:
                    faqs.append(FAQ(
                        question=clean_text(question_elem.get_text()),
                        answer=clean_text(answer_elem.get_text())
                    ))
            
            # Method 2: Look for dt/dd pairs
            if not faqs:
                dt_elements = soup.select('dt')
                for dt in dt_elements:
                    dd = dt.find_next_sibling('dd')
                    if dd:
                        faqs.append(FAQ(
                            question=clean_text(dt.get_text()),
                            answer=clean_text(dd.get_text())
                        ))
            
            # Method 3: Look for h3/h4 followed by paragraphs
            if not faqs:
                headings = soup.select('h3, h4, h5')
                for heading in headings:
                    question_text = clean_text(heading.get_text())
                    if '?' in question_text:  # Likely a question
                        # Find next paragraph or div
                        next_elem = heading.find_next_sibling(['p', 'div'])
                        if next_elem:
                            faqs.append(FAQ(
                                question=question_text,
                                answer=clean_text(next_elem.get_text())
                            ))
                            
        except Exception as e:
            logger.warning(f"Error parsing FAQs: {e}")
        
        return faqs
    
    async def _scrape_contact_info(self, soup: BeautifulSoup, insights: Dict[str, Any]) -> None:
        """Scrape contact information."""
        try:
            # Get page content for analysis
            page_text = soup.get_text()
            page_html = str(soup)
            
            # Extract emails
            emails = extract_emails(page_text)
            
            # Extract phone numbers
            phone_numbers = extract_phone_numbers(page_text)
            
            # Extract addresses (basic implementation)
            addresses = self._extract_addresses(page_text)
            
            # Look for contact page
            contact_form_url = None
            contact_links = soup.select('a[href*="contact"]')
            if contact_links:
                contact_form_url = get_absolute_url(self.base_url, contact_links[0].get('href'))
            
            insights["contact_info"] = {
                "emails": emails,
                "phone_numbers": phone_numbers,
                "addresses": addresses,
                "contact_form_url": contact_form_url
            }
            
            contact_summary = []
            if emails:
                contact_summary.append(f"{len(emails)} email{'s' if len(emails) != 1 else ''}")
            if phone_numbers:
                contact_summary.append(f"{len(phone_numbers)} phone{'s' if len(phone_numbers) != 1 else ''}")
            if addresses:
                contact_summary.append(f"{len(addresses)} address{'es' if len(addresses) != 1 else ''}")
            
            if contact_summary:
                logger.info(f"📞 Found contact info: {', '.join(contact_summary)}")
            else:
                logger.info("📞 No contact information found")
            
        except Exception as e:
            logger.error(f"Error scraping contact info: {e}")
            insights["errors"].append(f"Contact info error: {str(e)}")
    
    def _extract_addresses(self, text: str) -> List[str]:
        """Extract physical addresses from text."""
        addresses = []
        
        # Simple pattern for addresses (can be improved)
        address_patterns = [
            r'\d+\s+[\w\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr)[\w\s,]*\d{5}',
            r'[\w\s]+,\s*[A-Z]{2}\s+\d{5}',  # City, State ZIP
        ]
        
        for pattern in address_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            addresses.extend(matches)
        
        return list(set(addresses))
    
    async def _scrape_social_handles(self, soup: BeautifulSoup, insights: Dict[str, Any]) -> None:
        """Scrape social media handles and links."""
        try:
            page_text = soup.get_text()
            page_html = str(soup)
            
            social_handles = extract_social_handles(page_text, page_html)
            insights["social_handles"] = social_handles
            
            total_handles = sum(len(handles) for handles in social_handles.values())
            if total_handles > 0:
                platforms = list(social_handles.keys())
                logger.info(f"📱 Found {total_handles} social handle{'s' if total_handles != 1 else ''} ({', '.join(platforms)})")
            else:
                logger.info("📱 No social media handles found")
            
        except Exception as e:
            logger.error(f"Error scraping social handles: {e}")
            insights["errors"].append(f"Social handles error: {str(e)}")
    
    async def _scrape_brand_context(self, soup: BeautifulSoup, insights: Dict[str, Any]) -> None:
        """Scrape brand context and about information."""
        try:
            brand_context = {}
            
            # Look for about page
            about_urls = ['/pages/about', '/about', '/pages/about-us', '/about-us']
            
            for url_path in about_urls:
                full_url = urljoin(self.base_url, url_path)
                about_soup = self._get_soup(full_url)
                
                if about_soup:
                    content_elem = about_soup.select_one('.page-content, .about-content, main, .content')
                    if content_elem:
                        content = clean_text(content_elem.get_text())
                        brand_context["description"] = content
                        break
            
            # Extract from homepage if no about page
            if not brand_context.get("description"):
                hero_sections = soup.select('.hero, .banner, .intro, .about-section')
                for section in hero_sections:
                    text = clean_text(section.get_text())
                    if len(text) > 100:  # Substantial content
                        brand_context["description"] = text
                        break
            
            # Extract other brand info
            brand_context["name"] = insights.get("store_name")
            
            insights["brand_context"] = brand_context
            
        except Exception as e:
            logger.error(f"Error scraping brand context: {e}")
            insights["errors"].append(f"Brand context error: {str(e)}")
    
    async def _scrape_important_links(self, soup: BeautifulSoup, insights: Dict[str, Any]) -> None:
        """Scrape important links (order tracking, contact, blog, etc.)."""
        try:
            important_links = []
            
            # Define important link patterns
            important_patterns = {
                'order tracking': ['track', 'order', 'tracking'],
                'contact': ['contact', 'support', 'help'],
                'blog': ['blog', 'news', 'articles'],
                'support': ['support', 'help', 'faq'],
                'shipping': ['shipping', 'delivery'],
                'returns': ['return', 'refund'],
                'size guide': ['size', 'guide', 'fitting'],
            }
            
            # Find links in navigation and footer
            nav_links = soup.select('nav a, .navigation a, .menu a, footer a')
            
            for link in nav_links:
                href = link.get('href')
                text = clean_text(link.get_text())
                
                if href and text:
                    absolute_url = get_absolute_url(self.base_url, href)
                    
                    # Categorize the link
                    category = self._categorize_link(text, href, important_patterns)
                    
                    if category:
                        important_links.append(ImportantLink(
                            title=text,
                            url=absolute_url,
                            category=category
                        ))
            
            # Remove duplicates
            seen_urls = set()
            unique_links = []
            for link in important_links:
                if link.url not in seen_urls:
                    seen_urls.add(link.url)
                    unique_links.append(link)
            
            insights["important_links"] = unique_links
            if unique_links:
                logger.info(f"🔗 Found {len(unique_links)} important link{'s' if len(unique_links) != 1 else ''}")
            else:
                logger.info("🔗 No important links found")
            
        except Exception as e:
            logger.error(f"Error scraping important links: {e}")
            insights["errors"].append(f"Important links error: {str(e)}")
    
    def _categorize_link(self, text: str, href: str, patterns: Dict[str, List[str]]) -> Optional[str]:
        """Categorize a link based on its text and href."""
        text_lower = text.lower()
        href_lower = href.lower()
        
        for category, keywords in patterns.items():
            for keyword in keywords:
                if keyword in text_lower or keyword in href_lower:
                    return category
        
        return None
    
    async def scrape_competitor_analysis(self, brand_name: str) -> List[CompetitorInsight]:
        """
        Scrape competitor analysis (bonus feature).
        
        Args:
            brand_name: The brand name to search competitors for
            
        Returns:
            List of competitor insights
        """
        # This is a simplified implementation
        # In a real application, you would integrate with Google Search API
        # or other competitor analysis tools
        
        competitors = []
        
        try:
            # Mock competitor data for demo
            # In practice, you would search for competitors and scrape their data
            mock_competitors = [
                {
                    "name": f"Competitor of {brand_name}",
                    "website_url": "https://example-competitor.com",
                    "description": "A similar brand in the same industry"
                }
            ]
            
            for comp_data in mock_competitors:
                competitors.append(CompetitorInsight(**comp_data))
                
        except Exception as e:
            logger.error(f"Error in competitor analysis: {e}")
        
        return competitors
