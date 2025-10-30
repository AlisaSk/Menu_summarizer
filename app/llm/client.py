import json
from typing import Dict, Any, Optional
from app.core.config import settings
from app.fetch.utils import normalize_price_human, convert_weight_to_string, extract_allergens

class MenuParsingTools:
    """Function tools for LLM to help parse menu data"""
    
    @staticmethod
    def normalize_price(price_text: str) -> Optional[int]:
        """Normalize price text like '145,-' to integer 145"""
        return normalize_price_human(price_text)
    
    @staticmethod
    def detect_weekday(text: str) -> str:
        """Detect Czech weekday from menu text"""
        from app.fetch.utils import detect_weekday_from_text
        return detect_weekday_from_text(text)
    
    @staticmethod
    def convert_weight(weight_text: str) -> Optional[str]:
        """Convert weight/volume to standard format"""
        return convert_weight_to_string(weight_text)
    
    @staticmethod
    def extract_allergen_codes(text: str) -> list[str]:
        """Extract allergen codes from text"""
        return extract_allergens(text)

def get_gemini_model():
    """Get configured Gemini model"""
    if not settings.GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not set")

    try:
        import google.generativeai as genai  # lazy import to allow tests without package
    except Exception as e:
        raise ImportError("google-generativeai package is required to use Gemini client") from e

    genai.configure(api_key=settings.GOOGLE_API_KEY)
    return genai.GenerativeModel('gemini-2.5-flash')

