from dataclasses import dataclass, field
from typing import Optional
import requests


@dataclass
class CrawledItem:
    source: str
    title: str
    url: str
    content: str
    topic: str
    date: Optional[str] = None


class BaseCrawler:
    source_name: str = ""
    topics: list = field(default_factory=list)

    def crawl(self) -> list[CrawledItem]:
        raise NotImplementedError

    def _get_html(self, url: str, timeout: int = 15) -> str:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; CoreNetworkAgent/1.0; +viettel.com.vn)"}
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.text
