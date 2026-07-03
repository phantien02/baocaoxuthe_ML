import pytest
import responses as resp_lib
from agent.crawler.source_3gpp import Crawler3GPP
from agent.crawler.source_gsma import CrawlerGSMA
from agent.crawler.source_etsi import CrawlerETSI
from agent.crawler.source_ericsson import CrawlerEricsson
from agent.crawler.source_nokia import CrawlerNokia
from agent.crawler.source_huawei import CrawlerHuawei


CRAWLERS_UNDER_TEST = [
    (Crawler3GPP, Crawler3GPP.FEED_URL),
    (CrawlerGSMA, CrawlerGSMA.FEED_URL),
    (CrawlerETSI, CrawlerETSI.FEED_URL),
    (CrawlerEricsson, "https://www.ericsson.com/en/blog/tags/core-network"),
    (CrawlerNokia, "https://www.nokia.com/about-us/news/"),
    (CrawlerHuawei, "https://carrier.huawei.com/en/insights"),
]


@pytest.mark.parametrize("cls,url", CRAWLERS_UNDER_TEST)
@resp_lib.activate
def test_crawler_returns_list_on_200(cls, url):
    resp_lib.add(resp_lib.GET, url, body="<html><body></body></html>", status=200)
    items = cls().crawl()
    assert isinstance(items, list)


@pytest.mark.parametrize("cls,url", CRAWLERS_UNDER_TEST)
@resp_lib.activate
def test_crawler_returns_empty_on_500(cls, url):
    resp_lib.add(resp_lib.GET, url, status=500)
    items = cls().crawl()
    assert items == []


@resp_lib.activate
def test_ericsson_parses_article():
    resp_lib.add(
        resp_lib.GET,
        "https://www.ericsson.com/en/blog/tags/core-network",
        body="""
        <html><body>
          <div class="card">
            <h3><a href="/en/blog/2026/5gc-evolution">5GC Evolution with NWDAF</a></h3>
            <p>Network automation via AI/ML in 5G Core.</p>
          </div>
        </body></html>
        """,
        status=200,
    )
    items = CrawlerEricsson().crawl()
    assert len(items) == 1
    assert items[0].source == "ericsson"
    assert items[0].topic in ("5GC", "Autonomous", "IMS", "EPC", "General")


RSS_BODY = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>Feed</title>
  <item>
    <title>5G Autonomous Networks</title>
    <link>https://example.com/news/5g-autonomous</link>
    <description><![CDATA[<p>Self-managing networks with ZSM.</p>]]></description>
    <pubDate>Wed, 10 Jun 2026 08:30:00 +0000</pubDate>
  </item>
  <item>
    <title>5GC NWDAF analytics</title>
    <link>https://example.com/news/nwdaf</link>
    <description>AI/ML analytics in the 5G Core.</description>
    <pubDate>Mon, 22 Jun 2026 10:00:00 +0000</pubDate>
  </item>
</channel></rss>"""


@resp_lib.activate
def test_gsma_parses_rss_with_publish_dates():
    resp_lib.add(resp_lib.GET, CrawlerGSMA.FEED_URL, body=RSS_BODY, status=200)
    items = CrawlerGSMA().crawl()
    assert len(items) == 2
    assert items[0].source == "gsma"
    assert items[0].title == "5G Autonomous Networks"
    assert items[0].date == "2026-06-10 08:30:00"
    assert "Self-managing" in items[0].content  # HTML trong description được bóc sạch
    assert items[1].date == "2026-06-22 10:00:00"


@resp_lib.activate
def test_3gpp_rss_topic_detection():
    resp_lib.add(resp_lib.GET, Crawler3GPP.FEED_URL, body=RSS_BODY, status=200)
    items = Crawler3GPP().crawl()
    assert items[1].topic == "5GC"


@resp_lib.activate
def test_rss_crawler_returns_empty_on_invalid_xml():
    resp_lib.add(resp_lib.GET, CrawlerETSI.FEED_URL, body="not xml at all <<<", status=200)
    assert CrawlerETSI().crawl() == []


@resp_lib.activate
def test_nokia_parses_multiple_articles():
    resp_lib.add(
        resp_lib.GET,
        "https://www.nokia.com/about-us/news/",
        body="""
        <html><body>
          <article>
            <h3><a href="/news/ims-rcs">IMS Rich Communications</a></h3>
            <p>RCS and VoLTE advancements.</p>
          </article>
          <article>
            <h2><a href="/news/epc-evolution">EPC Evolution</a></h2>
            <p>Core network migration path.</p>
          </article>
        </body></html>
        """,
        status=200,
    )
    items = CrawlerNokia().crawl()
    assert len(items) == 2
    assert items[0].source == "nokia"
    assert items[1].source == "nokia"
