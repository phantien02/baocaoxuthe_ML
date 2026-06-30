from bs4 import BeautifulSoup
from .base import BaseCrawler, CrawledItem


class Crawler3GPP(BaseCrawler):
    source_name = "3gpp"
    BASE_URL = "https://www.3gpp.org/news-events/3gpp-news"

    def crawl(self) -> list[CrawledItem]:
        try:
            html = self._get_html(self.BASE_URL)
            soup = BeautifulSoup(html, "html.parser")
            items = []
            for article in soup.select("article")[:15]:
                title_tag = article.select_one("h3 a, h2 a, h3, h2")
                link_tag = article.select_one("a[href]")
                summary_tag = article.select_one("p.summary, p.description, p")
                if not title_tag or not link_tag:
                    continue
                href = link_tag.get("href", "")
                url = href if href.startswith("http") else f"https://www.3gpp.org{href}"
                title = title_tag.get_text(strip=True)
                content = summary_tag.get_text(strip=True) if summary_tag else title
                items.append(CrawledItem(
                    source=self.source_name,
                    title=title,
                    url=url,
                    content=content,
                    topic=self._detect_topic(title + " " + content),
                ))
            return items
        except Exception as e:
            print(f"[{self.source_name}] crawl error: {e}")
            return []

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
