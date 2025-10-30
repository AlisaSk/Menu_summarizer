"""
HTML analysis utilities for better menu extraction.
Alternative approach: send HTML directly to LLM for better structure understanding.
"""

from bs4 import BeautifulSoup
import re
from typing import Optional, Dict, Any
from datetime import datetime
from app.fetch.utils import CZ_WEEKDAYS


def clean_html_for_llm(html: str, max_length: int = 8000) -> str:
    """
    Clean and prepare HTML for LLM processing.
    Keep structure but remove unnecessary elements.
    """
    soup = BeautifulSoup(html, "html.parser")
    
    # Remove scripts, styles, and navigation elements
    for element in soup(["script", "style", "nav", "header", "footer", "aside", "noscript"]):
        element.decompose()
    
    # Remove common non-content elements
    for selector in [
        '[class*="cookie" i]', '[id*="cookie" i]',
        '[class*="gdpr" i]', '[id*="gdpr" i]',
        '[class*="advertisement" i]', '[id*="advertisement" i]',
        '[class*="banner" i]', '[id*="banner" i]',
        '.social', '.share', '.newsletter'
    ]:
        for element in soup.select(selector):
            element.decompose()
    
    # Focus on likely menu content areas
    menu_selectors = [
        '[class*="menu" i]', '[id*="menu" i]',
        '[class*="jidlo" i]', '[id*="jidlo" i]',
        '[class*="denni" i]', '[id*="denni" i]',
        '[class*="poledni" i]', '[id*="poledni" i]',
        'main', 'article', '.content', '#content'
    ]
    
    menu_containers = []
    for selector in menu_selectors:
        try:
            containers = soup.select(selector)
            menu_containers.extend(containers)
        except Exception:
            continue
    
    if menu_containers:
        # If we found menu-specific containers, use only those
        clean_soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        body = clean_soup.find("body")
        
        for container in menu_containers[:3]:  # Limit to first 3 containers
            body.append(container.extract())
        
        html_content = str(clean_soup)
    else:
        # Fallback to cleaned full HTML
        html_content = str(soup)
    
    # Truncate if too long
    if len(html_content) > max_length:
        html_content = html_content[:max_length] + "..."
    
    return html_content


def clean_body_text_for_llm(html: str, max_length: int = 8000) -> str:
    """
    Extract only the inner contents of <body>, remove non-content tags, and
    return a compact text suitable for LLM input.

    Steps:
    - Take only body inner content (fallback to full document if body absent)
    - Remove script/style/nav/header/footer/aside/noscript and other noise tags
    - Drop common cookie/GDPR/ads/banner elements by class/id heuristics
    - Convert remaining content to text with sensible newlines
    - Truncate to max_length to keep prompt small enough
    """
    soup = BeautifulSoup(html, "html.parser")

    body = soup.body if soup.body else soup

    # Tags to remove completely
    drop_tags = [
        "script", "style", "nav", "header", "footer", "aside", "noscript",
        "svg", "canvas", "iframe", "link", "meta", "form", "picture",
        "source", "video", "audio", "button", "input", "select", "textarea",
        "dialog",
    ]
    for el in body.find_all(drop_tags):
        el.decompose()

    # Heuristics for cookie/GDPR/ads/social/newsletter/banners
    noise_selectors = [
        '[class*="cookie" i]', '[id*="cookie" i]',
        '[class*="consent" i]', '[id*="consent" i]',
        '[class*="gdpr" i]', '[id*="gdpr" i]',
        '[class*="advert" i]', '[id*="advert" i]',
        '[class*="banner" i]', '[id*="banner" i]',
        '.social', '.share', '.newsletter', '.breadcrumbs', '.breadcrumb'
    ]
    for sel in noise_selectors:
        for el in body.select(sel):
            el.decompose()

    # Convert to text, preserving some structure with newlines
    text = body.get_text("\n", strip=True)

    # Normalize whitespace and collapse excessive empty lines
    import re
    # Replace 3+ newlines with 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Trim overly long whitespace sequences
    text = re.sub(r"[ \t]{2,}", " ", text)

    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length] + "..."

    return text


