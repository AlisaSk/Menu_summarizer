import os
from typing import Optional

class Settings:
    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/cache.sqlite")
    
    # LLM API Keys
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    
    # Development
    USE_MOCK: bool = os.getenv("USE_MOCK", "0").lower() in ("1", "true", "yes")
    
    # Scraping
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    USER_AGENT: str = os.getenv("USER_AGENT", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    # Playwright / JS rendering
    PLAYWRIGHT_HEADLESS: bool = os.getenv("PLAYWRIGHT_HEADLESS", "1").lower() in ("1", "true", "yes")
    JS_WAIT_TIMEOUT_MS: int = int(os.getenv("JS_WAIT_TIMEOUT_MS", "10000"))
    JS_EXTRA_WAIT_MS: int = int(os.getenv("JS_EXTRA_WAIT_MS", "1500"))
    
    # Cache TTL in hours
    CACHE_TTL_HOURS: int = int(os.getenv("CACHE_TTL_HOURS", "24"))

    # LLM timeouts and retries
    LLM_TIMEOUT_SECONDS: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "50"))
    LLM_MAX_ATTEMPTS: int = int(os.getenv("LLM_MAX_ATTEMPTS", "3"))

settings = Settings()
