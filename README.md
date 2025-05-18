# 📰 MarketPulse

**MarketPulse** 是一个自动化的市场新闻分析与推送系统。它通过拉取财经新闻、使用大模型进行分析，并将高影响力事件推送到 Slack，从而帮助用户快速把握市场动态。

---

## 📦 项目结构

```bash
.
├── configs/           # 全局配置文件（如 app.yml，prompt 模板）
├── infrastructure/    # 包含 Kafka、PostgreSQL 的 Docker 部署配置
├── scripts/           # 启动脚本与健康检查脚本
├── services/          # 三个核心服务：fetcher, analyzer, pusher
├── docker-compose.yml # 主服务组合配置
└── README.md          # 项目说明
```

---

## ⚙️ 功能介绍

### ✅ fetcher – 新闻获取

- 使用 [NewsAPI](https://newsapi.org) 拉取最新商业新闻
- 从标题中提取股票代码
- 将原始新闻事件推送到 Kafka 的 `raw-events` topic

### 🧠 analyzer – LLM 分析器

- 消费 Kafka 中的原始新闻
- 使用 OpenAI GPT 分析新闻内容：
  - 宏观视角（macro）
  - 行业影响（industry）
  - 同业比较（peer）
  - 技术面观点（technical）
  - 影响评分（impact_score）
- 将结果存入 PostgreSQL，并产出分析消息到 Kafka 的 `analysis` topic

### 🔔 pusher – Slack 推送器

- 监听分析结果（Kafka topic: `analysis`）
- 过滤高影响力事件（评分阈值 ≥ 0.7）
- 以格式化信息推送到 Slack webhook

---

## 🚀 快速开始

### 1. 配置 `.env`

在根目录添加 `.env` 文件：

```env
NEWS_API_KEY=your_newsapi_key
SLACK_WEBHOOK=https://hooks.slack.com/services/your/slack/webhook
PGHOST=localhost
PGUSER=postgres
PGPASSWORD=postgres
PGDATABASE=marketpulse
```

### 2. 启动服务

```bash
# 启动 Kafka + Postgres
docker-compose -f docker-compose.yml -f infrastructure/kafka/docker-compose.yml up -d
docker-compose -f infrastructure/postgres/docker-compose.yml up -d

# 初始化数据库（可选）
psql -h localhost -U postgres -d marketpulse -f infrastructure/postgres/init.sql

# 本地启动各服务
bash scripts/start_local.sh
```

---

## 🧪 技术栈

- **数据流处理**：Kafka
- **模型分析**：OpenAI Chat API
- **数据存储**：PostgreSQL
- **外部服务**：NewsAPI、Slack Webhook
- **环境管理**：dotenv + YAML
- **语言**：Python 3

---

## 📊 数据流图

```
[NewsAPI]
    ↓
 [fetcher] ───> Kafka (raw-events)
                          ↓
                     [analyzer] ─→ PostgreSQL
                          ↓
                     Kafka (analysis)
                          ↓
                       [pusher]
                          ↓
                       Slack
```

---

## 📝 配置说明

### `configs/app.yml`

配置使用的 LLM 模型（如 `gpt-4`, `gpt-3.5-turbo`）：

```yaml
openai:
  model: gpt-3.5-turbo
```

### `configs/prompts/earnings_analysis.json`

系统提示词，用于指导分析方向。

---

## 📈 数据表结构

### `raw_events`

| 字段名        | 类型       | 描述            |
|---------------|------------|-----------------|
| id            | serial     | 主键            |
| symbol        | text       | 股票代码        |
| event_type    | text       | 类型（如 NEWS） |
| headline      | text       | 新闻标题        |
| published_at  | timestamp  | 发布时间        |
| raw_text      | text       | 原始内容        |
| source        | text       | 来源            |
| meta          | JSONB      | 附加字段        |

### `analysis`

| 字段名         | 类型      | 描述                 |
|----------------|-----------|----------------------|
| id             | serial    | 主键                 |
| event_id       | int       | 外键（raw_events）   |
| macro_view     | text      | 宏观分析             |
| industry_view  | text      | 行业分析             |
| peer_compare   | text      | 同行业比较           |
| technical_view | text      | 技术面分析           |
| impact_score   | float     | 影响分数（0–1）      |

---

## 🧹 TODO / 未来优化方向

- [ ] 支持更多新闻源（如Reuters, Twitter, RSS），以及支持兼容不同格式的信息
- [ ] 提供 Web Dashboard
- [ ] 增强Multi Agent协作，以应对更加专业、复杂得行研、投资分析需求等
- [ ] 多语言支持

---

