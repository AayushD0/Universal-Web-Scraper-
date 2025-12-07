import httpx
from selectolax.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from typing import List, Tuple, Optional
from .models import (
    MetaData, Section, SectionContent, LinkItem, ImageItem, ErrorItem
)

NOISE_SELECTORS = [
    '[class*="cookie"]', '[class*="Cookie"]',
    '[class*="consent"]', '[class*="Consent"]',
    '[class*="modal"]', '[class*="Modal"]',
    '[class*="popup"]', '[class*="Popup"]',
    '[class*="newsletter"]', '[class*="Newsletter"]',
    '[class*="banner"]', '[id*="cookie"]',
    '[id*="consent"]', '[id*="modal"]',
    '[id*="popup"]', '[id*="newsletter"]',
    '[aria-label*="cookie"]', '[aria-label*="consent"]',
    'script', 'style', 'noscript', 'iframe',
    '[hidden]', '[aria-hidden="true"]'
]

SECTION_SELECTORS = ['header', 'nav', 'main', 'section', 'article', 'aside', 'footer']

SECTION_TYPE_MAP = {
    'header': 'hero',
    'nav': 'nav',
    'footer': 'footer',
    'main': 'section',
    'section': 'section',
    'article': 'section',
    'aside': 'section'
}


def extract_metadata(tree: HTMLParser, url: str) -> MetaData:
    title = ""
    title_tag = tree.css_first('title')
    if title_tag:
        title = title_tag.text(strip=True)
    
    og_title = tree.css_first('meta[property="og:title"]')
    if og_title and og_title.attributes.get('content'):
        title = og_title.attributes.get('content', title)
    
    description = ""
    desc_tag = tree.css_first('meta[name="description"]')
    if desc_tag:
        description = desc_tag.attributes.get('content', '')
    
    language = ""
    html_tag = tree.css_first('html')
    if html_tag:
        language = html_tag.attributes.get('lang', '')
    
    canonical = ""
    canonical_tag = tree.css_first('link[rel="canonical"]')
    if canonical_tag:
        canonical = canonical_tag.attributes.get('href', '')
    if canonical:
        canonical = urljoin(url, canonical)
    
    return MetaData(
        title=title or "",
        description=description or "",
        language=language or "",
        canonical=canonical or ""
    )


def make_absolute_url(href: str, base_url: str) -> str:
    if not href:
        return ""
    if href.startswith(('http://', 'https://', '//')):
        if href.startswith('//'):
            parsed = urlparse(base_url)
            return f"{parsed.scheme}:{href}"
        return href
    return urljoin(base_url, href)


def extract_section_content(element, base_url: str) -> SectionContent:
    headings = []
    for h in element.css('h1, h2, h3, h4, h5, h6'):
        text = h.text(strip=True)
        if text:
            headings.append(text)
    
    text_parts = []
    for p in element.css('p'):
        txt = p.text(strip=True)
        if txt:
            text_parts.append(txt)
    
    if not text_parts:
        all_text = element.text(strip=True)
        if all_text:
            text_parts.append(all_text[:500])
    
    links = []
    for a in element.css('a[href]'):
        href = a.attributes.get('href', '')
        link_text = a.text(strip=True)
        if href and not href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
            links.append(LinkItem(
                text=link_text or href,
                href=make_absolute_url(href, base_url)
            ))
    
    images = []
    for img in element.css('img[src]'):
        src = img.attributes.get('src', '')
        alt = img.attributes.get('alt', '')
        if src:
            images.append(ImageItem(
                src=make_absolute_url(src, base_url),
                alt=alt or ""
            ))
    
    lists = []
    for ul in element.css('ul, ol'):
        items = []
        for li in ul.css('li'):
            item_text = li.text(strip=True)
            if item_text:
                items.append(item_text)
        if items:
            lists.append(items)
    
    tables = []
    for table in element.css('table'):
        table_data = []
        for tr in table.css('tr'):
            row = []
            for cell in tr.css('th, td'):
                cell_text = cell.text(strip=True)
                row.append(cell_text)
            if row:
                table_data.append(row)
        if table_data:
            tables.append(table_data)
    
    return SectionContent(
        headings=headings,
        text=" ".join(text_parts),
        links=links[:50],
        images=images[:20],
        lists=lists[:10],
        tables=tables[:5]
    )


