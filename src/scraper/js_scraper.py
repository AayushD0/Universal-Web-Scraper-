import asyncio
from typing import List, Tuple
from playwright.async_api import async_playwright, Page, Browser
from selectolax.parser import HTMLParser
from .models import MetaData, Section, ErrorItem, Interactions
from .static_scraper import (
    extract_metadata, extract_sections, remove_noise
)

TAB_SELECTORS = [
    '[role="tab"]',
    'button[aria-controls]',
    '.tab',
    '[data-toggle="tab"]',
    '.nav-link[data-bs-toggle="tab"]'
]

LOAD_MORE_SELECTORS = [
    'button:has-text("Load more")',
    'button:has-text("Show more")',
    'button:has-text("See more")',
    'button:has-text("View more")',
    '[class*="load-more"]',
    '[class*="loadmore"]',
    '[class*="show-more"]',
    '[data-action="load-more"]'
]

PAGINATION_SELECTORS = [
    'a:has-text("Next")',
    'a:has-text("next")',
    '[rel="next"]',
    '.pagination a:last-child',
    '[aria-label="Next page"]',
    '.next > a',
    'a.next'
]


async def click_tabs(page: Page, interactions: Interactions, errors: List[ErrorItem]) -> None:
    for selector in TAB_SELECTORS:
        try:
            tabs = await page.query_selector_all(selector)
            for i, tab in enumerate(tabs[:3]):
                try:
                    if await tab.is_visible():
                        await tab.click()
                        interactions.clicks.append(selector)
                        await page.wait_for_timeout(500)
                except Exception:
                    pass
        except Exception as e:
            errors.append(ErrorItem(message=f"Tab click error: {str(e)[:50]}", phase="interaction"))


async def click_load_more(page: Page, interactions: Interactions, errors: List[ErrorItem]) -> None:
    for selector in LOAD_MORE_SELECTORS:
        try:
            for _ in range(3):
                try:
                    button = await page.query_selector(selector)
                    if button and await button.is_visible():
                        await button.click()
                        interactions.clicks.append(selector)
                        await page.wait_for_timeout(1000)
                    else:
                        break
                except Exception:
                    break
        except Exception as e:
            errors.append(ErrorItem(message=f"Load more error: {str(e)[:50]}", phase="interaction"))


async def perform_scrolls(page: Page, interactions: Interactions, errors: List[ErrorItem], scroll_count: int = 3) -> None:
    try:
        for i in range(scroll_count):
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            interactions.scrolls += 1
            await page.wait_for_timeout(1500)
            
            try:
                await page.wait_for_load_state('networkidle', timeout=3000)
            except Exception:
                pass
    except Exception as e:
        errors.append(ErrorItem(message=f"Scroll error: {str(e)[:50]}", phase="interaction"))


async def follow_pagination(page: Page, interactions: Interactions, errors: List[ErrorItem], max_pages: int = 3) -> List[str]:
    visited_urls = [page.url]
    
    for _ in range(max_pages - 1):
        next_link = None
        
        for selector in PAGINATION_SELECTORS:
            try:
                link = await page.query_selector(selector)
                if link and await link.is_visible():
                    href = await link.get_attribute('href')
                    if href and href not in visited_urls:
                        next_link = link
                        break
            except Exception:
                continue
        
        if not next_link:
            break
        
        try:
            await next_link.click()
            try:
                await page.wait_for_load_state('networkidle', timeout=5000)
            except Exception:
                await page.wait_for_timeout(2000)
            
            current_url = page.url
            if current_url not in visited_urls:
                visited_urls.append(current_url)
                interactions.pages.append(current_url)
        except Exception as e:
            pass
    
    return visited_urls


async def js_scrape(
    url: str,
    existing_metadata: MetaData = None,
    existing_sections: List[Section] = None
) -> Tuple[MetaData, List[Section], List[ErrorItem], Interactions]:
    errors = []
    interactions = Interactions(clicks=[], scrolls=0, pages=[url])
    metadata = existing_metadata or MetaData()
    sections = existing_sections or []
    
    browser: Browser = None
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until='networkidle', timeout=15000)
            except Exception as e:
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=10000)
                except Exception as e2:
                    errors.append(ErrorItem(message=f"Navigation failed: {str(e2)[:50]}", phase="render"))
                    return metadata, sections, errors, interactions
            
            await page.wait_for_timeout(1000)
            
            await click_tabs(page, interactions, errors)
            await click_load_more(page, interactions, errors)
            await perform_scrolls(page, interactions, errors, scroll_count=3)
            
            await follow_pagination(page, interactions, errors, max_pages=3)
            
            html_content = await page.content()
            
            try:
                tree = HTMLParser(html_content)
                remove_noise(tree)
                
                if not existing_metadata or not existing_metadata.title:
                    metadata = extract_metadata(tree, url)
                
                js_sections = extract_sections(tree, url)
                
                if js_sections:
                    existing_ids = {s.id for s in sections}
                    for sec in js_sections:
                        if sec.id not in existing_ids:
                            sections.append(sec)
                        else:
                            for i, existing in enumerate(sections):
                                if existing.id == sec.id:
                                    if len(sec.content.text) > len(existing.content.text):
                                        sections[i] = sec
                                    break
                
            except Exception as e:
                errors.append(ErrorItem(message=f"Parse error: {str(e)[:50]}", phase="parse"))
            
            await context.close()
            
    except Exception as e:
        errors.append(ErrorItem(message=f"Browser error: {str(e)[:50]}", phase="render"))
    
    return metadata, sections, errors, interactions
