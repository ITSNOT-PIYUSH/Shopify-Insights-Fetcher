"""
Pydantic models for request/response schemas.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, validator
from datetime import datetime


class InsightsRequest(BaseModel):
    """Request model for fetching insights."""
    
    website_url: str = Field(
        ...,
        description="The Shopify store URL to analyze",
        example="https://example-store.myshopify.com"
    )
    include_competitors: bool = Field(
        default=False,
        description="Whether to include competitor analysis"
    )
    
    @validator('website_url')
    def validate_url(cls, v):
        """Validate and normalize the website URL."""
        if not v:
            raise ValueError("Website URL is required")
        
        # Basic URL normalization
        if not v.startswith(('http://', 'https://')):
            v = f"https://{v}"
        
        return v


class Product(BaseModel):
    """Product model for catalog items."""
    
    id: Optional[int] = None
    title: str
    handle: Optional[str] = None
    description: Optional[str] = None
    vendor: Optional[str] = None
    product_type: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    price: Optional[str] = None
    compare_at_price: Optional[str] = None
    available: bool = True
    images: List[str] = Field(default_factory=list)
    variants: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProductCatalog(BaseModel):
    """Product catalog model."""
    
    total_products: int = 0
    products: List[Product] = Field(default_factory=list)
    has_more: bool = False
    next_page_url: Optional[str] = None


class HeroProduct(BaseModel):
    """Hero product model for featured products on homepage."""
    
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    price: Optional[str] = None
    featured_section: Optional[str] = None  # e.g., "banner", "featured", etc.


class Policy(BaseModel):
    """Policy model for various store policies."""
    
    title: str
    content: str
    url: Optional[str] = None
    last_updated: Optional[datetime] = None
    type: str  # e.g., "privacy", "refund", "terms", "shipping"


class FAQ(BaseModel):
    """FAQ model for frequently asked questions."""
    
    question: str
    answer: str
    category: Optional[str] = None
    order: Optional[int] = None


class ContactInfo(BaseModel):
    """Contact information model."""
    
    emails: List[str] = Field(default_factory=list)
    phone_numbers: List[str] = Field(default_factory=list)
    addresses: List[str] = Field(default_factory=list)
    contact_form_url: Optional[str] = None
    support_url: Optional[str] = None


class SocialHandles(BaseModel):
    """Social media handles model."""
    
    instagram: List[str] = Field(default_factory=list)
    facebook: List[str] = Field(default_factory=list)
    twitter: List[str] = Field(default_factory=list)
    tiktok: List[str] = Field(default_factory=list)
    youtube: List[str] = Field(default_factory=list)
    linkedin: List[str] = Field(default_factory=list)
    pinterest: List[str] = Field(default_factory=list)


class ImportantLink(BaseModel):
    """Important link model."""
    
    title: str
    url: str
    description: Optional[str] = None
    category: Optional[str] = None  # e.g., "support", "tracking", "blog", etc.


class BrandContext(BaseModel):
    """Brand context model containing about information."""
    
    name: Optional[str] = None
    description: Optional[str] = None
    mission: Optional[str] = None
    story: Optional[str] = None
    values: List[str] = Field(default_factory=list)
    founded: Optional[str] = None
    location: Optional[str] = None


class CompetitorInsight(BaseModel):
    """Competitor insight model."""
    
    name: str
    website_url: str
    description: Optional[str] = None
    estimated_products: Optional[int] = None
    price_range: Optional[str] = None
    social_presence: Optional[SocialHandles] = None


class InsightsResponse(BaseModel):
    """Response model for insights data."""
    
    # Basic store information
    store_url: str
    store_name: Optional[str] = None
    is_shopify_store: bool = True
    
    # Core insights
    product_catalog: ProductCatalog = Field(default_factory=ProductCatalog)
    hero_products: List[HeroProduct] = Field(default_factory=list)
    
    # Policies and FAQ
    privacy_policy: Optional[Policy] = None
    return_refund_policy: Optional[Policy] = None
    terms_of_service: Optional[Policy] = None
    shipping_policy: Optional[Policy] = None
    other_policies: List[Policy] = Field(default_factory=list)
    faqs: List[FAQ] = Field(default_factory=list)
    
    # Contact and social
    contact_info: ContactInfo = Field(default_factory=ContactInfo)
    social_handles: SocialHandles = Field(default_factory=SocialHandles)
    
    # Brand information
    brand_context: BrandContext = Field(default_factory=BrandContext)
    important_links: List[ImportantLink] = Field(default_factory=list)
    
    # Bonus features
    competitors: List[CompetitorInsight] = Field(default_factory=list)
    
    # Metadata
    scraped_at: datetime = Field(default_factory=datetime.now)
    processing_time: Optional[float] = None  # in seconds
    success: bool = True
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class HealthCheckResponse(BaseModel):
    """Health check response model."""
    
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"
    database_connected: bool = False


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str
    detail: Optional[str] = None
    status_code: int
    timestamp: datetime = Field(default_factory=datetime.now)


# Database models (for SQLAlchemy ORM)
class InsightsRecord(BaseModel):
    """Database record model for storing insights."""
    
    id: Optional[int] = None
    store_url: str
    store_name: Optional[str] = None
    insights_data: Dict[str, Any]  # JSON field for storing the full insights
    scraped_at: datetime = Field(default_factory=datetime.now)
    processing_time: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True