def extract_date_info_from_html(html: str) -> Dict[str, Any]:
    """
    Extract date-related information from HTML structure.
    Look for date patterns in text, attributes, and meta tags.
    """
    soup = BeautifulSoup(html, "html.parser")
    date_info = {
        "found_dates": [],
        "found_weekdays": [],
        "menu_type_indicators": []
    }
    
    # Look for date patterns in text
    date_patterns = [
        r'\d{1,2}\.\d{1,2}\.\d{4}',  # DD.MM.YYYY
        r'\d{1,2}\.\d{1,2}\.?',      # DD.MM.
        r'\d{4}-\d{2}-\d{2}',        # YYYY-MM-DD
        r'\d{1,2}/\d{1,2}/\d{4}',    # DD/MM/YYYY
    ]
    
    all_text = soup.get_text()
    for pattern in date_patterns:
        matches = re.findall(pattern, all_text)
        date_info["found_dates"].extend(matches)
    
    # Look for Czech weekdays
    text_lower = all_text.lower()
    for weekday in CZ_WEEKDAYS:
        if weekday in text_lower:
            date_info["found_weekdays"].append(weekday)
    
    # Look for menu type indicators
    menu_indicators = [
        "denní menu", "daily menu", "menu dne", "dnes",
        "polední menu", "lunch menu", "týdenní menu",
        "jídelní lístek", "menu na"
    ]
    
    for indicator in menu_indicators:
        if indicator.lower() in text_lower:
            date_info["menu_type_indicators"].append(indicator)
    
    # Look for time-related meta tags or structured data
    meta_tags = soup.find_all("meta")
    for meta in meta_tags:
        content = meta.get("content", "")
        if any(word in content.lower() for word in ["date", "updated", "modified"]):
            date_info["meta_dates"] = date_info.get("meta_dates", [])
            date_info["meta_dates"].append(content)
    
    # Look for datetime attributes in time tags
    time_tags = soup.find_all("time")
    for time_tag in time_tags:
        datetime_attr = time_tag.get("datetime", "")
        if datetime_attr:
            # Extract date from datetime attribute
            for pattern in date_patterns:
                matches = re.findall(pattern, datetime_attr)
                date_info["found_dates"].extend(matches)
    
    return date_info


def get_menu_focused_html(html: str) -> str:
    """
    Extract HTML focused specifically on menu content.
    This is an alternative to text extraction for LLM processing.
    """
    soup = BeautifulSoup(html, "html.parser")
    
    # Priority selectors for menu content
    menu_selectors = [
        # High priority - specific menu terms
        '[class*="menu" i]', '[id*="menu" i]',
        '[class*="jidelni" i]', '[id*="jidelni" i]',
        '[class*="denni" i]', '[id*="denni" i]',
        '[class*="poledni" i]', '[id*="poledni" i]',
        '[class*="daily" i]', '[id*="daily" i]',
        
        # Medium priority - content areas
        'main', 'article', 'section[class*="content" i]',
        '.content', '#content', '.main-content',
        
        # Lower priority - general containers
        '.container', '.wrapper'
    ]
    
    menu_html_parts = []
    
    for selector in menu_selectors:
        elements = soup.select(selector)
        for element in elements:
            # Check if element has substantial content
            text = element.get_text(strip=True)
            if len(text) > 50:  # Minimum content threshold
                # Clean the element
                for unwanted in element.select("script, style, nav, footer"):
                    unwanted.decompose()
                
                menu_html_parts.append(str(element))
        
        # If we found good menu content, stop looking
        if menu_html_parts and sum(len(part) for part in menu_html_parts) > 500:
            break
    
    if not menu_html_parts:
        # Fallback: return cleaned version of full page
        for unwanted in soup.select("script, style, nav, header, footer, aside"):
            unwanted.decompose()
        return str(soup)
    
    # Combine found menu parts into clean HTML structure
    result_html = f"""
    <html>
    <body>
    {''.join(menu_html_parts)}
    </body>
    </html>
    """
    
    return result_html


def should_use_html_mode(html: str) -> bool:
    """
    Determine if we should send HTML directly to LLM or use text extraction.
    
    HTML mode is better when:
    - Page has complex structure (tables, lists)
    - Menu items are in structured format
    - Text extraction loses important formatting
    """
    soup = BeautifulSoup(html, "html.parser")
    
    # Check for structured content indicators
    has_tables = len(soup.find_all("table")) > 0
    has_lists = len(soup.find_all(["ul", "ol"])) > 1
    has_menu_structure = len(soup.select('[class*="menu" i], [id*="menu" i]')) > 0
    
    # Check for price indicators in structured format
    price_in_structure = False
    for element in soup.select("td, li, .price, [class*='price' i]"):
        text = element.get_text()
        if re.search(r'\d+[.,]?-?\s*(?:kč|czk|,-)', text.lower()):
            price_in_structure = True
            break
    
    # Prefer HTML mode if we have structured content
    return has_tables or has_lists or has_menu_structure or price_in_structure
