# Universal Web Scraper

A production-ready universal website scraper with FastAPI backend that supports static and JavaScript-rendered pages.

## Features

- **Static Scraping**: Fast extraction using httpx + selectolax
- **JS Rendering**: Playwright-based fallback for JavaScript-heavy sites
- **Interactive Scraping**: Supports tab clicks, "Load more" buttons, infinite scroll, and pagination
- **Section-Aware Output**: Structured JSON with semantic section detection
- **Noise Filtering**: Automatically removes cookie banners, modals, and popups
- **Frontend UI**: Minimal but functional JSON viewer with download capability

## Quick Start

```bash
chmod +x run.sh
./run.sh
```

This will:
1. Create a Python virtual environment
2. Install all dependencies
3. Install Playwright Chromium browser
4. Start the server on http://localhost:8000

## Manual Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Start server
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### Health Check
```
GET /healthz
Response: {"status": "ok"}
```

### Scrape URL
```
POST /scrape
Body: {"url": "https://example.com"}
Response: Structured JSON with sections, metadata, and interactions
```

### Frontend
```
GET /
Response: HTML page with URL input, Scrape button, and JSON viewer
```

## Test URLs

1. **Static Site**: https://en.wikipedia.org/wiki/Artificial_intelligence
   - Tests basic HTML parsing and section extraction
   - Demonstrates metadata extraction (title, description, language)
   - Shows section grouping with headings and content

2. **JS-Heavy Site**: https://vercel.com/
   - Tests Playwright fallback and JavaScript rendering
   - Demonstrates automatic JS detection when static content is insufficient
   - Shows tab clicking interaction

3. **Pagination**: https://news.ycombinator.com/
   - Tests pagination link following (depth >= 3)
   - Demonstrates multi-page scraping
   - Records visited URLs in interactions.pages

## Response Schema

```json
{
  "result": {
    "url": "https://example.com",
    "scrapedAt": "2025-01-01T00:00:00Z",
    "meta": {
      "title": "Page Title",
      "description": "Meta description",
      "language": "en",
      "canonical": "https://example.com"
    },
    "sections": [
      {
        "id": "hero-0",
        "type": "hero",
        "label": "Welcome to Example",
        "sourceUrl": "https://example.com",
        "content": {
          "headings": ["Welcome"],
          "text": "Main content text...",
          "links": [{"text": "Learn More", "href": "https://example.com/learn"}],
          "images": [{"src": "https://example.com/img.png", "alt": "Hero image"}],
          "lists": [["Item 1", "Item 2"]],
          "tables": []
        },
        "rawHtml": "<section>...</section>",
        "truncated": true
      }
    ],
    "interactions": {
      "clicks": ["[role=\"tab\"]", "button:has-text(\"Load more\")"],
      "scrolls": 3,
      "pages": ["https://example.com", "https://example.com/?page=2"]
    },
    "errors": []
  }
}
```

## Known Limitations

1. **Rate Limiting**: No built-in rate limiting; external sites may block rapid requests
2. **Authentication**: Does not handle login-protected pages
3. **CAPTCHAs**: Cannot solve CAPTCHA challenges
4. **Dynamic Content**: Some AJAX-loaded content may not be captured if it loads after our wait period
5. **File Downloads**: Does not extract linked documents (PDFs, etc.)
6. **Iframes**: Content inside iframes is not extracted
7. **Shadow DOM**: Web components with Shadow DOM may not be fully parsed
8. **Same-Origin**: Pagination only follows links within the same domain

## Architecture

```
src/
├── main.py              # FastAPI application with /healthz, /scrape, / endpoints
├── scraper/
│   ├── models.py        # Pydantic response schemas
│   ├── static_scraper.py # httpx + selectolax scraping
│   └── js_scraper.py    # Playwright-based JS rendering with interactions
├── templates/
│   └── index.html       # Frontend UI with JSON viewer
└── static/
    └── styles.css       # Styling
```

## Environment Notes

- Python 3.10+ required
- Playwright requires Chromium browser (installed via `playwright install chromium`)
- Server binds to 0.0.0.0:8000 for accessibility

## License

MIT
