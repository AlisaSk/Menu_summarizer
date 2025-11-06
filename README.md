# Restaurant Menu Summarizer

REST API service for extracting and structuring Czech restaurant menus using LLM.

## Description

The service accepts a restaurant page URL, extracts content, parses today's menu, and returns structured JSON. Results are cached in SQLite using URL + date as the key.

## Architecture Decisions

### Content Fetching Strategy
**Chosen Strategy A: Custom scraper (requests + BeautifulSoup)**
- More control over the extraction process
- Ability to handle menu-specific elements
- More predictable behavior
- Support for various web page formats

### Caching
**SQLite with (URL + date) key**
- Simple deployment and maintenance
- Automatic date-based invalidation (older than today)
- Unique index on (menu_url, date) prevents duplication
- Suitable for this service's data volumes

### Data Schema
**Pydantic models for strict validation**
- `MenuItem`: category, name, price, allergens, weight
- `MenuData`: restaurant name, date, day of week, menu items list
- Input and output API validation

## Quick Start

### API Key Setup

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Sign in with your Google account
3. Click "Get API key" → "Create API key"
4. Copy the key
5. Create `.env` file from `.env.example` and add the key:

```bash
cp .env.example .env
# Edit .env and add: GOOGLE_API_KEY=your_key_here
```

### Docker Compose

```bash
# Set GOOGLE_API_KEY in .env file, then:

# Production mode
docker compose up -d --build
```

## API

### POST /summarize

Accepts restaurant URL and returns structured menu.

**Request:**
```json
{
  "url": "https://restaurace-example.cz/menu"
}
```

**Response:**
```json
{
  "cached": false,
  "data": {
    "restaurant_name": "Restaurace Example",
    "date": "2025-10-27",
    "day_of_week": "neděle",
    "menu_items": [
      {
        "category": "polévka",
        "name": "Hovězí vývar s nudlemi",
        "price": 45,
        "allergens": ["1", "3", "9"],
        "weight": "300ml"
      }
    ],
    "daily_menu": true,
    "source_url": "https://restaurace-example.cz/menu"
  }
}
```

### Other Endpoints
- `GET /health` - service health check
- `GET /cache/stats` - cache statistics
- `GET /` - service information

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_MOCK` | Use mock instead of LLM API | `0` |
| `DATABASE_PATH` | Path to SQLite file | `data/cache.sqlite` |
| `GOOGLE_API_KEY` | Google Gemini API key | - |
| `REQUEST_TIMEOUT` | Request timeout (seconds) | `300` |
| `CACHE_TTL_HOURS` | Cache TTL (hours) | `24` |
| `LLM_TIMEOUT_SECONDS` | LLM request timeout | `50` |
| `LLM_MAX_ATTEMPTS` | Max retry attempts for LLM | `3` |
| `PLAYWRIGHT_HEADLESS` | Run browser headless | `1` |
| `JS_WAIT_TIMEOUT_MS` | JS page load timeout | `10000` |
| `JS_EXTRA_WAIT_MS` | Extra wait for lazy-load | `1500` |

## Testing

### Running Tests

```bash
# Only required tests for assignment (6 tests)
pytest tests/test_required.py -v

# All tests (56 tests: unit + integration + required)
pytest -v

# Only unit tests
pytest tests/unit/ -v

# Only integration tests
pytest tests/integration/ -v

```

### Required Tests (`tests/test_required.py`)

- `test_menu_item_validation` - MenuData structure validation
- `test_price_normalization` - price parsing and normalization
- `test_allergen_extraction` - allergen code extraction

- `test_full_api_flow` - full API cycle with mock LLM

- `test_cache_prevents_duplicate_llm_calls` - verify second request doesn't call LLM
- `test_cache_purge_old_entries` - old entries cleanup

### Additional Tests

**Unit tests** (`tests/unit/`):
- `test_cache.py` - cache operations (set/get/purge/clear)
- `test_html_analyzer.py` - HTML analysis, date extraction, cleanup
- `test_schemas.py` - Pydantic model validation
- `test_utils.py` - price normalization, weight conversion, weekday detection

**Integration tests** (`tests/integration/`):
- `test_api.py` - API endpoints, cache integration, health checks

**Total: 56 tests** 

## Test Restaurant URLs (tested on my favourite places :) )

For testing you can use:
- `https://sushijo.cz/classic-rolls/`
- `https://anglicka.matokapraha.cz/cz/delivery/section:menu/main-dish`
- `https://www.lukalu.cz/`

**Note:** In `USE_MOCK=1` mode, mock data will be returned.

## Potential Improvements (with more time)

- Menu image support (OCR) - many sites have menus in .png format
- Scraping optimization - currently sending partial HTML if file is too large
- API cost optimization - currently need many tokens for good results (expensive)
- Metrics and response quality monitoring
- Webhook notifications for menu changes
- Use a RAG and/or LangChain-based approach to standardize menu extraction, storing previously parsed menu examples and automatically injecting them into prompts to improve structural consistency. This would reduce LLM calls and make output quality more stable.

## LLM Integration

Service uses Google Gemini 2.5 Flash with prompts for:
- Price normalization ("145,-" → 145)
- Weekday detection from menu text
- Weight and volume conversion
- Allergen code extraction

**Gemini offers a free tier, that's why it was chosen!**

## Error Handling

Service handles the following cases:
- Page unavailability/timeouts
- Missing menu in text
- LLM API errors
- Incorrect data formats

## Development

### Project Structure
```
menu_summarizer/
├── app/
│   ├── main.py                    # FastAPI application with lifespan
│   ├── schemas.py                 # Pydantic models (MenuItem, MenuData)
│   ├── api/
│   │   └── routes.py              # API endpoints (/summarize, /health, /cache/stats)
│   ├── core/
│   │   └── config.py              # Configuration (Settings with env variables)
│   ├── fetch/
│   │   ├── base.py                # Base Fetcher class
│   │   ├── html_analyzer.py       # HTML preprocessing and cleanup
│   │   ├── js_scraper.py          # Playwright for JS sites (SPA)
│   │   ├── requests_fetcher.py    # HTTP client (requests + BeautifulSoup)
│   │   ├── scraper.py             # Main scraping logic with JS fallback
│   │   └── utils.py               # Utilities (dates, prices, allergens, weight)
│   ├── llm/
│   │   └── client.py              # Gemini integration with retry logic
│   ├── cache/
│   │   └── db.py                  # SQLite caching (url + date)
│   └── services/
│       └── summarize.py           # Main business logic
├── tests/
│   ├── conftest.py                # Pytest fixtures (setup/teardown)
│   ├── test_required.py           # Required tests (6 tests)
│   ├── unit/                      # Unit tests (cache, schemas, utils, html)
│   └── integration/               # Integration tests (API endpoints)
├── docker/
│   └── entrypoint.sh              # Docker entrypoint script
├── data/                          # SQLite database (cache.sqlite)
├── .env                           # Environment variables (not in git)
├── .env.example                   # .env file template
├── .gitignore                     # Git ignore rules
├── docker-compose.yml             # Docker Compose configuration
├── Dockerfile                     # Docker image with Playwright
├── pytest.ini                     # Pytest configuration
├── requirements.txt               # Python dependencies
└── README.md                      # Documentation
```

### Adding a New LLM Provider
1. Add API key to `config.py`
2. Create client in `llm/client.py`
3. Update `summarize_menu` function

## License

MIT License