def determine_section_type(element, content: SectionContent) -> str:
    tag_name = element.tag.lower() if element.tag else ""
    
    if tag_name in SECTION_TYPE_MAP:
        base_type = SECTION_TYPE_MAP[tag_name]
    else:
        base_type = "unknown"
    
    classes = element.attributes.get('class', '').lower()
    element_id = element.attributes.get('id', '').lower()
    combined = classes + " " + element_id
    
    if any(x in combined for x in ['hero', 'banner', 'jumbotron', 'splash']):
        return 'hero'
    if any(x in combined for x in ['nav', 'menu', 'navigation']):
        return 'nav'
    if any(x in combined for x in ['footer', 'foot']):
        return 'footer'
    if any(x in combined for x in ['faq', 'accordion', 'question']):
        return 'faq'
    if any(x in combined for x in ['price', 'pricing', 'plan']):
        return 'pricing'
    if any(x in combined for x in ['grid', 'cards', 'gallery']):
        return 'grid'
    if any(x in combined for x in ['list', 'items']):
        return 'list'
    
    return base_type


def generate_label(element, content: SectionContent) -> str:
    if content.headings:
        return content.headings[0][:50]
    
    aria_label = element.attributes.get('aria-label', '')
    if aria_label:
        return aria_label[:50]
    
    if content.text:
        words = content.text.split()[:7]
        return " ".join(words)
    
    tag = element.tag or "Section"
    return f"{tag.capitalize()} Section"


def remove_noise(tree: HTMLParser) -> None:
    for selector in NOISE_SELECTORS:
        try:
            for node in tree.css(selector):
                node.decompose()
        except Exception:
            pass


def extract_sections(tree: HTMLParser, url: str) -> List[Section]:
    sections = []
    section_counts = {}
    
    for selector in SECTION_SELECTORS:
        for element in tree.css(selector):
            content = extract_section_content(element, url)
            
            if not content.text and not content.headings and not content.links:
                continue
            
            section_type = determine_section_type(element, content)
            label = generate_label(element, content)
            
            if section_type not in section_counts:
                section_counts[section_type] = 0
            section_id = f"{section_type}-{section_counts[section_type]}"
            section_counts[section_type] += 1
            
            raw_html = element.html or ""
            truncated = False
            if len(raw_html) > 1000:
                raw_html = raw_html[:1000] + "..."
                truncated = True
            
            sections.append(Section(
                id=section_id,
                type=section_type,
                label=label,
                sourceUrl=url,
                content=content,
                rawHtml=raw_html,
                truncated=truncated
            ))
    
    if not sections:
        body = tree.css_first('body')
        if body:
            content = extract_section_content(body, url)
            raw_html = body.html or ""
            truncated = len(raw_html) > 1000
            if truncated:
                raw_html = raw_html[:1000] + "..."
            
            sections.append(Section(
                id="body-0",
                type="unknown",
                label=generate_label(body, content),
                sourceUrl=url,
                content=content,
                rawHtml=raw_html,
                truncated=truncated
            ))
    
    return sections


def get_text_content_length(tree: HTMLParser) -> int:
    body = tree.css_first('body')
    if body:
        text = body.text(strip=True)
        return len(text)
    return 0


async def static_scrape(url: str) -> Tuple[MetaData, List[Section], List[ErrorItem], str, bool]:
    errors = []
    needs_js = False
    html_content = ""
    
    try:
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            html_content = response.text
    except httpx.TimeoutException:
        errors.append(ErrorItem(message="Request timeout", phase="fetch"))
        return MetaData(), [], errors, "", True
    except httpx.HTTPStatusError as e:
        errors.append(ErrorItem(message=f"HTTP {e.response.status_code}", phase="fetch"))
        return MetaData(), [], errors, "", True
    except Exception as e:
        errors.append(ErrorItem(message=str(e), phase="fetch"))
        return MetaData(), [], errors, "", True
    
    try:
        tree = HTMLParser(html_content)
        remove_noise(tree)
        
        text_length = get_text_content_length(tree)
        if text_length < 500:
            needs_js = True
        
        metadata = extract_metadata(tree, url)
        sections = extract_sections(tree, url)
        
        if not sections or all(not s.content.text for s in sections):
            needs_js = True
        
        return metadata, sections, errors, html_content, needs_js
        
    except Exception as e:
        errors.append(ErrorItem(message=str(e), phase="parse"))
        return MetaData(), [], errors, html_content, True
