from .base import BaseCrawler, CrawledItem


class Crawler3GPP(BaseCrawler):
    source_name = "3gpp"
    # RSS feed có sẵn pubDate; trang HTML news render bằng JS nên không crawl được
    FEED_URL = "https://www.3gpp.org/news-events/3gpp-news?format=feed&type=rss"

    def crawl(self) -> list[CrawledItem]:
        try:
            return self._fetch_rss_items(self.FEED_URL)
        except Exception as e:
            print(f"[{self.source_name}] crawl error: {e}")
            return []
