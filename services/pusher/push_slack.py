#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Subscribe analysis topic → filter by impact_score → post to Slack
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests
from confluent_kafka import Consumer
from dotenv import load_dotenv

# ───── 环境变量 ────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]          # MarketPulse/
load_dotenv()                                       # 读取 .env

BROKER        = "localhost:9092"
TOPIC         = "analysis"
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")
THRESHOLD     = 0.7                                 # 推送阈值

if not SLACK_WEBHOOK:
    sys.exit("❌  SLACK_WEBHOOK 未设置，请在 .env 中配置后再运行")

# ───── Kafka Consumer ─────────────────────────────────────────
consumer = Consumer(
    {
        "bootstrap.servers": BROKER,
        "group.id": "pusher",
        "auto.offset.reset": "earliest",
    }
)
consumer.subscribe([TOPIC])


# ───── 帮助函数 ────────────────────────────────────────────────
def to_dict(val) -> dict:
    """analysis 可能是字符串，也可能已是 dict"""
    return json.loads(val) if isinstance(val, str) else val


def to_score(val) -> float:
    """把字符串/10分制/百分制统一变成 0–1"""
    if isinstance(val, str):
        val = float(val)
    if val > 1:
        val = val / 10 if val <= 10 else val / 100
    return round(float(val), 4)


def post_slack(text: str) -> None:
    resp = requests.post(SLACK_WEBHOOK, json={"text": text}, timeout=10)
    if resp.status_code >= 300:
        print("⚠️  Slack 返回非 2xx：", resp.status_code, resp.text)


def format_msg(evt: dict) -> str:
    a = evt["analysis"]
    return (
        f"*{evt['headline']}* _(score {a['impact_score']:.2f})_\n"
        f"• 宏观: {a['macro_view']}\n"
        f"• 行业: {a['industry_view']}\n"
        f"• 同业: {a['peer_comparison']}\n"
        f"• 技术面: {a['technical_view']}\n"
        f"<{evt.get('url', '')}>"
    )


# ───── 主循环 ─────────────────────────────────────────────────
print("🚀  Slack-pusher started, waiting for messages…")

while True:
    msg = consumer.poll(1.0)
    if msg is None or msg.error():
        continue

    evt = json.loads(msg.value().decode())

    # 保证 analysis 为字典 & 分数为 float
    evt["analysis"] = to_dict(evt["analysis"])
    evt["analysis"]["impact_score"] = to_score(evt["analysis"]["impact_score"])

    if evt["analysis"]["impact_score"] >= THRESHOLD:
        post_slack(format_msg(evt))
        print("→ pushed to Slack:", evt["headline"][:60])
