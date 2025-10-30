from fastapi import APIRouter, HTTPException, status
from app.schemas import SummarizeRequest, SummarizeResponse
from app.services.summarize import process_menu_request, get_cache_stats
from app.fetch.scraper import fetch_html_with_js_fallback, extract_menu_text

router = APIRouter()

@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_menu(request: SummarizeRequest):
    """
    Summarize restaurant menu from URL.
    
    Accepts a URL and returns structured menu data for today.
    Results are cached per URL + date.
    """
    if not request.url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL is required"
        )
    
    if not request.url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL must start with http:// or https://"
        )
    
    try:
        result = await process_menu_request(request.url)
        return SummarizeResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/debug-scrape")
async def debug_scrape(request: SummarizeRequest):
    """Debug endpoint to see what text is extracted from URL"""
    try:
        html = await fetch_html_with_js_fallback(request.url)
        extracted_text = extract_menu_text(html)
        
        # Also test HTML analysis
        from app.fetch.html_analyzer import (
            should_use_html_mode, 
            extract_date_info_from_html,
            clean_html_for_llm,
            clean_body_text_for_llm
        )
        
        use_html = should_use_html_mode(html)
        date_info = extract_date_info_from_html(html)
        cleaned_body = clean_body_text_for_llm(html)
        
        # Check for SPA markers
        spa_markers = {
            "has_next_js": 'id="__next"' in html or '__NEXT_DATA__' in html,
            "has_react": 'data-reactroot' in html.lower(),
            "has_nuxt": 'window.__NUXT__' in html,
            "has_angular": 'ng-version' in html
        }
        
        result = {
            "url": request.url,
            "html_length": len(html),
            "extracted_text_length": len(extracted_text),
            "cleaned_body_length": len(cleaned_body),
            "should_use_html_mode": use_html,
            "spa_markers": spa_markers,
            "date_analysis": date_info,
            "extracted_text_preview": extracted_text[:1000] + "..." if len(extracted_text) > 1000 else extracted_text,
            "cleaned_body_preview": cleaned_body[:1500] + "..." if len(cleaned_body) > 1500 else cleaned_body
        }
        
        if use_html:
            cleaned_html = clean_html_for_llm(html)
            result["cleaned_html_length"] = len(cleaned_html)
            result["cleaned_html_preview"] = cleaned_html[:1000] + "..." if len(cleaned_html) > 1000 else cleaned_html
            
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/debug-js-render")
async def debug_js_render(request: SummarizeRequest):
    """Force JS rendering and show the difference"""
    try:
        from app.fetch.scraper import fetch_html
        from app.fetch.js_scraper import fetch_js_html
        from app.fetch.html_analyzer import clean_body_text_for_llm
        
        # Get static HTML
        static_html = await fetch_html(request.url)
        static_cleaned = clean_body_text_for_llm(static_html)
        
        # Get JS-rendered HTML
        js_html = await fetch_js_html(request.url)
        js_cleaned = clean_body_text_for_llm(js_html)
        
        # Check for SPA markers
        spa_markers_static = {
            "has_next_js": 'id="__next"' in static_html or '__NEXT_DATA__' in static_html,
            "has_react": 'data-reactroot' in static_html.lower(),
            "has_nuxt": 'window.__NUXT__' in static_html,
            "has_angular": 'ng-version' in static_html
        }
        
        return {
            "url": request.url,
            "static": {
                "html_length": len(static_html),
                "cleaned_length": len(static_cleaned),
                "spa_markers": spa_markers_static,
                "preview": static_cleaned[:1500] + "..." if len(static_cleaned) > 1500 else static_cleaned
            },
            "js_rendered": {
                "html_length": len(js_html),
                "cleaned_length": len(js_cleaned),
                "preview": js_cleaned[:1500] + "..." if len(js_cleaned) > 1500 else js_cleaned
            },
            "improvement": {
                "html_size_increase": len(js_html) - len(static_html),
                "text_size_increase": len(js_cleaned) - len(static_cleaned),
                "js_rendering_helped": len(js_cleaned) > len(static_cleaned) * 1.5
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/cache/stats")
async def cache_statistics():
    """Get cache statistics for debugging"""
    return get_cache_stats()

@router.delete("/cache/clear")
async def clear_cache():
    """Clear all cache entries"""
    try:
        from app.cache.db import clear_all
        clear_all()
        return {"message": "Cache cleared successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Restaurant Menu Summarizer"}
