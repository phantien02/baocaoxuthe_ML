from .base import BaseCrawler, CrawledItem


class CrawlerGSMA(BaseCrawler):
    source_name = "gsma"

    def crawl(self) -> list[CrawledItem]:
        return []
