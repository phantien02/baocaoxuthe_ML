import pytest
import responses as resp_lib
from agent.crawler.base import CrawledItem, BaseCrawler
from agent.crawler.source_3gpp import Crawler3GPP


def test_crawled_item_fields():
    item = CrawledItem(
        source="3gpp", title="Test", url="https://3gpp.org/1",
        content="content", topic="5GC",
    )
    assert item.source == "3gpp"
    assert item.topic == "5GC"
    assert item.date is None


def test_base_crawler_requires_crawl():
    class NoCrawl(BaseCrawler):
        source_name = "test"

    with pytest.raises(NotImplementedError):
        NoCrawl().crawl()


@resp_lib.activate
def test_3gpp_crawler_parses_rss():
    resp_lib.add(
        resp_lib.GET,
        Crawler3GPP.FEED_URL,
        body="""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <item>
    <title>5GC NWDAF Release 19 Update</title>
    <link>https://www.3gpp.org/news/5gc-update</link>
    <description>New features for network automation in Release 19.</description>
    <pubDate>Thu, 25 Jun 2026 09:00:00 +0000</pubDate>
  </item>
</channel></rss>""",
        status=200,
    )
    crawler = Crawler3GPP()
    items = crawler.crawl()
    assert isinstance(items, list)
    assert len(items) == 1
    assert items[0].source == "3gpp"
    assert items[0].date == "2026-06-25 09:00:00"
    assert items[0].topic in ("5GC", "IMS", "EPC", "Autonomous", "General")


@resp_lib.activate
def test_3gpp_crawler_returns_empty_on_http_error():
    resp_lib.add(
        resp_lib.GET,
        Crawler3GPP.FEED_URL,
        status=500,
    )
    items = Crawler3GPP().crawl()
    assert items == []


def test_detect_topic_5gc():
    c = Crawler3GPP()
    assert c._detect_topic("AMF SMF UPF 5G core architecture") == "5GC"


def test_detect_topic_ims():
    c = Crawler3GPP()
    assert c._detect_topic("VoLTE VoNR IMS enhancement") == "IMS"


def test_detect_topic_autonomous():
    c = Crawler3GPP()
    assert c._detect_topic("autonomous network ZSM AI/ML operations") == "Autonomous"
