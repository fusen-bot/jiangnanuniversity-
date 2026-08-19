# 期刊财务智能运营平台

面向单个学术期刊编辑部的企业级作品集应用。系统将审稿费、版面费和作者稿费从分散的 Excel/脚本操作，重构为可校验、可复核、可审批、可审计的统一流程。

> 本仓库只包含模拟和脱敏数据，不代表真实单位生产上线。原 Flask 原型保留在 `backend/` 与 `frontend/`，新版位于 `server/` 与 `web/`。

## 业务闭环

`数据导入 → 规则校验 → 异常复核 → 审批/驳回 → 报表导出 → 审计归档`

- 审稿费：人员匹配、校内外识别、费用计算、缺失和重复检查。
- 版面费：录用、开票、核销、税务信息和进度管理。
- 作者稿费：期刊数据采集、PDF通信作者提取、资格与金额计算。
- 企业协作：四角色RBAC、任务中心、流程评论、文件中心和审计记录。
- AI副驾：DeepSeek + 制度检索 + 授权业务摘要 + 受控工具调用 + 人工确认。

## 技术栈

- React、TypeScript、Vite、Ant Design
- FastAPI、Pydantic、SQLAlchemy、Alembic
- PostgreSQL、Celery、Redis
- DeepSeek API；无密钥时使用确定性 Fake AI 完整体验流程
- Docker Compose、GitHub Actions、pytest、Vitest、Ruff、mypy

## 一键启动

要求 Docker 与 Docker Compose：

```bash
cp .env.enterprise.example .env
docker compose up --build
```

打开 <http://localhost:8080>。第一次启动会执行数据库迁移并写入脱敏演示数据。

| 角色 | 账号 | 演示密码 |
|---|---|---|
| 管理员 | `admin` | `Admin123!` |
| 财务经办人 | `operator` | `Operator123!` |
| 审批人 | `approver` | `Approver123!` |
| 只读人员 | `viewer` | `Viewer123!` |

演示密码只用于本地作品集，生产部署必须删除或修改种子账号，并设置随机的 `JFP_SECRET_KEY`、数据库密码和 HTTPS。

## 本地开发

后端：

```bash
cd server
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

前端：

```bash
cd web
npm install
npm run dev
```

API 文档位于 <http://localhost:8000/docs>。关键配置均使用 `JFP_` 前缀环境变量。

## 质量检查

```bash
cd server && ruff check . && mypy app && pytest
cd web && npm run lint && npm test && npm run build
docker compose config
```

测试覆盖状态机、费用规则、异常复核、密码与脱敏、RBAC/CSRF、AI注入拒绝及知识引用。核心领域与安全服务覆盖率门槛为 80%。

## 文档导航

- [架构与设计决策](DESIGN.md)
- [数据模型](docs/DATA_MODEL.md)
- [API与权限](docs/API_AND_PERMISSIONS.md)
- [AI工程](docs/AI_ENGINEERING.md)
- [安全设计](docs/SECURITY.md)
- [部署与运维](docs/OPERATIONS.md)
- [旧版迁移映射](docs/LEGACY_MIGRATION.md)
- [历史资料接入与隐私边界](docs/REAL_DATA_INTEGRATION.md)

## 已知边界

- 当前是单机构模块化单体，不实现多租户和微服务。
- 期刊网站结构各异，`JournalGateway` 是受控适配层，需要按目标站公开接口/DOM配置解析规则。
- 知识检索使用透明的关键词召回，当前数据规模无需引入向量数据库；当制度文档规模和评测结果证明有必要时再升级混合检索。
- AI 无权直接修改财务记录或审批，只能提供引用充分的建议和待确认任务。

## License

MIT
