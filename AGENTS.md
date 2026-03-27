# AGENTS

## 项目定位

- 这是一个 Python 3.12 的终端版《Slay the Spire》原型项目。
- 默认交互界面是基于 `rich` 的编号菜单终端 UI，并提供基于 `textual` 的可选 TUI。
- 目标是本地单机、可回放的菜单驱动流程，不是图形界面项目，也不是服务端项目。
- 开发环境、依赖管理、命令执行默认都用 `uv`。
- 当前已配置 `[project.scripts]`，可用 `uv run slay-the-spire ...` 或 `uv run python -m slay_the_spire.app.cli ...` 启动。

## 关键结构

- `pyproject.toml`：包配置、依赖、pytest 配置、打包内容声明、脚本入口。
- `src/slay_the_spire/app/cli.py`：CLI 入口，支持 `new` / `load`，并支持全局 `--ui terminal|textual`。
- `src/slay_the_spire/app/session.py`：会话状态、菜单路由、默认内容路径、默认存档路径、跨幕推进、胜利/失败判定。
- `src/slay_the_spire/app/menu_definitions.py`：终端编号菜单定义，包含战斗、事件、商店、休息、Boss 奖励、查看页菜单。
- `src/slay_the_spire/adapters/terminal/`：Rich 终端渲染、prompt、combat/non-combat 屏幕和组件。
- `src/slay_the_spire/adapters/textual/`：Textual 入口、地图组件、日志和交互面板。
- `src/slay_the_spire/adapters/persistence/save_files.py`：JSON 存档读写。
- `src/slay_the_spire/content/`：内容加载与注册表。
- `src/slay_the_spire/domain/`：战斗流程、状态模型、Hook、地图生成、奖励生成等领域逻辑。
- `src/slay_the_spire/use_cases/`：开始游戏、出牌、结束回合、进房间、事件、商店、休息、奖励、存读档等用例。
- `content/`：仓库根目录内容 JSON，开发时应优先编辑这里。
- `src/slay_the_spire/data/content/`：随 wheel 打包的内容 JSON；默认运行优先读取这里。
- `tests/`：终端 UI、Textual UI、内容校验、领域逻辑、存档和 E2E 冒烟测试。
- `docs/superpowers/`：设计和计划文档，可参考，但不要把它当成当前行为真相。

## 当前功能事实（以代码为准）

- 当前只有 1 个角色：`ironclad`。
- 当前已有 2 幕：`act1`、`act2`。
- `act1` 结束后会进入 `act2`；`act2` Boss 奖励领取完成后会进入最终 `victory`。
- 当前地图按 `content/acts/*.json` 的 `map_config` 生成分支路径，不是固定单线。
- 当前地图规则会实际生成并走到 `combat`、`event`、`elite`、`shop`、`rest`、`boss`。
- `act1` 至少保证 1 个商店、1 个休息点、1 个精英；`act2` 至少保证 1 个事件、1 个商店、1 个休息点、2 个精英。
- 当前普通敌人池至少包含：
  - `act1_basic`：`slime`、`jaw_worm`
  - `act2_basic`：`chosen`、`byrd`、`spheric_guardian`、`slaver_red`
- 当前精英池至少包含：
  - `act1_elites`：`lagavulin`
  - `act2_elites`：`book_of_stabbing`、`gremlin_leader`、`slaver_blue`、`taskmaster`
- 当前 Boss 池至少包含：
  - `act1_bosses`：`hexaghost`
  - `act2_bosses`：`champ`、`bronze_automaton`、`the_collector`
- `bronze_automaton` 与 `the_collector` 的敌人文件里还包含其衍生单位 `bronze_orb`、`torch_head`。
- 当前 `lagavulin` 会先睡眠 3 次敌方行动，再进入固定攻击循环；没有复刻原版减力/减敏 debuff。
- 当前事件池不止 1 个事件：
  - `act1_events` 已包含 `shining_light`、`the_cleric`、`world_of_goop`、`living_wall`、`big_fish`、`golden_shrine` 等
  - `act2_events` 已包含 `ancient_writing`、`masked_bandits`、`forgotten_altar`
