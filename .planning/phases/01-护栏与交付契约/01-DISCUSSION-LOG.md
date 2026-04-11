# Phase 1: 护栏与交付契约 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-11
**Phase:** 1-护栏与交付契约
**Areas discussed:** 回归测试包边界, 内容可触达校验口径, 新增内容批次验收清单格式, 测试执行入口与开发者体验

---

## 回归测试包边界

| Option | Description | Selected |
|--------|-------------|----------|
| 关键链路最小集 | session 菜单模式、跨幕推进、reward generate/apply、effect queue/hook 时序、save/load round-trip | ✓ |
| 更窄 | 只补当前已知最脆弱的 session/reward/save-load | |
| 更宽 | 把 Textual 展示、map 坏输入、inspect/potion 混合路径也纳入 Phase 1 必跑 | |

**User's choice:** 关键链路最小集。
**Notes:** 用户选择 `1A`。

| Option | Description | Selected |
|--------|-------------|----------|
| 固定 seed 的短路径 smoke | 覆盖跨幕/奖励/存读档关键节点，但不追求全三幕通关，三幕闭环留给 Phase 2 | ✓ |
| 不增加 E2E | 只做单元/集成测试，不在 Phase 1 增加 E2E | |
| 提前三幕 smoke | 即使 Act 3 还要用测试入口或构造状态辅助 | |

**User's choice:** 固定 seed 的短路径 smoke。
**Notes:** 用户选择 `2A`。

| Option | Description | Selected |
|--------|-------------|----------|
| 时序契约 | queue tail 顺序、hook 入队顺序、dead target noop、combat end 触发顺序 | ✓ |
| 卡牌效果覆盖 | 按 Ironclad 已有复杂卡逐张补更多断言 | |
| 状态序列化覆盖 | 优先保证 effect queue/save-load round-trip，不深挖效果细节 | |

**User's choice:** 时序契约。
**Notes:** 用户选择 `3A`。

| Option | Description | Selected |
|--------|-------------|----------|
| pytest marker 或集中测试文件 | 便于 `uv run pytest ...` 跑护栏子集 | ✓ |
| 只靠现有目录测试命令 | 不新增标记或集中入口 | |
| 新增脚本/命令 | 包装测试入口 | |

**User's choice:** pytest marker 或集中测试文件。
**Notes:** 用户选择 `4A`。

---

## 内容可触达校验口径

| Option | Description | Selected |
|--------|-------------|----------|
| 分层定义 | 已录入 = registry 能加载；可触达 = 被角色/幕/奖励池/事件池/遭遇池等运行入口引用 | ✓ |
| 宽松定义 | 只要 registry 能加载就算覆盖，触达缺口仅作为备注 | |
| 严格定义 | 必须能通过菜单或固定 seed 实际走到，才算可触达 | |

**User's choice:** 分层定义。
**Notes:** 用户说“全按你的推荐”。

| Option | Description | Selected |
|--------|-------------|----------|
| 单独列出并默认失败 | 凡进入随机奖励池的 placeholder 都让校验失败；不在随机池的 placeholder 只列报告 | ✓ |
| 只列报告 | 不让测试失败 | |
| 任何 placeholder 都失败 | 即使它只在特殊/事件池中暂存 | |

**User's choice:** 单独列出并默认失败。
**Notes:** 用户说“全按你的推荐”。

| Option | Description | Selected |
|--------|-------------|----------|
| 按内容类型各自检查 | 卡牌查角色奖励池，遗物查标准/boss/shop/event/Neow 等池，药水查 potion pool，敌人/事件查 act pool | ✓ |
| 先只查遗物和卡牌 | 敌人/事件/药水留给后续阶段 | |
| 只检查 Phase 1 已知风险 | placeholder relic 与 reward generator 使用的池 | |

**User's choice:** 按内容类型各自检查。
**Notes:** 用户说“全按你的推荐”。

| Option | Description | Selected |
|--------|-------------|----------|
| pytest 断言 + 可读摘要 | 测试失败给最小缺口列表，另有 helper/report 文本便于人工看“已录入 vs 可触达” | ✓ |
| 纯 pytest 断言 | 不额外输出报告 | |
| Markdown/JSON 报告为主 | pytest 只确认报告存在/可生成 | |

