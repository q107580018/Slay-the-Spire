# Task Plan: Slay the Spire 2 研究与终端文字版复刻方案

## Goal
基于最新公开资料梳理 `Slay the Spire 2` 的已知机制、核心玩法循环与可复刻边界，并产出一份适合终端文字版实现的设计与落地建议。

## Current Phase
Phase 2

## Phases
### Phase 1: Requirements & Discovery
- [x] Understand user intent
- [x] Identify constraints and requirements
- [x] Document findings in findings.md
- **Status:** complete

### Phase 2: Research & Validation
- [x] Verify latest public information about `Slay the Spire 2`
- [x] Distinguish confirmed mechanics from inference/speculation
- [ ] Summarize features relevant to terminal adaptation
- **Status:** in_progress

### Phase 3: Design Direction
- [x] Clarify target scope for the terminal version
- [x] Propose implementation approaches with trade-offs
- [x] Present an initial design for approval
- **Status:** complete

### Phase 4: Planning & Structure
- [ ] Define technical architecture
- [ ] Break the project into implementation phases
- [ ] Document decisions with rationale
- **Status:** in_progress

### Phase 5: Delivery
- [ ] Deliver research summary
- [ ] Deliver recommended next step
- [ ] Keep planning files current
- **Status:** pending

## Key Questions
1. `Slay the Spire 2` 目前哪些机制已被官方明确公开？
2. 终端文字版应优先复刻“战斗规则”还是“地图/事件/卡组成长”全流程？
3. 哪些原作体验依赖视觉表现，必须在终端版中降维重构？

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 先做公开资料研究，再进入复刻设计 | `Slay the Spire 2` 仍属动态信息，先确认已知事实才能避免错设目标 |
| 使用文件化计划记录研究过程 | 任务跨多个步骤，避免上下文丢失 |
| 第一版范围定为“单人核心爬塔骨架” | 控制复杂度，优先保证架构质量 |
| 先产出设计 spec，再进入 implementation plan | 符合设计先行流程，也便于后续审阅与迭代 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| 当前目录为空且不是 Git 仓库 | 1 | 按空项目处理，直接初始化规划文件 |

## Notes
- 研究输出需要明确区分“官方已确认”和“基于演示推断”
- 在进入实现前，需要用户确认终端版的范围与 fidelity
