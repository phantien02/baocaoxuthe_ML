from .base import BaseCrawler, CrawledItem


class CrawlerEricsson(BaseCrawler):
    source_name = "ericsson"

    def crawl(self) -> list[CrawledItem]:
        return []
