from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class LinkItem(BaseModel):
    text: str
    href: str


class ImageItem(BaseModel):
    src: str
    alt: str


class SectionContent(BaseModel):
    headings: List[str] = Field(default_factory=list)
    text: str = ""
    links: List[LinkItem] = Field(default_factory=list)
    images: List[ImageItem] = Field(default_factory=list)
    lists: List[List[str]] = Field(default_factory=list)
    tables: List[List[List[str]]] = Field(default_factory=list)


class Section(BaseModel):
    id: str
    type: str
    label: str
    sourceUrl: str
    content: SectionContent
    rawHtml: str
    truncated: bool = False


class MetaData(BaseModel):
    title: str = ""
    description: str = ""
    language: str = ""
    canonical: str = ""


class Interactions(BaseModel):
    clicks: List[str] = Field(default_factory=list)
    scrolls: int = 0
    pages: List[str] = Field(default_factory=list)


class ErrorItem(BaseModel):
    message: str
    phase: str


class ScrapeResult(BaseModel):
    url: str
    scrapedAt: str
    meta: MetaData
    sections: List[Section] = Field(default_factory=list)
    interactions: Interactions
    errors: List[ErrorItem] = Field(default_factory=list)


class ScrapeResponse(BaseModel):
    result: ScrapeResult


class ScrapeRequest(BaseModel):
    url: str
