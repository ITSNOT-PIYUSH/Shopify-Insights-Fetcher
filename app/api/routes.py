"""
API routes for the Shopify Insights Fetcher.
"""
import logging
import time
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse

from app.models.schemas import (
    InsightsRequest, InsightsResponse, ErrorResponse, 
    InsightsRecord, HealthCheckResponse
)
from app.services.scraper import ShopifyScraperService
from app.db.database import save_insights_record, get_insights_record, get_all_insights_records
from app.core.utils import is_valid_url, normalize_url
from app.core.config import settings

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


def get_scraper_service() -> ShopifyScraperService:
    """Dependency to get scraper service instance."""
    return ShopifyScraperService()


@router.post(
    "/fetch-insights",
    response_model=InsightsResponse,
    summary="Fetch Store Insights",
    description="Extract comprehensive insights from a Shopify store including products, policies, FAQs, and more",
    responses={
        200: {"description": "Successfully extracted insights"},
        401: {"description": "Website not found or not accessible"},
        422: {"description": "Invalid request parameters"},
        500: {"description": "Internal server error"}
    }
)
async def fetch_insights(
    request: InsightsRequest,
    background_tasks: BackgroundTasks,
    scraper: ShopifyScraperService = Depends(get_scraper_service)
) -> InsightsResponse:
    """
    Fetch comprehensive insights from a Shopify store.
    
    This endpoint extracts:
    - Product catalog
    - Hero/featured products
    - Store policies (privacy, refund, terms, shipping)
    - FAQs
    - Contact information
    - Social media handles
    - Brand context and about information
    - Important links
    - Optional: Competitor analysis
    """
    start_time = time.time()
    
    try:
        # Validate and normalize URL
        website_url = normalize_url(request.website_url)
        
        if not is_valid_url(website_url):
            raise HTTPException(
                status_code=422,
                detail=f"Invalid website URL: {request.website_url}"
            )
        
        logger.info(f"🚀 Processing insights request for: {website_url}")
        
        # Check if we have recent cached data
        cached_insights = get_insights_record(website_url)
        if cached_insights:
            # Check if data is recent (less than 24 hours old)
            scraped_at = cached_insights.get("scraped_at", 0)
            if time.time() - scraped_at < 86400:  # 24 hours
                logger.info(f"⚡ Returning cached insights for: {website_url}")
                
                # Convert to response model
                response_data = cached_insights.copy()
                response_data["processing_time"] = time.time() - start_time
                
                try:
                    return InsightsResponse(**response_data)
                except Exception as e:
                    logger.warning(f"Failed to parse cached insights: {e}")
                    # Fall through to scrape fresh data
        
        # Scrape insights
        try:
            insights_data = await scraper.scrape_store_insights(website_url)
        except ValueError as e:
            # Invalid URL or store not accessible
            raise HTTPException(
                status_code=401,
                detail=f"Website not found or not accessible: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Scraping failed for {website_url}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to extract insights from the website"
            )
        
        # Add competitor analysis if requested
        if request.include_competitors and insights_data.get("store_name"):
            try:
                competitors = await scraper.scrape_competitor_analysis(insights_data["store_name"])
                insights_data["competitors"] = [comp.dict() for comp in competitors]
            except Exception as e:
                logger.warning(f"Competitor analysis failed: {e}")
                insights_data["warnings"].append(f"Competitor analysis failed: {str(e)}")
        
        # Update processing time
        insights_data["processing_time"] = time.time() - start_time
        
        # Convert to response model
        try:
            response = InsightsResponse(**insights_data)
        except Exception as e:
            logger.error(f"Failed to create response model: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to process extracted insights"
            )
        
        # Save to database in background
        background_tasks.add_task(
            save_insights_to_db,
            website_url,
            insights_data.get("store_name"),
            insights_data,
            insights_data.get("processing_time"),
            insights_data.get("success", True),
            None if insights_data.get("success", True) else str(insights_data.get("errors", []))
        )
        
        logger.info(f"✅ Successfully processed insights for {website_url} in {response.processing_time:.2f}s")
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing insights request: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing the request"
        )


