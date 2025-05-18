#!/usr/bin/env bash
# 一键启动 Kafka + Postgres + 三个服务 (dev mode)
docker compose -f infrastructure/kafka/docker-compose.yml up -d
# 这里可扩展 docker-compose.dev.yml 启动 Postgres、服务容器
echo "✅ Local stack is up. Remember to run the workers in separate terminals."