async def summarize_menu(
    raw_text: str,
    today_iso: str,
    weekday_cs: str,
    source_url: str,
    html_content: str = None
) -> Dict[str, Any]:
    """
    Use Gemini to parse raw menu text or HTML into structured JSON.
    Can work with either text extraction or direct HTML for better structure understanding.
    """
    if settings.USE_MOCK:
        return await _mock_summarize_menu(raw_text, today_iso, weekday_cs, source_url)
    
    model = get_gemini_model()

    # Decide content mode
    use_html = html_content is not None and len(str(html_content).strip()) > 0
    original_content = html_content if use_html else raw_text
    content_type = "HTML structure" if use_html else "extracted text"

    def build_prompt(body: str) -> str:
        return (
            f"You are a Czech restaurant menu parser. Parse the given menu {content_type} into structured JSON.\n\n"
            f"Today's date: {today_iso}\n"
            f"Day of week: {weekday_cs}\n"
            f"Source URL: {source_url}\n\n"
            "IMPORTANT: Return ONLY valid JSON without any additional text or markdown formatting.\n\n"
            "Required JSON format:\n"
            "{\n"
            "  \"restaurant_name\": \"Name of restaurant or 'Unknown Restaurant' if not found\",\n"
            f"  \"date\": \"{today_iso}\",\n"
            "  \"day_of_week\": \"pondělí|úterý|středa|čtvrtek|pátek|sobota|neděle\",\n"
            "  \"menu_items\": [\n"
            "    {\n"
            "      \"category\": \"polévka|hlavní chod|salát|dezert|nápoj|příloha\",\n"
            "      \"name\": \"Dish name\",\n"
            "      \"price\": 145,\n"
            "      \"allergens\": [\"1\", \"3\", \"9\"],\n"
            "      \"weight\": \"150g\"\n"
            "    }\n"
            "  ],\n"
            "  \"daily_menu\": true,\n"
            f"  \"source_url\": \"{source_url}\"\n"
            "}\n\n"
            f"Rules for {content_type} parsing:\n"
            "1. Extract restaurant name from the content (look for headings, titles, business names)\n"
            f"2. Determine if this is TODAY'S specific daily menu for {weekday_cs} ({today_iso}):\n"
            f"   - Set daily_menu=true if menu explicitly shows today's date or weekday\n"
            f"   - Set daily_menu=false if menu shows different dates/weekdays, or is a general/permanent menu\n"
            "   - Extract day_of_week from menu content if explicitly mentioned\n"
            "3. Categorize each menu item appropriately:\n"
            "   - \"polévka\" for soups\n"
            "   - \"hlavní chod\" for main dishes, meat, pasta, rice dishes\n"
            "   - \"salát\" for salads\n"
            "   - \"dezert\" for desserts, sweets\n"
            "   - \"nápoj\" for drinks, beverages\n"
            "   - \"příloha\" for side dishes, bread, garnish\n"
            "4. For prices: convert \"145,-\", \"120 Kč\", \"95.50\", \"€15\" etc. to integer CZK (145, 120, 95, 375)\n"
            "5. Parse allergen codes from patterns like \"(1,3,9)\" or \"alergeny: 1,3,9\" as string array\n"
            "6. Include weight/portion info if available, standardize units (kg→g, l→ml)\n"
            "7. If multiple dates found in menu, extract the one that matches items and set daily_menu accordingly\n"
            "8. If no menu items found, return empty array for menu_items\n"
            "9. ALWAYS include all required fields, use sensible defaults if information not available\n\n"
            f"{'HTML structure analysis:' if use_html else 'Text content analysis:'}\n"
            f"- {'Look for table structures, list items, and div containers for menu items' if use_html else 'Extract information from the processed text content'}\n"
            f"- {'Pay attention to HTML classes/IDs that might indicate menu sections' if use_html else 'Look for price patterns and section headers in text'}\n"
            f"- {'Tables often contain structured menu data with prices in separate columns' if use_html else 'Sequential text often groups items by category'}\n"
            f"- LOOK for date/weekday indicators to determine if this is today's menu or a different day\n\n"
            f"Parse this menu {content_type}:\n\n"
            f"{body}"
        )

    def shrink_text(text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[:limit] + "..."

    # Progressive shrinking limits for retries
    limits = [6000, 4000, 2000]
    max_attempts = min(settings.LLM_MAX_ATTEMPTS, len(limits)) if settings.LLM_MAX_ATTEMPTS else 3

    last_error: Optional[Exception] = None
    for attempt in range(max_attempts):
        limit = limits[attempt]
        body = shrink_text(original_content, limit)
        prompt = build_prompt(body)

        try:
            print(f"LLM ATTEMPT {attempt+1}/{max_attempts}: content_len={len(body)}, timeout={settings.LLM_TIMEOUT_SECONDS}s")
            response = model.generate_content(prompt)

            if not response.text:
                raise ValueError("Empty response from Gemini")

            # Clean the response text - remove any markdown formatting
            content = response.text.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()

            # Try to parse JSON
            try:
                parsed_data = json.loads(content)

                # Post-process prices to ensure they're integers
                for item in parsed_data.get('menu_items', []):
                    if 'price' in item and item['price'] is not None:
                        if isinstance(item['price'], str):
                            item['price'] = MenuParsingTools.normalize_price(item['price'])

                # Post-process day_of_week: if daily_menu=false, set to today's weekday
                is_daily_menu = parsed_data.get('daily_menu', True)
                if not is_daily_menu:
                    # Import here to get fresh current weekday
                    from app.fetch.utils import get_current_weekday_czech
                    current_weekday = get_current_weekday_czech()
                    print(f"Setting day_of_week to today ({current_weekday}) because daily_menu=false")
                    parsed_data['day_of_week'] = current_weekday
                
                return parsed_data

            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    raise ValueError(f"No valid JSON found in Gemini response: {content[:200]}...")

        except Exception as e:
            last_error = e
            # Retry on timeouts or transient errors
            msg = str(e).lower()
            is_timeout = "timeout" in msg or "504" in msg or "deadline" in msg
            if attempt < max_attempts - 1 and is_timeout:
                import time
                backoff = 0.7 * (attempt + 1)
                print(f"LLM TIMEOUT/TRANSIENT ERROR, retrying in {backoff:.1f}s... ({e})")
                time.sleep(backoff)
                continue
            break

    raise Exception(f"Gemini parsing failed: {str(last_error) if last_error else 'Unknown error'}")

async def _mock_summarize_menu(
    raw_text: str, 
    today_iso: str, 
    weekday_cs: str, 
    source_url: str
) -> Dict[str, Any]:
    """Mock implementation for testing without LLM API"""
    
    # Extract potential restaurant name (first meaningful line)
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    restaurant_name = lines[0] if lines else "Mock Restaurant"
    
    # Create mock menu items based on common Czech menu patterns
    mock_items = [
        {
            "category": "polévka",
            "name": "Hovězí vývar s nudlemi",
            "price": 45,
            "allergens": ["1", "3", "9"],
            "weight": "300ml"
        },
        {
            "category": "hlavní chod",
            "name": "Smažený řízek s bramborami",
            "price": 185,
            "allergens": ["1", "3"],
            "weight": "200g"
        }
    ]
    
    return {
        "restaurant_name": restaurant_name,
        "date": today_iso,
        "day_of_week": weekday_cs,
        "menu_items": mock_items,
        "daily_menu": True,
        "source_url": source_url
    }
