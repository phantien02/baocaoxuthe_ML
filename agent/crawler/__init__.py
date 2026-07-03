from .source_3gpp import Crawler3GPP
from .source_gsma import CrawlerGSMA
from .source_etsi import CrawlerETSI
from .source_ericsson import CrawlerEricsson
from .source_nokia import CrawlerNokia
from .source_huawei import CrawlerHuawei
from agent.storage.database import save_crawled_item

CRAWLERS = [
    Crawler3GPP(),
    CrawlerGSMA(),
    CrawlerETSI(),
    CrawlerEricsson(),
    CrawlerNokia(),
    CrawlerHuawei(),
]


def run_all_crawlers() -> int:
    total_new = 0
    for crawler in CRAWLERS:
        items = crawler.crawl()
        for item in items:
            if save_crawled_item(item.source, item.title, item.url, item.content, item.topic,
                                 published_at=item.date):
                total_new += 1
    return total_new
