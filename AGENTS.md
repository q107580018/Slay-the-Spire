# AGENTS

## 文档职责

- `AGENTS.md` 只用于给代理/协作者说明本仓库的协作约束、代码事实入口和修改注意事项。
- 项目介绍、当前功能说明、快速开始、运行命令等面向人类读者的内容放在 `README.md`，不要在这里重复维护。
- 若 `AGENTS.md` 与其他文档冲突，优先以代码和测试为准。

## 项目边界

- 这是一个 Python 3.12 的 `textual` TUI 版《Slay the Spire》原型项目。
- 当前玩法内容与系统基线默认以原版《Slay the Spire》1 代为主。
- 默认且唯一运行界面是基于 `textual` 的 TUI；底层复用共享的 `rich` 展示组件。
- 目标是本地单机、可回放的菜单驱动流程，不是图形界面项目，也不是服务端项目。
- Python 相关环境、依赖管理和命令执行默认都使用 `uv`。

## 代码事实入口

- `pyproject.toml`：包配置、依赖、pytest 配置、脚本入口、打包声明。
- `src/slay_the_spire/app/cli.py`：CLI 入口。
- `src/slay_the_spire/app/session.py`：会话状态、菜单路由、默认路径、跨幕推进。
- `src/slay_the_spire/app/menu_definitions.py`：编号菜单定义。
- `src/slay_the_spire/adapters/presentation/`：共享终端展示/渲染、inspect、combat/non-combat 屏幕。
- `src/slay_the_spire/adapters/textual/`：Textual 入口、地图组件、日志和交互面板。
- `src/slay_the_spire/adapters/persistence/save_files.py`：JSON 存档读写。
- `src/slay_the_spire/content/`：内容加载与注册表。
- `src/slay_the_spire/domain/`：战斗、状态模型、Hook、地图生成、奖励生成等领域逻辑。
- `src/slay_the_spire/use_cases/`：开始游戏、出牌、结束回合、进房间、事件、商店、休息、奖励、存读档等用例。
- `content/`：唯一内容真源，开发时编辑的内容 JSON。
- `src/slay_the_spire/data/content/`：构建 wheel 时临时生成的包内内容 JSON。
- `tests/`：UI、内容校验、领域逻辑、存档和 E2E 测试。

## 协作规则

- 默认优先相信 `src/slay_the_spire/app/session.py`、`tests/` 和 `content/`，不要优先相信旧设计文档。
- 面向玩家的菜单、事件、奖励、效果说明等 UI 文案默认统一写中文；代码标识、命令、路径和必要专有名词可保留原文。
- 做设计取舍时，如果 1 代、2 代资料或旧设计文档冲突，默认以“当前代码中的 1 代内容基线 + 已落地行为”优先；只有需求明确指定时才转向 2 代。
- 若需要参考原版资料，优先查询官方社区 Wiki：[Slay the Spire Wiki](https://slay-the-spire.fandom.com/wiki/)。
- 中文卡牌中英对照与术语校对优先参考：[杀戮尖塔中文 Wiki](https://sts.huijiwiki.com/wiki/) 需要用tvly skill访问。

## 修改约束

- 修改内容 JSON 时，只改根目录 `content/`。
- 默认运行优先读取根目录 `content/`；`src/slay_the_spire/data/content/` 仅在构建 wheel 时临时生成，不应手工维护。
- 当前存档 `schema_version` 是 `2`；如果改动存档结构，要同步处理 `save_game.py`、`load_game.py` 和相关测试。
- 当前开发阶段默认不需要兼容旧存档或旧菜单状态；若重构需要删除旧分支，可直接清理，除非需求明确要求兼容。
- 仓库当前没有 `.env` / `.env.example`，也没有外部服务凭据依赖。
- 存档文件默认写入 `saves/latest.json`；用户已明确说明：存档不需要提交。

## 变更联动检查

- 新增房间类型前，先确认地图内容、use case / session 路由、共享展示层 / Textual 展示三层都补齐。
- 调整 Boss 奖励或跨幕流程时，同时检查 `boss -> boss_chest -> 下一幕 / victory` 这条完整链路。
- 新增角色、卡牌、敌人、事件、遗物或药水时，同时检查内容注册表、掉落入口和对应测试。
- 新增战斗后奖励或 Boss 奖励时，同时检查 `src/slay_the_spire/domain/rewards/reward_generator.py`、`src/slay_the_spire/use_cases/apply_reward.py` 和对应测试。
- 修改菜单、渲染或会话路由时，优先检查 `tests/adapters/presentation/` 和 `tests/e2e/`。
- 修改 Textual UI 时，优先检查 `tests/adapters/textual/test_slay_app.py`。
- 修改内容注册表或 JSON 结构时，优先检查 `tests/content/test_registry_validation.py`。
- 修改存档结构时，优先检查 `tests/use_cases/test_save_load.py`。

## 文档维护

- 改动代码、内容、命令入口、流程、测试基线或发布方式后，同步更新 `README.md`。
- 只有当协作约束、仓库事实入口或修改约束发生变化时，才更新 `AGENTS.md`。
