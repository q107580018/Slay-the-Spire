# Technology Stack

**Project:** Slay the Spire TUI 原版 1 代复刻（brownfield）
**Researched:** 2026-04-11
**Research mode:** Ecosystem（Stack 维度）
**Overall confidence:** HIGH

## Recommended Stack（沿用，不换栈）

### Core Runtime & UI
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.12+ | 主运行时与领域逻辑实现 | 现有代码、模型、use case、测试体系都已围绕 Python 3.12 构建，迁移成本高且无收益。 |
| Textual | `>=8.1.1` | 唯一交互界面（TUI） | 项目边界已明确“默认且唯一界面是 Textual TUI”；现有菜单流、地图、日志面板都已落地。 |
| Rich | `>=14.3.3` | 共享终端渲染层 | 已沉淀在 `adapters/presentation/`，被 Textual 层复用；继续沿用可避免 UI 渲染分叉。 |

### Testing & Tooling
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pytest | `>=8.0` | 单元/集成/E2E 回归 | 现有测试目录和约束已成型（content 校验、session、Textual、save/load）；是补齐原版规则的核心护栏。 |
| uv | repo 现状（见 `uv.lock`） | Python 环境、依赖、命令统一入口 | 仓库与协作规则都要求 Python 工作默认用 `uv`；可保持开发、CI、文档命令一致。 |

### Content & Persistence
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `content/*.json` | N/A | 游戏内容真源（卡牌/遗物/敌人/事件等） | 现有加载器、注册表、测试全部围绕 JSON 内容管线；适合“批量补内容 + 可审阅差异”。 |
| JSON save file | `schema_version = 3` | 本地单机存档（默认 `saves/latest.json`） | 符合“本地单机、可回放”目标；无需引入 DB 或远程状态。 |

## 本地资料入口（实现时应优先使用）

| 资料入口 | 用途 | 何时必须查 |
|---------|------|-----------|
| `docs/reference/` | 原版 1 代卡牌本地参考（开发参考，不参与运行） | 新增/校对卡牌数值、效果文本、类型字段时先查本地参考。 |
| `docs/local_wiki/cards_and_relics.md` | 当前项目已实现内容的本地汇总 | 规划批次、核对“已实现 vs 占位”状态时先查。 |
| `content/` | 唯一运行时内容真源 | 任何玩法补齐都应以这里为编辑入口。 |
| [Slay the Spire Wiki](https://slay-the-spire.fandom.com/wiki/) | 英文外部交叉校验 | 本地资料缺项、触发时机不明确、原版规则存在歧义时再查。 |
| [杀戮尖塔中文 Wiki](https://sts.huijiwiki.com/wiki/) | 中文术语/中英对照校对 | UI 文案、术语命名、卡牌翻译需要统一时查。 |

## 不应引入的技术方向（明确排除）

| 方向 | Why Not |
|------|---------|
| Web 前端栈（React/Vue/Next.js 等） | 与“唯一 Textual TUI 界面”边界冲突；会分散内容复刻主线。 |
| 桌面 GUI（PySide/PyQt/Tk/Kivy 等） | 目标不是图形界面项目，重做 UI 成本远高于收益。 |
| 服务端/API 层（FastAPI/Django/Flask + HTTP） | 产品是本地单机流程，无账号/联机需求，引入后只增加复杂度。 |
| 数据库（PostgreSQL/SQLite/Redis） | 当前 JSON 内容与 JSON 存档已满足需求；数据库会增加迁移、运维和一致性负担。 |
| 外部服务依赖（云存档、排行榜、遥测平台） | AGENTS 约束明确无外部凭据依赖，且不在当前复刻范围。 |
| 消息队列/微服务/分布式组件 | 与单机 TUI 原型规模不匹配，属于过度设计。 |

## Alternatives Considered（保守结论）

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| UI | Textual + Rich | Web/GUI 双轨并行 | 双轨会造成规则实现和测试矩阵翻倍，不利于分批复刻。 |
| Persistence | JSON 文件 | 关系型数据库 | 当前无查询/并发瓶颈，DB 只会引入 schema 迁移成本。 |
| Content source | `content/` JSON | 迁移到 YAML/数据库 CMS | 既有注册表与验证链路基于 JSON，迁移收益不成立。 |
| Python workflow | uv | pip + venv + 手工脚本 | 违背仓库既定协作规则，增加环境漂移风险。 |

## 落地建议（给 roadmap 的栈约束）

1. 后续 phase 的技术目标应写成“扩内容/扩规则/补测试”，而不是“引入新基础设施”。
2. 所有玩法增量都保持在现有分层内：`content -> registries -> domain/use_cases -> session -> textual/presentation`。
3. 每批内容补齐时，至少同步 `content`、对应 use case/domain、以及 `pytest` 回归。
4. 如果出现“需要上 Web/DB/服务端”的提案，默认判定为越界，除非项目边界被明确重定义。

## Confidence

| Topic | Confidence | Notes |
|------|------------|-------|
| 继续沿用 Python/Textual/Rich/pytest/uv | HIGH | 由 `AGENTS.md`、`README.md`、`pyproject.toml`、现有代码结构一致支持。 |
| 继续以 JSON 作为内容与存档核心 | HIGH | 当前内容注册表与 save/load 全链路已按 JSON 实现。 |
| 排除 Web/GUI/服务端/数据库/外部服务 | HIGH | 与项目边界、里程碑目标和现有架构完全一致。 |
| 本地资料与 Wiki 校对触发条件 | MEDIUM-HIGH | 本地入口清晰；具体某条原版细则仍可能需逐条外部核对。 |

## Sources

- `/Users/qiuwen/Documents/Slay-the-Spire/AGENTS.md`
- `/Users/qiuwen/Documents/Slay-the-Spire/README.md`
- `/Users/qiuwen/Documents/Slay-the-Spire/pyproject.toml`
- `/Users/qiuwen/Documents/Slay-the-Spire/.planning/PROJECT.md`
- `/Users/qiuwen/Documents/Slay-the-Spire/.planning/codebase/STACK.md`
- `/Users/qiuwen/Documents/Slay-the-Spire/.planning/codebase/ARCHITECTURE.md`
- `/Users/qiuwen/Documents/Slay-the-Spire/.planning/codebase/CONCERNS.md`
