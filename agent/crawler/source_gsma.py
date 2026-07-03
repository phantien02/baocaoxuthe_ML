from .base import BaseCrawler, CrawledItem


class CrawlerGSMA(BaseCrawler):
    source_name = "gsma"
    # RSS feed có sẵn pubDate; trang HTML cũ không trả về bài nào
    FEED_URL = "https://www.gsma.com/newsroom/feed/"

    def crawl(self) -> list[CrawledItem]:
        try:
            return self._fetch_rss_items(self.FEED_URL)
        except Exception as e:
            print(f"[{self.source_name}] crawl error: {e}")
            return []