- 当前事件效果已覆盖升级牌、删牌、回血、加金币、扣金币、加最大生命、获得遗物、失去生命等分支。
- 当前铁甲战士起始套牌仍是 `5 strike + 4 defend + 1 bash`。
- 当前铁甲战士卡池不止起始 3 张，`content/cards/ironclad_starter.json` 还包含升级牌和额外可奖励牌，如 `anger`、`pommel_strike`、`shrug_it_off`、`bloodletting`、`true_grit` 等。
- 当前有诅咒牌内容：`content/cards/curses.json`。
- 当前起始遗物池至少包含 `burning_blood` 和 `golden_idol`。
- 当前 Boss 遗物池包含 `black_blood`、`anchor`、`lantern`。
- 当前药水池已存在 `fire_potion`、`block_potion`、`strength_potion`。
- `burning_blood`、`black_blood`、`anchor`、`lantern` 等遗物效果已接入运行时 Hook。
- 当前战斗奖励会真实写回 `run_state`：金币会增加，卡牌奖励会把对应实例加入牌组，Boss 奖励会发高额金币和三选一遗物。
- 当前战斗奖励中的 `reward_strike` / `reward_defend` 会分别落成 `strike_plus` / `defend_plus`。
- 当前商店可出售卡牌、遗物、药水，并支持付费移除 1 张牌。
- 当前休息点支持至少“恢复生命”和“升级 1 张牌”。
- 终端交互主路径走 `route_menu_choice()` 的编号菜单，不是自由文本命令模式。
- 查看页已覆盖角色状态、牌组、遗物、药水、敌人详情、卡牌详情等 inspect 菜单。
- CLI 支持：
  - `uv run python -m slay_the_spire.app.cli new --seed 5`
  - `uv run python -m slay_the_spire.app.cli load --save-path saves/latest.json`
  - `uv run slay-the-spire new --seed 5`
  - `uv run slay-the-spire --ui textual new --seed 5`
- `new` 必填 `--seed`，可选 `--character`、`--content-root`、`--save-path`。
- `load` 可选 `--content-root`、`--save-path`。
- 全局可选 `--ui terminal|textual`，默认 `terminal`。
- 默认存档路径是 `./saves/latest.json`。
- 默认内容路径优先取 `src/slay_the_spire/data/content/`；只有找不到时才会回退到仓库根目录 `content/`。
- `content/` 与 `src/slay_the_spire/data/content/` 是两套实际文件；修改内容时必须同步维护。

## 开发和发布规则

- 初始化环境：`uv sync --dev`
- 跑测试：`uv run pytest`
- 本地启动新游戏：`uv run python -m slay_the_spire.app.cli new --seed 5`
- 启动 Textual 界面：`uv run slay-the-spire --ui textual new --seed 5`
- 从存档恢复：`uv run python -m slay_the_spire.app.cli load --save-path saves/latest.json`
- 打包：`uv build`
- 打包后检查 `dist/` 中的 wheel / sdist 是否更新。
- 发版前确认包内资源路径仍可用；wheel 实际携带的是 `src/slay_the_spire/data/content/`，不是根目录 `content/`。
- 如果修改内容 JSON，发布前至少同步更新 `src/slay_the_spire/data/content/`，否则默认运行和打包结果会读到旧内容。
- 如果修改菜单、渲染或会话路由，优先补 `tests/adapters/terminal/test_app.py`、`tests/adapters/terminal/test_renderer.py`、`tests/e2e/test_single_act_smoke.py`、`tests/e2e/test_two_act_smoke.py`。
- 如果修改 Textual UI，优先检查 `tests/adapters/textual/test_slay_app.py`。
- 如果修改内容注册表或 JSON 结构，优先检查 `tests/content/test_registry_validation.py`。
- 如果修改存档结构，检查 `src/slay_the_spire/use_cases/save_game.py`、`src/slay_the_spire/use_cases/load_game.py` 和 `tests/use_cases/test_save_load.py`，避免破坏已有 JSON 兼容性。

## 配置与安全

- 仓库当前没有 `.env` / `.env.example`，也没有外部服务凭据依赖。
- 存档文件是普通 JSON，默认写入 `saves/latest.json`。
- 用户已明确说明：存档不需要提交。
- 内容加载依赖目录结构存在 `characters/ironclad.json`；改目录结构时要同步更新 `default_content_root()` 判定逻辑。
- `saves/` 当前未被忽略；如需提交样例存档，先确认不包含本地路径或临时调试状态。

## 维护建议

- 优先相信 `src/slay_the_spire/app/session.py`、`tests/`、`content/` 和 `src/slay_the_spire/data/content/`，不要优先相信旧文档。
- 新增房间类型前，先确认三层都补齐：地图内容、use case / session 路由、终端渲染。
- 新增角色、卡牌、敌人、事件、遗物或药水时，先改根目录 `content/`，再同步到 `src/slay_the_spire/data/content/`。
- 新增战斗后奖励或 Boss 奖励时，同时检查 `src/slay_the_spire/domain/rewards/reward_generator.py`、`src/slay_the_spire/use_cases/apply_reward.py` 和对应测试。
- 新增菜单、事件、奖励、效果说明等面向玩家的终端文案时，默认统一写成中文；除代码标识、命令、路径和必要专有名词外，不要向终端用户暴露英文效果文本。
- 如果修改启动方式、`--ui` 参数或脚本入口，记得同步更新这里和 `pyproject.toml`。
