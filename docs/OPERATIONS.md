# 部署与运维

## 服务

- `web`：Nginx托管React并反向代理API。
- `api`：FastAPI同步业务接口。
- `worker`：Celery处理导入、PDF、爬虫和长任务。
- `postgres`：业务事实来源。
- `redis`：任务代理和结果后端。
- `migrate`：一次性执行迁移与脱敏演示种子。

## 健康与排障

```bash
docker compose ps
docker compose logs api worker
curl http://localhost:8080/health
```

任务失败时批次进入 `task_failed`，不得静默跳过。先检查Worker日志、源文件和外部接口，再由经办人重试校验。

## 备份恢复

生产备份必须同时包含 PostgreSQL 和文件卷，并定期做恢复演练。数据库恢复后校验 `stored_files.sha256` 与文件卷内容；Redis不作为业务事实来源，无需用于长期恢复。

升级步骤：备份 → 拉取版本 → `docker compose build` → `alembic upgrade head` → 启动 → 健康检查 → 核心流程冒烟。失败时回滚应用镜像和数据库备份，不能只回滚代码而保留不兼容结构。
