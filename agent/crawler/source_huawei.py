from bs4 import BeautifulSoup
from .base import BaseCrawler, CrawledItem
from .source_3gpp import Crawler3GPP


class CrawlerHuawei(BaseCrawler):
    source_name = "huawei"
    BASE_URL = "https://carrier.huawei.com/en/insights"

    def crawl(self) -> list[CrawledItem]:
        try:
            html = self._get_html(self.BASE_URL)
            soup = BeautifulSoup(html, "html.parser")
            items = []
            detector = Crawler3GPP()
            for card in soup.select(".insight-item, article, .card")[:15]:
                title_tag = card.select_one("h3 a, h2 a, h3, h2")
                link_tag = card.select_one("a[href]")
                summary_tag = card.select_one("p")
                if not title_tag or not link_tag:
                    continue
                href = link_tag.get("href", "")
                url = href if href.startswith("http") else f"https://carrier.huawei.com{href}"
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
