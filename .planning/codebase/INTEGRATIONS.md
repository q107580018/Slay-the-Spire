# External Integrations

**Analysis Date:** 2026-04-11

## APIs & External Services

**Runtime External API:**
- Not detected - 运行时代码未发现 HTTP SDK 或第三方 API 客户端依赖，见 `pyproject.toml`、`src/slay_the_spire/`
  - SDK/Client: Not applicable
  - Auth: Not applicable

**CLI/Local Tooling:**
- `uv` - 仅用于本地依赖与命令执行，不是应用运行期外部服务，见 `README.md`
  - SDK/Client: `uv` CLI
  - Auth: Not required

## Data Storage

**Databases:**
- Not detected（无 RDBMS/NoSQL 连接）
  - Connection: Not applicable
  - Client: Not applicable

**File Storage:**
- Local filesystem only
  - 内容读取：`content/`（开发真源）与打包内容目录，见 `src/slay_the_spire/content/provider.py`、`src/slay_the_spire/build_content.py`
  - 存档读写：JSON 文件，见 `src/slay_the_spire/adapters/persistence/save_files.py`

**Caching:**
- None（未检测到 Redis/Memory cache 层）

## Authentication & Identity

**Auth Provider:**
- Custom: None（本地单机，无登录体系）
  - Implementation: Not applicable

## Monitoring & Observability

**Error Tracking:**
- None（未检测到 Sentry 等错误追踪）

**Logs:**
- 交互日志显示在 TUI 组件内（`RichLog`），无外部日志聚合，见 `src/slay_the_spire/adapters/textual/slay_app.py`

## CI/CD & Deployment

**Hosting:**
- 本地运行（CLI/TUI），非云托管服务，见 `README.md`

**CI Pipeline:**
- Not detected（仓库未检测到 `.github/workflows/`）

## Environment Configuration

**Required env vars:**
- None detected（运行通过 CLI 参数配置，见 `src/slay_the_spire/app/cli.py`）

**Secrets location:**
- Not applicable（仓库当前无外部服务凭据依赖）

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

---

*Integration audit: 2026-04-11*
