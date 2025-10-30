import httpx
import asyncio
from bs4 import BeautifulSoup
from typing import Optional
from app.core.config import settings

async def fetch_html(url: str) -> str:
    """Fetch raw HTML from a URL with proper error handling."""
    try:
        headers = {
            "User-Agent": settings.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "cs,en-US;q=0.7,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        async with httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT,
            headers=headers,
            follow_redirects=True
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.TimeoutException:
        raise Exception(f"Timeout while fetching {url}")
    except httpx.HTTPStatusError as e:
        raise Exception(f"HTTP error {e.response.status_code} for {url}")
    except Exception as e:
        raise Exception(f"Failed to fetch {url}: {str(e)}")

async def fetch_html_with_js_fallback(url: str) -> str:
    """
    Fetch HTML with JavaScript fallback if static content is insufficient.
    """
    # Mock mode for testing
    if settings.USE_MOCK:
        return await _mock_fetch_html(url)
    
    try:
        # First try static HTTP request
        html = await fetch_html(url)
        
        # Quick check if we got meaningful content
        extracted = extract_menu_text(html)

        # Heuristics for SPA/JS-heavy pages
        spa_markers = (
            'id="__next"' in html.lower() or
            'id="__next"' in html or
            '__NEXT_DATA__' in html or
            'data-reactroot' in html or
            'window.__NUXT__' in html or
            'ng-version' in html
        )

        # If we got very little content or page looks like SPA, try JavaScript rendering
        if len(extracted.strip()) < 150 or spa_markers:
            try:
                from app.fetch.js_scraper import fetch_js_html
                reason = f"{len(extracted)} chars" + (" + SPA markers" if spa_markers else "")
                print(f"Static content insufficient ({reason}), trying JavaScript rendering...")
                html = await fetch_js_html(url)
            except ImportError:
                print("Playwright not available, using static content")
            except Exception as e:
                print(f"JavaScript rendering failed: {e}, using static content")
        
        return html
        
    except Exception as e:
        # If static request fails, try JavaScript as last resort
        try:
            from app.fetch.js_scraper import fetch_js_html
            print(f"Static request failed: {e}, trying JavaScript rendering...")
            return await fetch_js_html(url)
        except ImportError:
            raise Exception(f"Both static and JavaScript fetching failed. Static error: {e}")
        except Exception as js_e:
            raise Exception(f"Both static and JavaScript fetching failed. Static: {e}, JS: {js_e}")

def extract_menu_text(html: str) -> str:
    """Extract visible text from HTML, focusing on menu content."""
    soup = BeautifulSoup(html, "html.parser")
    
    # Remove script and style elements
    for script in soup(["script", "style", "nav", "header", "footer"]):
        script.decompose()
    
    menu_text = []
    
    # Enhanced menu-specific selectors in order of priority
    menu_selectors = [
        # Czech menu terms
        "[id*='menu' i]", "[class*='menu' i]",
        "[id*='jidlo' i]", "[class*='jidlo' i]", 
        "[id*='jidelni' i]", "[class*='jidelni' i]",
        "[id*='listek' i]", "[class*='listek' i]",
        "[id*='dnes' i]", "[class*='dnes' i]",
        "[id*='denni' i]", "[class*='denni' i]",
        "[id*='poledni' i]", "[class*='poledni' i]",
        "[id*='dnesni' i]", "[class*='dnesni' i]",
        
        # English menu terms  
        "[id*='daily' i]", "[class*='daily' i]",
        "[id*='lunch' i]", "[class*='lunch' i]",
        "[id*='food' i]", "[class*='food' i]",
        "[id*='dish' i]", "[class*='dish' i]",
        
        # Common menu container patterns
        ".content", ".main", ".main-content", 
        "#content", "#main", "#main-content",
        ".container", ".wrapper", ".page-content"
    ]
    
    # Try to find menu-specific elements first
    found_menu_content = False
    for selector in menu_selectors:
        elements = soup.select(selector)
        for element in elements:
            text = element.get_text(" ", strip=True)
            if text and len(text) > 30:  # Longer threshold for meaningful content
                menu_text.append(text)
                found_menu_content = True
        
        # If we found good menu content, prioritize it
        if found_menu_content and menu_text:
            break
    
    # If no menu-specific content found, use more comprehensive extraction
    if not menu_text:
        # Get all text content, but prioritize certain tags
        priority_tags = ["main", "article", "section"]
        for tag_name in priority_tags:
            for tag in soup.find_all(tag_name):
                text = tag.get_text(" ", strip=True)
                if text and len(text) > 50:
                    menu_text.append(text)
        
        # Fallback to general content extraction
        if not menu_text:
            for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "span", "div"]):
                text = tag.get_text(" ", strip=True)
                # Filter meaningful text that might contain menu info
                if (text and 
                    len(text) > 15 and 
                    len(text) < 500 and  # Not too long
                    not text.lower().startswith(('cookie', 'gdpr', 'consent', 'terms', 'privacy')) and
                    any(char.isalpha() for char in text)):  # Contains letters
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

