# Phase 1: 护栏与交付契约 - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 建立后续批量开发的验证护栏和交付契约，不补新角色、卡牌、事件、敌人或三幕主线能力本身。交付范围是让开发者可以稳定验证 session 菜单模式、跨幕推进、reward generate/apply、effect 时序、save/load round-trip，以及内容“已录入”和“可触达”的差异。

</domain>

<decisions>
## Implementation Decisions

### 回归测试包边界
- **D-01:** Phase 1 的必跑护栏采用关键链路最小集，覆盖 session 菜单模式、跨幕推进、reward generate/apply、effect queue/hook 时序和 save/load round-trip。
- **D-02:** E2E 只要求固定 seed 的短路径 smoke，覆盖跨幕、奖励和存读档关键节点；不在 Phase 1 提前追求完整三幕通关，完整 Act 1 -> Act 3 -> Boss Chest -> Victory 留给 Phase 2。
- **D-03:** `effect_resolver.py` 护栏重点是时序契约，包括 queue tail 顺序、hook 入队顺序、dead target noop 和 combat end 触发顺序；不要把 Phase 1 扩成逐张卡牌效果补全。
- **D-04:** 回归护栏要能用 `pytest` 子集运行，优先通过 marker 或集中测试文件组织。

### 内容可触达校验口径
- **D-05:** “已录入”定义为 registry 能加载；“可触达”定义为被角色、幕、奖励池、事件池、遭遇池等运行入口引用。
- **D-06:** placeholder 遗物单独列出；凡进入随机奖励池的 placeholder 都应让校验失败，不在随机池的 placeholder 只列入报告。
- **D-07:** 未接入奖励池/运行入口的判定要按内容类型检查：卡牌查角色奖励池，遗物查 standard/boss/shop/event/Neow 等池，药水查 potion pool，敌人和事件查 act pool。
- **D-08:** 校验输出采用 pytest 断言 + 可读摘要。测试失败给最小缺口列表，helper/report 文本便于人工区分“已录入 vs 可触达”。

### 新增内容批次验收清单格式
- **D-09:** 验收清单采用 README 模板 + 测试守护：README 写开发者清单，测试验证关键事实，避免清单变成无人维护的独立文档。
- **D-10:** 每批新增内容的清单覆盖全链路最小项：`content/`、registry/content validation、domain/use case、session route、presentation/Textual、README。
- **D-11:** 关键入口缺失即视为未交付。内容 JSON 已新增但 registry 校验、触达池、应用链路或玩家反馈缺任一关键项，不能算完成。
- **D-12:** 新增 placeholder 必须明确策略：有 `implementation_status`，不进入随机投放池，并且在 README 或覆盖报告中可见。

### 测试执行入口与开发者体验
- **D-13:** 护栏测试入口使用 pytest marker + README 命令，例如 `uv run pytest -m guardrail`。
- **D-14:** 失败输出优先服务开发者定位，直接列出缺口 ID、内容类型、池/入口和建议检查文件。
- **D-15:** Phase 1 不引入 coverage 百分比阈值，避免用行覆盖率制造噪音；重点是关键链路行为。
- **D-16:** README 需要记录 guardrail 命令、适用场景、失败含义，以及内容批次如何使用验收清单。

### the agent's Discretion
- pytest marker 的具体命名、集中测试文件拆分、helper/report 的内部实现结构由 planner/researcher 根据现有测试布局决定。
- 固定 seed 短路径 smoke 的具体 seed 和构造方式可由实现阶段选择，但不得扩大为完整三幕主线交付。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` — Phase 1 goal, success criteria, and dependency boundary.
- `.planning/REQUIREMENTS.md` — `GUARD-01`, `GUARD-02`, `GUARD-03` definitions and roadmap traceability.
- `.planning/PROJECT.md` — project constraints: Python/Textual/Rich TUI boundary, content source, persistence and testing expectations.

### Codebase constraints
- `.planning/codebase/TESTING.md` — current pytest layout, existing test types, and command conventions.
- `.planning/codebase/CONCERNS.md` — fragile areas around `session.py`, `effect_resolver.py`, map bad input, and UI observability.
- `.planning/codebase/STRUCTURE.md` — source/test directory responsibilities and where guardrail work should connect.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/app/test_session.py` — existing session/menu route assertions; useful for Phase 1 session menu guardrails.
- `tests/use_cases/test_apply_reward.py` — existing reward generate/apply coverage, including boss rewards, combat rewards, relic interactions and pool behavior.
- `tests/domain/test_effect_resolver.py` — existing effect queue and hook ordering assertions; natural place to extend timing contract guardrails.
- `tests/use_cases/test_save_load.py` — existing save/load schema and round-trip coverage.
- `tests/content/test_registry_validation.py` — existing registry/content validation and `implementation_status` checks; likely base for reachable-vs-loaded checks.
- `tests/e2e/test_single_act_smoke.py` and `tests/e2e/test_two_act_smoke.py` — existing smoke patterns for fixed-path session flows.

### Established Patterns
- Tests use `pytest`, module-local helper factories, direct domain/use case objects, and `tmp_path` for file persistence.
- Python commands should run through `uv`, consistent with README and project instructions.
- Existing coverage is behavior-driven; there is no configured coverage threshold, and Phase 1 should not add one.

### Integration Points
- Content truth source is root `content/`; do not hand-edit `src/slay_the_spire/data/content/`.
- Runtime content loading goes through `src/slay_the_spire/content/` registries and provider.
- Reward generation/application connects through `src/slay_the_spire/domain/rewards/reward_generator.py` and `src/slay_the_spire/use_cases/apply_reward.py`.
- Session route guardrails connect through `src/slay_the_spire/app/session.py` and menu definitions.
- README must be updated with the guardrail command, applicability, failure interpretation and batch acceptance checklist.

</code_context>

<specifics>
## Specific Ideas

- Use `uv run pytest -m guardrail` as the documented guardrail command shape.
- Guardrail failures should name the exact missing content ID, content type, pool/entry point and likely file to inspect.
- The coverage report should distinguish “registry loads it” from “runtime can reach it”; these are not equivalent.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 1 scope.

</deferred>

---

*Phase: 01-护栏与交付契约*
*Context gathered: 2026-04-11*
