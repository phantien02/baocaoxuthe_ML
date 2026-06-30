from .base import BaseCrawler, CrawledItem


class CrawlerNokia(BaseCrawler):
    source_name = "nokia"

    def crawl(self) -> list[CrawledItem]:
        return []