**User's choice:** pytest 断言 + 可读摘要。
**Notes:** 用户说“全按你的推荐”。

---

## 新增内容批次验收清单格式

| Option | Description | Selected |
|--------|-------------|----------|
| README 模板 + 测试守护 | README 写开发者清单，测试验证关键事实，避免清单变成没人看的文档 | ✓ |
| 只放 README | 不新增专门测试约束 | |
| 独立模板 | 新增独立 `.planning` 或 `docs` 模板，每批开发时复制填写 | |

**User's choice:** README 模板 + 测试守护。
**Notes:** 用户说“全按推荐”。

| Option | Description | Selected |
|--------|-------------|----------|
| 全链路最小项 | `content/`、registry/content validation、domain/use case、session route、presentation/Textual、README | ✓ |
| 只覆盖代码和测试 | 不要求 README | |
| 动态覆盖 | 按内容类型动态覆盖，先不强制 presentation/Textual | |

**User's choice:** 全链路最小项。
**Notes:** 用户说“全按推荐”。

| Option | Description | Selected |
|--------|-------------|----------|
| 关键入口缺失即失败 | 内容 JSON 已加但 registry 校验、触达池、应用链路或玩家反馈缺任一关键项，就视为未交付 | ✓ |
| 加载通过即可 | 允许后续补展示/README | |
| 实现者自行定义 | 失败标准由实现者在每个 plan 里自行定义 | |

**User's choice:** 关键入口缺失即失败。
**Notes:** 用户说“全按推荐”。

| Option | Description | Selected |
|--------|-------------|----------|
| 必须明确 | 新增 placeholder 必须有 `implementation_status`、不进入随机投放池，且 README/报告可见 | ✓ |
| 只要求遗物 | 卡牌/事件暂不要求 | |
| 不在清单里管 | 交给内容校验报告处理 | |

**User's choice:** 必须明确。
**Notes:** 用户说“全按推荐”。

---

## 测试执行入口与开发者体验

| Option | Description | Selected |
|--------|-------------|----------|
| pytest marker + README 命令 | 例如给护栏测试加 `guardrail` marker，并在 README 记录 `uv run pytest -m guardrail` | ✓ |
| 集中测试文件即可 | 不加 marker | |
| 新增脚本/命令 | 包装所有检查 | |

**User's choice:** pytest marker + README 命令。
**Notes:** 用户说“按推荐”。

| Option | Description | Selected |
|--------|-------------|----------|
| 开发者定位 | 失败消息直接列缺口 ID、内容类型、池/入口、建议检查文件 | ✓ |
| 审核视角 | 输出更像覆盖率报告，强调百分比和汇总 | |
| CI 视角 | 尽量短，只给失败断言和测试名 | |

**User's choice:** 开发者定位。
**Notes:** 用户说“按推荐”。

| Option | Description | Selected |
|--------|-------------|----------|
| 不引入 | Phase 1 关注关键链路行为，不用行覆盖率制造噪音 | ✓ |
| 引入低阈值 | 作为基线 | |
| 只统计 guardrail | 只对新增 guardrail 测试文件统计覆盖率 | |

**User's choice:** 不引入。
**Notes:** 用户说“按推荐”。

| Option | Description | Selected |
|--------|-------------|----------|
| 命令 + 适用场景 + 失败解释 | 说明什么时候跑 guardrail、失败代表什么、内容批次怎么用清单 | ✓ |
| 只列命令 | 细节留给测试失败消息 | |
| 完整流程文档 | 包括每类内容的详细手工验收步骤 | |

**User's choice:** 命令 + 适用场景 + 失败解释。
**Notes:** 用户说“按推荐”。

## the agent's Discretion

- pytest marker 的具体命名、集中测试文件拆分、helper/report 的内部实现结构由 planner/researcher 根据现有测试布局决定。
- 固定 seed 短路径 smoke 的具体 seed 和构造方式可由实现阶段选择。

## Deferred Ideas

- None.