def save_insights_to_db(
    store_url: str,
    store_name: Optional[str],
    insights_data: dict,
    processing_time: Optional[float],
    success: bool,
    error_message: Optional[str]
) -> None:
    """Background task to save insights to database."""
    try:
        record_id = save_insights_record(
            store_url=store_url,
            store_name=store_name,
            insights_data=insights_data,
            processing_time=processing_time,
            success=success,
            error_message=error_message
        )
        if record_id:
            logger.info(f"💾 Saved insights record {record_id}")
        # Remove the noisy warning for expected behavior
    except Exception as e:
        logger.error(f"Error saving insights to database: {e}")


@router.get(
    "/insights/history",
    summary="Get Insights History",
    description="Retrieve historical insights data with pagination"
)
async def get_insights_history(
    limit: int = 50,
    offset: int = 0
):
    """
    Get historical insights data.
    
    Args:
        limit: Maximum number of records to return (max 100)
        offset: Number of records to skip
    """
    try:
        # Validate parameters
        if limit > 100:
            limit = 100
        if limit < 1:
            limit = 10
        if offset < 0:
            offset = 0
        
        records = get_all_insights_records(limit=limit, offset=offset)
        
        return {
            "records": records,
            "limit": limit,
            "offset": offset,
            "count": len(records)
        }
        
    except Exception as e:
        logger.error(f"Error retrieving insights history: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve insights history"
        )


@router.get(
    "/insights/{store_url:path}",
    response_model=InsightsResponse,
    summary="Get Cached Insights",
    description="Retrieve cached insights for a specific store URL"
)
async def get_cached_insights(store_url: str):
    """
    Get cached insights for a specific store.
    
    Args:
        store_url: The store URL to retrieve insights for
    """
    try:
        # Normalize URL
        normalized_url = normalize_url(store_url)
        
        # Get from database
        insights_data = get_insights_record(normalized_url)
        
        if not insights_data:
            raise HTTPException(
                status_code=404,
                detail=f"No cached insights found for: {store_url}"
            )
        
        return InsightsResponse(**insights_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving cached insights: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve cached insights"
        )


@router.delete(
    "/insights/{store_url:path}",
    summary="Clear Cached Insights",
    description="Clear cached insights for a specific store URL"
)
async def clear_cached_insights(store_url: str):
    """
    Clear cached insights for a specific store.
    
    Args:
        store_url: The store URL to clear insights for
    """
    try:
        # This would require implementing a delete function in database.py
        # For now, return a success message
        
        return {
            "message": f"Cache clearing requested for: {store_url}",
            "note": "Cache clearing functionality to be implemented"
        }
        
    except Exception as e:
        logger.error(f"Error clearing cached insights: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to clear cached insights"
        )


@router.get(
    "/stats",
    summary="Get API Statistics",
    description="Get usage statistics for the API"
)
async def get_api_stats():
    """Get API usage statistics."""
    try:
        # Get basic stats from database
        records = get_all_insights_records(limit=1000)  # Get recent records for stats
        
        total_requests = len(records)
        successful_requests = sum(1 for r in records if r.get("success", True))
        failed_requests = total_requests - successful_requests
        
        if total_requests > 0:
            success_rate = (successful_requests / total_requests) * 100
            avg_processing_time = sum(
                r.get("processing_time", 0) for r in records if r.get("processing_time")
            ) / total_requests
        else:
            success_rate = 0
            avg_processing_time = 0
        
        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate_percent": round(success_rate, 2),
            "average_processing_time_seconds": round(avg_processing_time, 2),
            "database_enabled": get_insights_record("test") is not None or total_requests > 0
        }
        
    except Exception as e:
        logger.error(f"Error retrieving API stats: {e}")
        return {
            "error": "Failed to retrieve statistics",
            "database_enabled": False
        }
