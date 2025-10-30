import json
from typing import Dict, Any
from app.fetch import scraper
from app.fetch.html_analyzer import (
    should_use_html_mode, 
    get_menu_focused_html, 
    extract_date_info_from_html,
    clean_html_for_llm,
    clean_body_text_for_llm
)
from app.fetch.utils import today_prague_str, detect_weekday_from_text
from app.cache import db as cache_db
from app.llm import client as llm_client
from app.schemas import MenuData

async def process_menu_request(url: str) -> Dict[str, Any]:
    """
    Main pipeline for processing menu summarization request.
    
    1. Calculate today's date (Europe/Prague timezone)
    2. Purge old cache entries
    3. Check cache for existing data
    4. If not cached: fetch -> extract -> LLM -> validate -> cache
    5. Return structured response
    """
    
    # Get today's date in Prague timezone
    today = today_prague_str()
    
    # Clean up old cache entries
    cache_db.purge_old(today)
    
    
    # Check cache first
    cached_payload = cache_db.get(url, today)
    if cached_payload:
        try:
            cached_data = json.loads(cached_payload)
            print(f"CACHE HIT for {url} on {today}")
            return {"cached": True, "data": cached_data}
        except json.JSONDecodeError:
            print(f"CACHE CORRUPTED for {url}, proceeding with fresh fetch")
            pass
    
    # Fresh processing pipeline
    try:
        print(f"PROCESSING {url} - fetching HTML...")
        
        # Step 1: Fetch HTML content
        html = await scraper.fetch_html_with_js_fallback(url)
        if not html:
            raise Exception("No content received from URL")
        
        print(f"HTML RECEIVED: {len(html)} characters")
        
        # Step 2: Extract text for fallback
        menu_text = scraper.extract_menu_text(html)
        print(f"EXTRACTED TEXT: {len(menu_text)} characters")
        print(f"TEXT PREVIEW: {menu_text[:500]}...")
        
        # Step 3: Detect weekday
        weekday = detect_weekday_from_text(menu_text)
        print(f"DETECTED WEEKDAY: {weekday}")
        
        # Prepare cleaned body text for LLM (body-only, tags removed)
        cleaned_body_text = clean_body_text_for_llm(html)

        # Log cleaned text with clear boundaries to separate from other logs
        print("\n===== CLEANED BODY TEXT BEGIN =====")
        # Print a preview if very long to avoid flooding logs
        if len(cleaned_body_text) > 4000:
            print(cleaned_body_text[:4000] + "... [truncated]")
        else:
            print(cleaned_body_text)
        print("===== CLEANED BODY TEXT END =====\n")

        # Step 4: Smart LLM processing - avoid timeouts with large HTML
        html_size_kb = len(html) / 1024
        
        if html_size_kb > 200:  # Very large HTML - use text only
            print(f"VERY LARGE HTML ({html_size_kb:.1f}KB) - using text mode only")
            structured_data = await llm_client.summarize_menu(
                raw_text=cleaned_body_text or menu_text,
                today_iso=today,
                weekday_cs=weekday,
                source_url=url,
                html_content=None
            )
        else:
            # Previously we used raw HTML; now we send the cleaned body text instead
            print(f"SENDING TO LLM - cleaned text from HTML (size {html_size_kb:.1f}KB)")
            structured_data = await llm_client.summarize_menu(
                raw_text=cleaned_body_text or menu_text,
                today_iso=today,
                weekday_cs=weekday,
                source_url=url,
                html_content=None  # send text, not raw HTML
            )
        
        print(f"LLM RESPONSE: {structured_data}")
        
        # Step 5: Validate the response using Pydantic
        menu_data = MenuData(**structured_data)
        validated_data = menu_data.model_dump()
        
        print(f"VALIDATED DATA: {validated_data}")
        
        # Step 6: Cache the result
        cache_payload = json.dumps(validated_data, ensure_ascii=False)
        cache_db.set(url, today, cache_payload)
        
        print(f"CACHED RESULT for {url}")
        
        return {"cached": False, "data": validated_data}
        
    except Exception as e:
        print(f"ERROR processing {url}: {str(e)}")
        raise Exception(f"Menu processing failed: {str(e)}")

def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics for debugging"""
    try:
        return cache_db.get_stats()
    except Exception as e:
        return {"error": str(e)}
