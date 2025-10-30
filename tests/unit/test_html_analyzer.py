import pytest
from app.fetch.html_analyzer import (
    should_use_html_mode,
    extract_date_info_from_html,
    clean_html_for_llm,
    get_menu_focused_html
)

class TestHtmlAnalyzer:
    """Unit tests for HTML analysis functionality"""
    
    def test_should_use_html_mode_with_tables(self):
        """Test HTML mode detection with table structure"""
        html_with_table = """
        <html>
        <body>
            <table class="menu">
                <tr>
                    <td>Polévka</td>
                    <td>45,-</td>
                </tr>
                <tr>
                    <td>Hlavní chod</td>
                    <td>185 Kč</td>
                </tr>
            </table>
        </body>
        </html>
        """
        assert should_use_html_mode(html_with_table) is True
    
    def test_should_use_html_mode_with_lists(self):
        """Test HTML mode detection with list structure"""
        html_with_lists = """
        <html>
        <body>
            <ul class="menu-items">
                <li>Polévka - 45,-</li>
                <li>Řízek - 185,-</li>
            </ul>
            <ol>
                <li>Item 1</li>
                <li>Item 2</li>
            </ol>
        </body>
        </html>
        """
        assert should_use_html_mode(html_with_lists) is True
    
    def test_should_use_html_mode_with_menu_classes(self):
        """Test HTML mode detection with menu-specific classes"""
        html_with_menu_class = """
        <html>
        <body>
            <div class="daily-menu">
                <p>Today's special</p>
            </div>
        </body>
        </html>
        """
        assert should_use_html_mode(html_with_menu_class) is True
    
    def test_should_use_text_mode_simple_html(self):
        """Test that simple HTML without structure uses text mode"""
        simple_html = """
        <html>
        <body>
            <p>Just some text without structure</p>
        </body>
        </html>
        """
        assert should_use_html_mode(simple_html) is False
    
    def test_extract_date_info_czech_dates(self):
        """Test extraction of Czech date formats"""
        html_with_dates = """
        <html>
        <body>
            <h1>Menu na 27.10.2025</h1>
            <p>Dnešní menu - středa</p>
            <div>Denní menu pro pondělí</div>
        </body>
        </html>
        """
        date_info = extract_date_info_from_html(html_with_dates)
        
        assert "27.10.2025" in date_info["found_dates"]
        assert "středa" in date_info["found_weekdays"]
        assert "pondělí" in date_info["found_weekdays"]
        assert any("denní menu" in indicator.lower() for indicator in date_info["menu_type_indicators"])
    
    def test_extract_date_info_iso_dates(self):
        """Test extraction of ISO date formats"""
        html_with_iso = """
        <html>
        <body>
            <time datetime="2025-10-27">Today</time>
            <meta name="updated" content="2025-10-27T12:00:00">
        </body>
        </html>
        """
        date_info = extract_date_info_from_html(html_with_iso)
        
        assert "2025-10-27" in date_info["found_dates"]
    
    def test_clean_html_for_llm(self):
        """Test HTML cleaning for LLM processing"""
        dirty_html = """
        <html>
        <head>
            <script>console.log('test');</script>
            <style>.test { color: red; }</style>
        </head>
        <body>
            <nav>Navigation</nav>
            <div class="menu">
                <h2>Today's Menu</h2>
                <p>Soup: 45,-</p>
            </div>
            <footer>Footer content</footer>
            <script>alert('popup');</script>
        </body>
        </html>
        """
        
        cleaned = clean_html_for_llm(dirty_html)
        
        # Should remove scripts, styles, nav, footer
        assert "<script>" not in cleaned
        assert "<style>" not in cleaned
        assert "<nav>" not in cleaned
        assert "<footer>" not in cleaned
        
        # Should keep menu content
        assert "Today's Menu" in cleaned
        assert "Soup: 45,-" in cleaned
    
    def test_get_menu_focused_html(self):
        """Test extraction of menu-focused HTML"""
        html_with_menu = """
        <html>
        <body>
            <header>Site header</header>
            <nav>Navigation</nav>
            <div class="daily-menu">
                <h2>Denní menu</h2>
                <ul>
                    <li>Polévka - 45,-</li>
                    <li>Hlavní chod - 185,-</li>
                </ul>
            </div>
            <aside>Sidebar</aside>
            <footer>Footer</footer>
        </body>
        </html>
        """
        
        focused_html = get_menu_focused_html(html_with_menu)
        
        # Should contain menu content
        assert "Denní menu" in focused_html
        assert "Polévka - 45,-" in focused_html
        assert "Hlavní chod - 185,-" in focused_html
        
        # Should be valid HTML structure
        assert "<html>" in focused_html
        assert "<body>" in focused_html
    
    def test_get_menu_focused_html_fallback(self):
        """Test fallback when no specific menu content found"""
        generic_html = """
        <html>
        <body>
            <div>
                <p>Some restaurant content but no specific menu markers</p>
                <p>Price: 150,- for something</p>
            </div>
        </body>
        </html>
        """
        
        focused_html = get_menu_focused_html(generic_html)
        
        # Should return cleaned version of full content
        assert "Some restaurant content" in focused_html
        assert "150,-" in focused_html
        assert "<html>" in focused_html

class TestDateExtraction:
    """Specific tests for date and weekday extraction"""
    
    def test_multiple_date_formats(self):
        """Test various date format recognition"""
        html_multi_dates = """
        <div>
            <span>27.10.2025</span>
            <span>27.10.</span>
            <span>2025-10-27</span>
            <span>27/10/2025</span>
        </div>
        """
        
        date_info = extract_date_info_from_html(html_multi_dates)
        dates = date_info["found_dates"]
        
        assert "27.10.2025" in dates
        assert "27.10." in dates
        assert "2025-10-27" in dates
        assert "27/10/2025" in dates
    
    def test_weekday_variations(self):
        """Test recognition of various weekday formats"""
        html_weekdays = """
        <div>
            <p>pondělí speciál</p>
            <p>Menu na ÚTERÝ</p>
            <p>Středa - dnešní nabídka</p>
            <h2>čtvrtek</h2>
            <span>pá. speciálka</span>
            <span>so menu</span>
            <span>ne. brunch</span>
        </div>
        """
        
        date_info = extract_date_info_from_html(html_weekdays)
        weekdays = [wd.lower() for wd in date_info["found_weekdays"]]
        
        assert "pondělí" in weekdays
        assert "úterý" in weekdays
        assert "středa" in weekdays
        assert "čtvrtek" in weekdays
    
    def test_menu_type_indicators(self):
        """Test recognition of menu type indicators"""
        html_indicators = """
        <div>
            <h1>Denní menu</h1>
            <h2>Daily menu special</h2>
            <p>Menu dne</p>
            <span>Dnes nabízíme</span>
            <div>Polední menu</div>
            <section>Lunch menu</section>
            <p>Týdenní menu</p>
            <h3>Jídelní lístek</h3>
        </div>
        """
        
        date_info = extract_date_info_from_html(html_indicators)
        indicators = [ind.lower() for ind in date_info["menu_type_indicators"]]
        
        assert "denní menu" in indicators
        assert "daily menu" in indicators
        assert "menu dne" in indicators
        assert "dnes" in indicators
        assert "polední menu" in indicators
        assert "lunch menu" in indicators
        assert "týdenní menu" in indicators
        assert "jídelní lístek" in indicators
