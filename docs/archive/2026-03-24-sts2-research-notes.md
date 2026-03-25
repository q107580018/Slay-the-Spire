# Findings & Decisions

## Requirements
- 全面了解 `Slay the Spire 2`，包括游戏机制
- 目标是后续复刻，形式为终端文字版游戏
- 输出需要能直接支持后续方案设计与实现拆分
- 第一版范围收敛为“单人核心爬塔骨架”
- 设计优先级是可扩展性与可维护性，而不是一次性塞入全部 StS2 新机制
- 首个可玩里程碑只做 1 个 Act，但要把系统边界打磨好
- 实现语言选择 `Python`

## Research Findings
- 当前项目目录为空，需要从研究与设计文档开始
- 截至 2026-03-24，`Slay the Spire 2` 已于 2026-03-05 进入 Steam Early Access。
- 官方 FAQ 明确确认的新机制范围包括 `enchantments`、`afflictions`、`Ancients`、`alternate acts`，以及更多角色、卡牌、遗物、药水、敌人和事件。
- Steam 商店页确认支持单人和最多 4 人在线合作，并存在多人专用卡牌与团队联动。
- `Enchantments` 是官方定义的“持续整局 run 的卡牌修饰器”，普通 enchantment 偏小幅强化，稀有 enchantment 可明显改变构筑方向。
- `Quests` 是新的卡牌类型：拿到后满足指定条件，完成时给出高价值奖励。
- `Ancients` 是进入新 Act 时给出的祝福来源，这些祝福以专属强力 relic 的形式出现，用来替代旧作的 boss relic 节点选择。
- `Alternate Acts` 是进入新 Act 时随机二选一的分支版本，不只是换皮，而是替换环境、敌人、事件和 Boss 池。
- `Necrobinder` 是已确认新角色，其机制围绕友方单位 `Osty`、`Doom` 状态和关键词修改展开。
- `Silent` 在续作中确认拥有 `Sly` 机制：被弃掉时会免费自动打出。
- 2024-11 官方开发日志确认了若干 QOL/UI 变化：彩色地图图标、放大点击区、地图手绘路径、增强的顶部信息栏。
- 2026-02 官方 Q&A 确认默认手牌上限仍为 10，当前没有提高上限的方法。
- 2026-03-19 官方 beta patch `v0.100.0` 的设计方向之一是让 `infinites` 更难达成，说明 Early Access 版本仍在快速平衡迭代。
- 媒体 2026-03-17 上手信息提到当前 EA 已可跑完整三幕流程，并有每角色 10 级 Ascension；这是媒体观察，不视为官方设计承诺。

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 先产出“机制研究 + 终端化映射” | 终端版复刻的关键不是像素级还原，而是机制保真 |
| 第一阶段只复刻“官方已确认且系统边界清晰”的规则骨架 | Early Access 内容仍在快速变化，先稳住核心框架更合理 |
| 数值层与单卡层不作为初版对齐目标 | 现阶段平衡补丁频繁，直接抄数值很快会过时 |
| 第一版只做单人核心爬塔，不做 co-op | 先稳定状态机、战斗系统和 run 流程，再谈多人同步 |
| 第一版架构必须为后续接入 Enchantments、Ancients、Alternate Acts 预留扩展点 | 用户明确要求可扩展与可维护 |
| 首个里程碑只做 1 个 Act | 限制内容规模，把精力放在核心抽象和边界设计 |
| 采用“领域模型 + 数据驱动”路线 | 在可维护性、扩展性和实现成本之间最平衡 |
| 实现语言定为 `Python` | 用户最终明确选择；后续用类型标注和测试弥补动态语言约束 |
| 状态拆分为 `RunState` / `ActState` / `RoomState` / `CombatState` | 降低耦合，为存档、扩展新系统和测试提供清晰边界 |
| 战斗内状态变更统一通过 `Effect` 管线执行 | 避免卡牌、敌人、遗物各自直接改状态，降低联动失控风险 |
| 内容定义与规则执行分离 | 卡牌、敌人、事件尽量数据驱动，减少后续内容扩展成本 |
| 使用“90% 数据驱动 + 10% 特例脚本”策略 | 兼顾常规内容扩展效率与少量复杂牌的表达能力 |
| 预留统一 hooks 触发器模型 | 为未来的 relic、status、enchantment、ancient 扩展提供稳定挂点 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| 本地无现成项目文件可沿用 | 先建立规划与研究文档，后续再初始化代码结构 |

## Resources
- 官方 FAQ: https://www.megacrit.com/faq/
- Steam 商店页: https://store.steampowered.com/app/2868840/Slay_the_Spire_2/
- 官方发售公告: https://www.megacrit.com/news/2026-03-05-early-access-launch/
- 官方发售日公告: https://www.megacrit.com/news/2026-02-19-release-date-trailer/
- 官方 Neowsletter（Map/QOL）: https://www.megacrit.com/news/2024-11-07-neowsletter-issue-4/
- 官方 Neowsletter（Enchantments）: https://www.megacrit.com/news/2025-2-12-neowsletter-issue-7/
- 官方 Neowsletter（Quests）: https://www.megacrit.com/news/2025-3-12-neowsletter-issue-8/
- 官方 Neowsletter（Alternate Acts）: https://www.megacrit.com/news/2025-9-11-neowsletter-issue-14/
- 官方 Neowsletter（Necrobinder）: https://www.megacrit.com/news/2025-10-16-neowsletter-issue-15/
- 官方 Neowsletter（Ancients）: https://www.megacrit.com/news/2025-11-13-neowsletter-issue-16/
- 官方 Neowsletter（2026-02 Q&A）: https://www.megacrit.com/news/2026-2-16-neowsletter-issue-19/
- Steam 公告与补丁: https://steamcommunity.com/app/2868840/announcements/
- 媒体上手补充参考: https://www.pcgamer.com/games/card-games/slay-the-spire-2-is-bigger-better-and-more-complicated-than-the-original-in-the-best-way/

## Visual/Browser Findings
- 地图界面支持直接画线规划路径，这说明“路线规划”在续作中被更显式地强化。
- `Osty` 在战斗中呈现为场上独立友方实体，而不是抽象层的被动效果。
- `Alternate Acts` 的视觉与敌群差异足够大，说明它更接近“Act 模板切换”而非简单事件换表。
