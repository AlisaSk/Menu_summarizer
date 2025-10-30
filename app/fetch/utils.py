import re
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional

CZ_TZ = ZoneInfo("Europe/Prague")
CZ_WEEKDAYS = ["pondělí", "úterý", "středa", "čtvrtek", "pátek", "sobota", "neděle"]

def today_prague_str() -> str:
    """Get today's date in Prague timezone as ISO string"""
    return datetime.now(CZ_TZ).date().isoformat()

def get_current_weekday_czech() -> str:
    """Get current weekday in Czech"""
    idx = datetime.now(CZ_TZ).weekday()  # 0=Monday, 1=Tuesday, etc.
    return CZ_WEEKDAYS[idx]

def detect_weekday_from_text(text: str) -> str:
    """
    Detect Czech weekday from menu text.
    If found, return it. Otherwise return current weekday.
    """
    if not text:
        return get_current_weekday_czech()
    
    text_lower = text.lower()
    for weekday in CZ_WEEKDAYS:
        if weekday in text_lower:
            return weekday
    
    # Also check for common abbreviations
    abbrevs = {
        "po": "pondělí", "út": "úterý", "st": "středa", 
        "čt": "čtvrtek", "pá": "pátek", "so": "sobota", "ne": "neděle"
    }
    
    for abbrev, full_name in abbrevs.items():
        if abbrev in text_lower:
            return full_name
    
    return get_current_weekday_czech()

def normalize_price_human(price_text: str) -> Optional[int]:
    """
    Normalize price text to integer CZK.
    Examples: '145,-' -> 145, '145 Kč' -> 145, '95.50' -> 95
    """
    if not price_text:
        return None
        
    # Remove spaces and common currency indicators
    cleaned = re.sub(r'[^\d,.-]', '', str(price_text))
    
    # Handle Czech format: 145,- or 145,-
    if ',-' in cleaned:
        cleaned = cleaned.replace(',-', '')
    
    # Extract first number sequence
    match = re.search(r'(\d+)(?:[,.-]\d*)?', cleaned)
    if match:
        return int(match.group(1))
    
    return None

def convert_weight_to_string(text: str) -> Optional[str]:
    """
    Convert weight/volume information to standardized string format.
    Examples: '0,5 kg' -> '500g', '0.33 l' -> '330ml', '150g' -> '150g'
    """
    if not text:
        return None
    
    text_clean = text.lower().replace(',', '.')
    
    # Check for kg -> g conversion
    kg_match = re.search(r'([\d.]+)\s*kg', text_clean)
    if kg_match:
        kg_value = float(kg_match.group(1))
        return f"{int(kg_value * 1000)}g"
    
    # Check for liters -> ml conversion  
    l_match = re.search(r'([\d.]+)\s*l(?:itr)?', text_clean)
    if l_match:
        l_value = float(l_match.group(1))
        return f"{int(l_value * 1000)}ml"
    
    # Check for direct g/ml
    g_match = re.search(r'(\d+)\s*g', text_clean)
    if g_match:
        return f"{g_match.group(1)}g"
        
    ml_match = re.search(r'(\d+)\s*ml', text_clean)
    if ml_match:
        return f"{ml_match.group(1)}ml"
    
    # Check for portions/pieces
    portion_match = re.search(r'(\d+)\s*(ks|kus|porce|portion)', text_clean)
    if portion_match:
        return f"{portion_match.group(1)} {portion_match.group(2)}"
    
    return None

def extract_allergens(text: str) -> list[str]:
    """
    Extract allergen codes from text.
    Look for patterns like: (1,3,9) or [1,3,9] or "alergeny: 1,3,9"
    """
    if not text:
        return []
    
    allergens = []
    
    # Pattern for parentheses or brackets: (1,3,9) or [1,3,9]
    bracket_pattern = r'[\(\[]([0-9,\s]+)[\)\]]'
    matches = re.findall(bracket_pattern, text)
    
    for match in matches:
        # Split by comma and clean up
        nums = [num.strip() for num in match.split(',') if num.strip().isdigit()]
        allergens.extend(nums)
    
    # Pattern for "alergeny:" or "allergens:" followed by numbers
    # Updated to handle accented characters better
    allergen_pattern = r'(?:alerg[eěé]ny?[:]?|allergens?[:]?)[\s]*([0-9,\s]+)'
    matches = re.findall(allergen_pattern, text.lower())
    
    for match in matches:
        nums = [num.strip() for num in match.split(',') if num.strip().isdigit()]
        allergens.extend(nums)
    
    # Remove duplicates and sort
    unique_allergens = sorted(list(set(allergens)))
    return unique_allergens
