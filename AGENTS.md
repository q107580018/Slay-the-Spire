# AGENTS

## 项目定位

- 这是一个 Python 3.12 的终端版《Slay the Spire》原型项目，界面依赖 `rich`。
- 当前目标是本地单机、编号菜单驱动的可玩流程，不是图形界面项目，也不是服务端项目。
- 开发环境与命令默认用 `uv`。
- 目前没有配置 `[project.scripts]`。启动入口请用 `uv run python -m slay_the_spire.app.cli ...`。

## 关键结构

- `pyproject.toml`：包配置、依赖、pytest 配置、打包内容声明。
- `src/slay_the_spire/app/cli.py`：CLI 入口，只支持 `new` 和 `load`。
- `src/slay_the_spire/app/session.py`：会话状态、菜单路由、默认内容路径、默认存档路径。
- `src/slay_the_spire/adapters/terminal/`：Rich 终端渲染、菜单 prompt、屏幕布局。
- `src/slay_the_spire/domain/`：战斗流程、状态模型、效果、地图、奖励等领域逻辑。
- `src/slay_the_spire/use_cases/`：开始游戏、出牌、结束回合、进房间、事件选择、存读档等用例。
- `content/`：仓库根目录内容 JSON，适合开发时直接查看和编辑。
- `src/slay_the_spire/data/content/`：会被打进 wheel 的内容 JSON。默认运行优先读取这里。
- `tests/`：终端 UI、领域逻辑、存档、E2E 冒烟测试。
- `docs/superpowers/`：设计与实施计划文档，可参考，不要把它当成当前行为真相。

## 当前功能事实（以代码为准）

- 当前只有 1 个角色：`ironclad`。
- 当前只有 1 幕地图：`act1`。
- 当前地图固定为：`start -> hallway -> elite | event -> boss`。
- 当前普通敌人池来自 `content/enemies/act1_basic.json`：`slime`、`jaw_worm`。
- 当前精英池来自 `content/enemies/act1_elites.json`：只有 `lagavulin`。
- `act1_map.json` 把 `boss_pool_id` 也指向 `act1_elites`，所以 Boss 目前复用精英池，不是独立 Boss 内容。
- 当前 `lagavulin` 会先睡眠 3 次敌方行动，再进入固定的 `18` 伤攻击循环；还没有复刻原版的减力/减敏 debuff。
- 当前事件池只有 `shining_light`，选项只有“接受 / 离开”。
- 当前初始卡池只有 `strike`、`defend`、`bash`。
- 当前铁甲战士起始套牌是 `5 strike + 4 defend + 1 bash`。
- 当前起始遗物只有 `burning_blood`，效果是战斗结束回复 6 点生命；该效果已经接入运行时 hook，会在真实战斗结算后生效。
- 终端交互主路径走 `route_menu_choice()` 的编号菜单，不是自由文本命令模式。
- CLI 支持：
  - `uv run python -m slay_the_spire.app.cli new --seed 5`
  - `uv run python -m slay_the_spire.app.cli load --save-path saves/latest.json`
- `new` 必填 `--seed`，可选 `--character`、`--content-root`、`--save-path`。
- `load` 可选 `--content-root`、`--save-path`。
- 默认存档路径是 `./saves/latest.json`。
- 默认内容路径优先取 `src/slay_the_spire/data/content/`；只有找不到时才会回退到仓库根目录 `content/`。
- `content/` 与 `src/slay_the_spire/data/content/` 当前内容一致，但它们是两套实际文件，需要同步维护。
- 事件、商店、休息、奖励的用例已经存在，但当前主地图只实际走到战斗和事件。
- 当前奖励领取会真实写回 `run_state`：金币奖励会增加金币，卡牌奖励会把对应卡牌实例加入牌组。
- 当前战斗奖励卡牌 `reward_strike` / `reward_defend` 会分别落成 `strike_plus` / `defend_plus` 实例。

## 开发和发布规则

- 初始化环境：`uv sync --dev`
- 跑测试：`uv run pytest`
- 本地启动新游戏：`uv run python -m slay_the_spire.app.cli new --seed 5`
- 从存档恢复：`uv run python -m slay_the_spire.app.cli load --save-path saves/latest.json`
- 打包：`uv build`
- 打包后检查 `dist/` 里的 wheel / sdist 是否更新。
- 发版前确认包内资源路径仍可用。wheel 实际携带的是 `src/slay_the_spire/data/content/`，不是根目录 `content/`。
- 如果修改内容 JSON，发布前至少做一件事：同步更新 `src/slay_the_spire/data/content/`。否则默认运行和打包结果会读到旧内容。
- 如果修改菜单、渲染或会话路由，优先补 `tests/adapters/terminal/` 与 `tests/e2e/test_single_act_smoke.py`。
- 如果修改存档结构，检查 `src/slay_the_spire/use_cases/save_game.py`、`load_game.py` 和对应测试，避免破坏已有 JSON 兼容性。

## 配置与安全

- 仓库当前没有 `.env` / `.env.example`，也没有外部服务凭据依赖。
- 存档文件是普通 JSON，默认写入 `saves/latest.json`。如果要提交样例存档，先确认不包含本地路径。
- 内容加载依赖目录结构存在 `characters/ironclad.json`。改目录结构时要同步更新 `default_content_root()` 判定逻辑。

## 维护建议

- 优先相信 `src/slay_the_spire/app/session.py`、`tests/` 和 `content/*.json`，不要优先相信旧文档。
- 新增房间类型前，先确认三层都补齐：地图内容、use case、终端菜单渲染。
- 新增角色、卡牌、敌人或事件时，先改根目录 `content/`，再同步到 `src/slay_the_spire/data/content/`。
- 新增菜单、事件、奖励、效果说明等面向玩家的终端文案时，默认统一写成中文；除代码标识、命令、路径和必要专有名词外，不要向终端用户暴露英文效果文本。
- 如果后续希望直接执行 `slay-the-spire`，需要在 `pyproject.toml` 增加 `[project.scripts]`。
