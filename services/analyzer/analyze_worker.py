#!/usr/bin/env python
# services/analyzer/analyze_worker.py
from __future__ import annotations
import json, os, yaml
from pathlib import Path
import psycopg2
from confluent_kafka import Consumer, Producer
from openai import OpenAI
from dotenv import load_dotenv

# ───── 环境 & 配置 ───────────────────────────────────────────────
load_dotenv()
ROOT      = Path(__file__).resolve().parents[2]
cfg       = yaml.safe_load((ROOT / "configs/app.yml").read_text())
MODEL     = cfg.get("openai", {}).get("model", "gpt-3.5-turbo")

# ───── 连接 ─────────────────────────────────────────────────────
BROKER, IN_TOPIC, OUT_TOPIC = "localhost:9092", "raw-events", "analysis"
consumer = Consumer({"bootstrap.servers": BROKER, "group.id": "analyzer", "auto.offset.reset": "earliest"})
consumer.subscribe([IN_TOPIC])
producer = Producer({"bootstrap.servers": BROKER})

conn = psycopg2.connect(
    host=os.getenv("PGHOST"), user=os.getenv("PGUSER"),
    password=os.getenv("PGPASSWORD"), dbname=os.getenv("PGDATABASE"))
cur  = conn.cursor()

client        = OpenAI()
SYSTEM_PROMPT = (ROOT / "configs/prompts/earnings_analysis.json").read_text(encoding="utf-8")

# ───── 辅助函数 ─────────────────────────────────────────────────
def llm_analyze(text: str) -> dict:
    rsp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user",   "content": text}],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    content = rsp.choices[0].message.content
    return json.loads(content) if isinstance(content, str) else content

def to_text(val) -> str:
    """确保入库是字符串；dict→json、None→空串"""
    if val is None:          return ""
    if isinstance(val, str): return val
    return json.dumps(val, ensure_ascii=False)

def to_score(val) -> float:
    """把可能的字符串/百分制/十分制统一压到 0-1 浮点"""
    if isinstance(val, str): val = float(val)
    if val > 1:              val = val / 10 if val <= 10 else val / 100
    return round(float(val), 4)

# ───── 主循环 ───────────────────────────────────────────────────
def handle(msg):
    evt = json.loads(msg.value().decode())
    try:
        analysis = llm_analyze(evt["raw_text"])
    except Exception as e:
        print("❌ LLM 解析失败:", e)
        return

    evt["analysis"] = analysis
    producer.produce(OUT_TOPIC, json.dumps(evt).encode())
    producer.flush()

    # 插 raw_events
    cur.execute(
        """INSERT INTO raw_events
           (symbol,event_type,headline,published_at,raw_text,source,meta)
           VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
        [evt["symbol"], evt["event_type"], evt["headline"],
         evt["published_at"], evt["raw_text"], evt["source"],
         json.dumps(evt.get("meta", {}))])
    event_id = cur.fetchone()[0]

    # 标准化分析字段
    macro   = to_text(analysis.get("macro_view"))
    indus   = to_text(analysis.get("industry_view"))
    peer    = to_text(analysis.get("peer_comparison"))
    tech    = to_text(analysis.get("technical_view"))
    score   = to_score(analysis.get("impact_score", 0))

    # 插 analysis
    cur.execute(
        """INSERT INTO analysis
           (event_id,macro_view,industry_view,peer_compare,technical_view,impact_score)
           VALUES (%s,%s,%s,%s,%s,%s)""",
        [event_id, macro, indus, peer, tech, score])
    conn.commit()

    print(f"✓ analyzed {evt['headline'][:60]}... score={score:.2f}")

def main():
    while True:
        msg = consumer.poll(1.0)
        if msg and not msg.error():
            handle(msg)

if __name__ == "__main__":
    main()
