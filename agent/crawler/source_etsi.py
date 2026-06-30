from bs4 import BeautifulSoup
from .base import BaseCrawler, CrawledItem
from .source_3gpp import Crawler3GPP


class CrawlerETSI(BaseCrawler):
    source_name = "etsi"
    BASE_URL = "https://www.etsi.org/news-events/news"

    def crawl(self) -> list[CrawledItem]:
        try:
            html = self._get_html(self.BASE_URL)
            soup = BeautifulSoup(html, "html.parser")
            items = []
            detector = Crawler3GPP()
            for card in soup.select(".news-list-item, article, .item")[:15]:
                title_tag = card.select_one("h3 a, h2 a, h3, h2")
                link_tag = card.select_one("a[href]")
                summary_tag = card.select_one("p")
                if not title_tag or not link_tag:
                    continue
                href = link_tag.get("href", "")
                url = href if href.startswith("http") else f"https://www.etsi.org{href}"
                title = title_tag.get_text(strip=True)
                content = summary_tag.get_text(strip=True) if summary_tag else title
                items.append(CrawledItem(
                    source=self.source_name, title=title, url=url,
                    content=content, topic=detector._detect_topic(title + " " + content),
                ))
            return items
        except Exception as e:
            print(f"[{self.source_name}] crawl error: {e}")
            return []
