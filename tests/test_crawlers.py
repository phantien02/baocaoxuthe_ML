import pytest
import responses as resp_lib
from agent.crawler.source_gsma import CrawlerGSMA
from agent.crawler.source_etsi import CrawlerETSI
from agent.crawler.source_ericsson import CrawlerEricsson
from agent.crawler.source_nokia import CrawlerNokia
from agent.crawler.source_huawei import CrawlerHuawei


CRAWLERS_UNDER_TEST = [
    (CrawlerGSMA, "https://www.gsma.com/solutions-and-impact/technologies/networks/"),
    (CrawlerETSI, "https://www.etsi.org/news-events/news"),
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


@resp_lib.activate
def test_gsma_parses_article():
    resp_lib.add(
        resp_lib.GET,
        "https://www.gsma.com/solutions-and-impact/technologies/networks/",
        body="""
        <html><body>
          <article>
            <h2><a href="/news/5g-autonomous">5G Autonomous Networks</a></h2>
            <p>Self-managing networks with ZSM.</p>
          </article>
        </body></html>
        """,
        status=200,
    )
    items = CrawlerGSMA().crawl()
    assert len(items) == 1
    assert items[0].source == "gsma"
    assert items[0].title == "5G Autonomous Networks"


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
