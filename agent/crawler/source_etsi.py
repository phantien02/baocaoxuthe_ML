from .base import BaseCrawler, CrawledItem


class CrawlerETSI(BaseCrawler):
    source_name = "etsi"
    # RSS feed có sẵn pubDate; trang HTML cũ bị timeout
    FEED_URL = "https://www.etsi.org/newsroom/rss"

    def crawl(self) -> list[CrawledItem]:
        try:
            return self._fetch_rss_items(self.FEED_URL)
        except Exception as e:
            print(f"[{self.source_name}] crawl error: {e}")
            return []
