import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
from typing import Optional
from app.core.config import settings

async def fetch_js_html(url: str, wait_for_content: bool = True) -> str:
    """
    Fetch HTML from a URL using Playwright to handle JavaScript.
    
    Args:
        url: The URL to fetch
        wait_for_content: Whether to wait for dynamic content to load
    
    Returns:
        Raw HTML string after JavaScript execution
    """
    try:
        async with async_playwright() as p:
            # Launch browser (headless configurable)
            browser = await p.chromium.launch(
                headless=settings.PLAYWRIGHT_HEADLESS,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            # Create a new page
            page = await browser.new_page()
            
            # Set user agent
            await page.set_extra_http_headers({"User-Agent": settings.USER_AGENT})
            
            # Navigate to the URL with timeout (first ensure DOM content loaded)
            await page.goto(url, timeout=settings.REQUEST_TIMEOUT * 1000, wait_until="domcontentloaded")
            # Some SPAs need an extra idle stabilization
            try:
                await page.wait_for_load_state("networkidle", timeout=settings.REQUEST_TIMEOUT * 1000)
            except PlaywrightTimeout:
                pass

            # Try dismissing common cookie banners to unblock content
            cookie_selectors = [
                'button:has-text("Accept")',
                'button:has-text("I Agree")',
                'button:has-text("Souhlasím")',
                'button:has-text("Přijmout")',
                '[id*="cookie" i] button',
                '[class*="cookie" i] button'
            ]
            for sel in cookie_selectors:
                try:
                    btn = page.locator(sel).first
                    if await btn.count() > 0:
                        await btn.click(timeout=1500)
                        break
                except Exception:
                    continue
            
            # Wait for content to load if requested
            if wait_for_content:
                # Try multiple relevant selectors progressively
                selectors = [
                    '[class*="menu" i], [id*="menu" i]',
                    'main [class*="menu" i]',
                    '#__next',
                    'script#__NEXT_DATA__',
                    'main',
                    'article',
                    'section'
                ]
                waited = False
                for sel in selectors:
                    try:
                        await page.wait_for_selector(sel, timeout=min(4000, settings.JS_WAIT_TIMEOUT_MS))
                        waited = True
                        break
                    except PlaywrightTimeout:
                        continue

                # Trigger lazy loads by scrolling
                for _ in range(3):
                    try:
                        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                        await page.wait_for_timeout(700)
                    except Exception:
                        break

                # Extra small wait for hydration
                await page.wait_for_timeout(min(3000, settings.JS_EXTRA_WAIT_MS))
            
            # Get the rendered HTML
            html = await page.content()
            
            await browser.close()
            return html
            
    except PlaywrightTimeout:
        raise Exception(f"Timeout while fetching {url}")
    except Exception as e:
        raise Exception(f"Failed to fetch {url} with JavaScript: {str(e)}")

def extract_menu_text_js(html: str) -> str:
    """
    Extract menu text from JavaScript-rendered HTML.
    Enhanced version with better menu detection.
    """
    soup = BeautifulSoup(html, "html.parser")
    
    # Remove script and style elements
    for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
        script.decompose()
    
    menu_text = []
    
    # Enhanced menu-specific selectors in order of priority
    menu_selectors = [
        # Direct menu selectors
        '[class*="menu" i]', '[id*="menu" i]',
        '[class*="food" i]', '[id*="food" i]',
        '[class*="dish" i]', '[id*="dish" i]',
        '[class*="item" i]', '[id*="item" i]',
        '[class*="product" i]', '[id*="product" i]',
        
        # Czech menu terms
        '[class*="jidlo" i]', '[id*="jidlo" i]', 
        '[class*="jidelni" i]', '[id*="jidelni" i]',
        '[class*="listek" i]', '[id*="listek" i]',
        '[class*="dnes" i]', '[id*="dnes" i]',
        '[class*="denni" i]', '[id*="denni" i]',
        '[class*="poledni" i]', '[id*="poledni" i]',
        
        # English menu terms  
        '[class*="daily" i]', '[id*="daily" i]',
        '[class*="lunch" i]', '[id*="lunch" i]',
        '[class*="restaurant" i]', '[id*="restaurant" i]',
        
        # Restaurant-specific selectors
        '[class*="roll" i]', '[id*="roll" i]',  # For sushi
        '[class*="sushi" i]', '[id*="sushi" i]',
        '[class*="pizza" i]', '[id*="pizza" i]',
        '[class*="pasta" i]', '[id*="pasta" i]',
        
        # Common content containers
        '.content', '.main', '.main-content', 
        '#content', '#main', '#main-content',
        '.container', '.wrapper', '.page-content',
        'article', 'section', 'main'
    ]
    
    # Try to find menu-specific elements first
    found_menu_content = False
    for selector in menu_selectors:
        try:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(" ", strip=True)
                if text and len(text) > 20:  # Meaningful content threshold
                    menu_text.append(text)
                    found_menu_content = True
        except Exception:
            continue
        
        # If we found good menu content, prioritize it
        if found_menu_content and len(" ".join(menu_text)) > 200:
            break
    
    # If no menu-specific content found, use comprehensive extraction
    if not menu_text or len(" ".join(menu_text)) < 100:
        # Look for price indicators which suggest menu content
        price_patterns = ['kč', 'czk', ',-', '$', '€', 'price']
        
        for tag in soup.find_all(["div", "section", "article", "ul", "ol", "table"]):
            text = tag.get_text(" ", strip=True)
            if (text and 
                len(text) > 30 and 
                len(text) < 1000 and  # Not too long
                any(pattern in text.lower() for pattern in price_patterns)):
                menu_text.append(text)
        
        # If still no good content, get all meaningful text
        if not menu_text:
            for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "span", "div"]):
                text = tag.get_text(" ", strip=True)
                if (text and 
                    len(text) > 15 and 
                    len(text) < 500 and
                    not text.lower().startswith(('cookie', 'gdpr', 'consent', 'terms', 'privacy')) and
                    any(char.isalpha() for char in text)):
                    menu_text.append(text)
    
    # Join and clean the text
    full_text = "\n".join(menu_text)
    
    # Additional text cleaning
    import re
    # Remove excessive whitespace
    full_text = re.sub(r'\s+', ' ', full_text)
    # Remove repeated phrases (common in navigation)
    lines = full_text.split('\n')
    unique_lines = []
    seen = set()
    for line in lines:
        line = line.strip()
        if line and line not in seen and len(line) > 5:
            unique_lines.append(line)
            seen.add(line)
    
    return "\n".join(unique_lines)
