import logging
import os
import signal
import sys
from datetime import datetime

from agent.bot.commands import handle_post
from agent.bot.rest_client import NetchatRestClient
from agent.bot.websocket_client import NetchatWebSocketClient
from agent.crawler import run_all_crawlers
from agent.llm.claude_client import generate_report
from agent.scheduler import init_scheduler, stop as stop_scheduler
from agent.storage.database import get_recent_items, init_db, save_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def crawl_and_report(rest_client: NetchatRestClient) -> None:
    logger.info("Starting scheduled crawl+report")
    try:
        new_count = run_all_crawlers()
        logger.info(f"Crawl complete: {new_count} new items")
        items = get_recent_items(days=7)
        if not items:
            logger.info("No items in last 7 days, skipping report")
            return
        week_label = datetime.now().strftime("Tuần %W/%Y")
        report = generate_report(items, week_label)
        channel_id = rest_client.get_channel_id()
        save_report("scheduled", report, channel_id)
        rest_client.post_message(report, channel_id)
        logger.info("Scheduled report sent")
    except Exception as e:
        # Không để job chết âm thầm: log đầy đủ traceback + báo ngắn cho người dùng
        logger.exception("Scheduled crawl+report failed")
        try:
            rest_client.post_message(
                f"⚠️ Báo cáo theo lịch gặp lỗi ({type(e).__name__}). "
                "Bot sẽ tự chạy lại vào lịch kế tiếp; bạn có thể thử `!report` sau ít phút.",
                rest_client.get_channel_id(),
            )
        except Exception:
            logger.exception("Không gửi được thông báo lỗi cho người dùng")


def main() -> None:
    init_db()
    logger.info("Database initialized")

    rest_client = NetchatRestClient()
    ws_client = NetchatWebSocketClient(
        on_post_callback=lambda post, event_data: handle_post(post, rest_client, event_data)
    )

    scheduler = init_scheduler(lambda: crawl_and_report(rest_client))

    def shutdown(signum, frame):
        logger.info("Shutting down...")
        stop_scheduler()
        ws_client.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    ws_client.start()
    logger.info("Bot ready — listening on Netchat")

    # Keep main thread alive
    import time
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