def normalize_price(price_text: str) -> Optional[int]:
    """
    Normalize price text to integer CZK.
    Examples: "145,-" -> 145, "120 Kč" -> 120, "95" -> 95
    """
    if not price_text:
        return None
    
    # Remove common currency symbols and separators
    import re
    # Extract numbers, handling Czech format (145,- or 145,50)
    match = re.search(r'(\d+)(?:[,.-]\d*)?', str(price_text))
    if match:
        return int(match.group(1))
    return None

async def _mock_fetch_html(url: str) -> str:
    """Mock HTML fetcher for testing without network requests"""
    
    # Generate different mock content based on URL
    if "hradcany" in url.lower():
        return """
        <html>
        <head><title>Restaurace Hradčany</title></head>
        <body>
            <header>
                <h1>Restaurace Hradčany</h1>
                <nav>Menu | Kontakt | O nás</nav>
            </header>
            <main>
                <section class="daily-menu">
                    <h2>Denní menu - neděle 27.10.2025</h2>
                    <div class="menu-items">
                        <div class="soup">
                            <h3>Polévka</h3>
                            <p>Hovězí vývar s nudlemi a zeleninou (1,3,9) - 45,-</p>
                        </div>
                        <div class="main-dishes">
                            <h3>Hlavní chod</h3>
                            <ul>
                                <li>Smažený řízek s bramborovou kaší (1,3,7) - 185,- / 200g</li>
                                <li>Grilovaný losos s rýží (4,9) - 220,- / 180g</li>
                                <li>Vegetariánské rizoto (7,9) - 165,- / 250g</li>
                            </ul>
                        </div>
                        <div class="desserts">
                            <h3>Dezert</h3>
                            <p>Jablečný štrúdl s vanilkovou omáčkou (1,3,7) - 85,- / 120g</p>
                        </div>
                    </div>
                    <div class="allergens">
                        <p>Alergeny: 1-obiloviny, 3-vejce, 4-ryby, 7-mléko, 9-celer</p>
                    </div>
                </section>
            </main>
            <footer>
                <p>© 2025 Restaurace Hradčany</p>
            </footer>
        </body>
        </html>
        """
    
    elif "vlasta" in url.lower():
        return """
        <html>
        <body>
            <h1>Restaurace Vlasta</h1>
            <div id="poledni-menu">
                <h2>Polední menu</h2>
                <table class="menu-table">
                    <tr>
                        <td>Polévka dne</td>
                        <td>Gulášová polévka</td>
                        <td>42 Kč</td>
                    </tr>
                    <tr>
                        <td>Menu 1</td>
                        <td>Kuřecí steak s bramborami (1,7)</td>
                        <td>175 Kč</td>
                    </tr>
                    <tr>
                        <td>Menu 2</td>
                        <td>Těstoviny s rajčatovou omáčkou (1,3)</td>
                        <td>145 Kč</td>
                    </tr>
                </table>
            </div>
        </body>
        </html>
        """
    
    elif "ujezdu" in url.lower():
        return """
        <html>
        <body>
            <div class="restaurant-header">
                <h1>Restaurant U Jezdu</h1>
            </div>
            <section class="dnesni-nabidka">
                <h2>Dnešní nabídka - středa</h2>
                <div class="menu-category">
                    <h3>Polévky</h3>
                    <p>Bramborová polévka s klobásou 48,-</p>
                </div>
                <div class="menu-category">
                    <h3>Hlavní jídla</h3>
                    <p>Svíčková na smetaně (1,3,7,9) 195,- (150g)</p>
                    <p>Smažené kuřecí řízky (1,3) 180,- (180g)</p>
                    <p>Grilovaná zelenina (7) 155,- (200g)</p>
                </div>
                <div class="menu-category">
                    <h3>Přílohy</h3>
                    <p>Houskové knedlíky (1,3) 25,-</p>
                    <p>Vařené brambory 20,-</p>
                </div>
            </section>
        </body>
        </html>
        """
    
    else:
        # Generic mock restaurant
        return """
        <html>
        <body>
            <h1>Test Restaurant</h1>
            <div class="menu">
                <h2>Daily Menu</h2>
                <p>Polévka: Zeleninová polévka 40,-</p>
                <p>Hlavní chod: Kuřecí s rýží (1,7) 160,-</p>
                <p>Nápoj: Cola 0.5l 35,-</p>
            </div>
        </body>
        </html>
        """
