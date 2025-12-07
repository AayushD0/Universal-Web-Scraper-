from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timezone
import os

from .scraper.models import ScrapeRequest, ScrapeResponse, ScrapeResult, Interactions
from .scraper.static_scraper import static_scrape
from .scraper.js_scraper import js_scrape

app = FastAPI(title="Universal Web Scraper", version="1.0.0")

class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

app.add_middleware(NoCacheMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates_dir = os.path.join(os.path.dirname(__file__), "templates")
static_dir = os.path.join(os.path.dirname(__file__), "static")

templates = Jinja2Templates(directory=templates_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/healthz")
async def health_check():
    return {"status": "ok"}


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_url(request: ScrapeRequest):
    url = request.url
    scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    metadata, sections, errors, html_content, needs_js = await static_scrape(url)
    
    interactions = Interactions(clicks=[], scrolls=0, pages=[url])
    
    if needs_js or not sections:
        js_metadata, js_sections, js_errors, js_interactions = await js_scrape(
            url,
            existing_metadata=metadata if metadata.title else None,
            existing_sections=sections
        )
        
        if js_metadata and js_metadata.title:
            metadata = js_metadata
        if js_sections:
            sections = js_sections
        errors.extend(js_errors)
        interactions = js_interactions
    
    result = ScrapeResult(
        url=url,
        scrapedAt=scraped_at,
        meta=metadata,
        sections=sections,
        interactions=interactions,
        errors=errors
    )
    
    return ScrapeResponse(result=result)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
