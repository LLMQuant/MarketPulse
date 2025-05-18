import os, json, time, re, logging, sys
import requests
from confluent_kafka import Producer
from dotenv import load_dotenv

# ── 基础设置 ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    stream=sys.stdout,
)

load_dotenv()                            # 读取 .env

NEWS_API     = os.getenv("NEWS_API_KEY")
BROKER       = "localhost:9092"
TOPIC        = "raw-events"
TICKER_REGEX = re.compile(r"\b[A-Z]{2,5}\b")  # MVP：粗暴提取股票代码

if not NEWS_API:
    logging.error("环境变量 NEWS_API_KEY 未设置，立即退出")
    sys.exit(1)

producer = Producer({"bootstrap.servers": BROKER})

# ── 主要逻辑 ────────────────────────────────────────────────────────
def fetch_news():
    url = (
        "https://newsapi.org/v2/top-headlines?"
        f"category=business&pageSize=20&language=en&apiKey={NEWS_API}"
    )
    logging.debug("GET %s", url)
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()
    except Exception as exc:
        logging.exception("拉取 NewsAPI 失败: %s", exc)
        return

    articles = data.get("articles", [])
    logging.info("获取到 %d 篇新闻", len(articles))

    for a in articles:
        symbol = TICKER_REGEX.findall(a["title"])[:1] or ["SPY"]
        evt = dict(
            symbol=symbol[0],
            event_type="NEWS",
            headline=a["title"],
            published_at=a["publishedAt"],
            raw_text=a.get("description") or "",
            source=a["source"]["name"],
            meta={},
        )
        try:
            producer.produce(TOPIC, json.dumps(evt).encode())
        except BufferError:
            logging.warning("Kafka 缓冲区已满，先 flush 再重试")
            producer.flush()
            producer.produce(TOPIC, json.dumps(evt).encode())

    producer.flush()
    logging.info("已推送 %d 条消息到 Kafka", len(articles))


if __name__ == "__main__":
    logging.info("开始循环拉取新闻，每 60 秒一次 …")
    while True:
        fetch_news()
        time.sleep(60)
