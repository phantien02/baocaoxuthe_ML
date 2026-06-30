from .base import BaseCrawler, CrawledItem


class CrawlerETSI(BaseCrawler):
    source_name = "etsi"

    def crawl(self) -> list[CrawledItem]:
        return []
