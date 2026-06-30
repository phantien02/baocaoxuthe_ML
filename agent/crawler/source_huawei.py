from .base import BaseCrawler, CrawledItem


class CrawlerHuawei(BaseCrawler):
    source_name = "huawei"

    def crawl(self) -> list[CrawledItem]:
        return []
