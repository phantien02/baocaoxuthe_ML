import email.utils
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup


@dataclass
class CrawledItem:
    source: str
    title: str
    url: str
    content: str
    topic: str
    date: Optional[str] = None  # ngày xuất bản "YYYY-MM-DD HH:MM:SS" nếu nguồn cung cấp


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

    def _fetch_rss_items(self, feed_url: str, limit: int = 30) -> list[CrawledItem]:
        """Đọc RSS/Atom feed — ưu tiên hơn crawl HTML vì có sẵn ngày xuất bản (pubDate)."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
        }
        resp = requests.get(feed_url, headers=headers, timeout=20)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        items = []
        for node in list(root.iter("item"))[:limit]:
            title = (node.findtext("title") or "").strip()
            link = (node.findtext("link") or "").strip()
            if not title or not link:
                continue
            desc_html = node.findtext("description") or ""
            desc = BeautifulSoup(desc_html, "html.parser").get_text(" ", strip=True)
            content = desc[:1000] if desc else title
            items.append(CrawledItem(
                source=self.source_name,
                title=title,
                url=link,
                content=content,
                topic=self._detect_topic(f"{title} {desc}"),
                date=self._parse_rss_date(node),
            ))
        return items

    @staticmethod
    def _parse_rss_date(node) -> Optional[str]:
        raw = (node.findtext("pubDate")
               or node.findtext("{http://purl.org/dc/elements/1.1/}date"))
        if not raw:
            return None
        try:
            return email.utils.parsedate_to_datetime(raw).strftime("%Y-%m-%d %H:%M:%S")
        except (TypeError, ValueError):
            pass
        try:
            return datetime.fromisoformat(raw.strip().replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

    def _detect_topic(self, text: str) -> str:
        t = text.lower()
        if any(k in t for k in ("5gc", "amf", "smf", "upf", "nrf", "nwdaf", "5g core", "pcf")):
            return "5GC"
        if any(k in t for k in ("ims", "volte", "vonr", "rcs", "rich communication")):
            return "IMS"
        if any(k in t for k in ("epc", "pgw", "sgw", "mme", "pcrf", "4g core")):
            return "EPC"
        if any(k in t for k in ("autonomous", "self-managing", "zsm", "zero-touch", "ai/ml", "closed loop")):
            return "Autonomous"
        return "General"
