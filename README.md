# Slay the Spire TUI Prototype

一个基于 Python 3.12、`textual` 和 `rich` 构建的《Slay the Spire》终端原型项目。

项目当前以原版《Slay the Spire》1 代为玩法与内容基线，目标是实现一个本地单机、可存读档、可回放主流程的 TUI 版本，不是图形界面项目，也不是服务端项目。

## 当前实现

- 当前角色：`ironclad`
- 当前章节：`act1`、`act2`
- 当前开局流程：`new` 先进入 opening；不传 `--character` 时先选角色，传 `--character` 时直接进入 `Neow`
- 当前主路径：`act1` Boss 宝箱后进入 `act2`，`act2` Boss 宝箱后进入最终 `victory`
- 当前房间类型：普通战斗、事件、精英、商店、休息点、宝箱、Boss、Boss 宝箱
- 当前支持：分支地图、战斗奖励、Boss 奖励、遗物/药水/商店、休息点升级与跳过、JSON 存读档
- 当前普通宝箱流程为：未打开时不显示具体遗物，打开后可选择拿取遗物或放弃并离开
- 当前部分敌人已具备原版核心 debuff 行为，例如 `lagavulin` 的 `Siphon Soul` 会使玩家失去力量与敏捷
- 当前战斗结算已支持正负力量与敏捷修正；负力量会降低伤害，负敏捷会降低获得的格挡，最低按 `0` 结算
- 当前 opening 支持角色选择、`Neow` 奖励与目标卡子菜单
- 当前 opening 的 `Neow` 菜单支持悬浮预览更完整的奖励信息：卡牌、遗物、药水会显示与其他 hover preview 一致的详细效果说明
- 当前 `Neow` 的诅咒 tradeoff 选项会以“加入诅咒牌”作为代价，并发放配套高价值奖励；不会再出现“奖励本身就是诅咒牌”的选项
- 当前默认交互：Textual TUI，底层复用共享的 `rich` 渲染和 inspect 组件
- 当前铁甲战士红卡已按原版 1 代完整补齐，包含普通 / 非普通 / 稀有 / 无限升级 `Searing Blow`、动态费用 `Blood for Blood`、条件出牌 `Clash`、消耗联动 `Dark Embrace` / `Feel No Pain`、状态牌联动 `Evolve` / `Fire Breathing`、双目标牌 `Headbutt` 等完整机制
- 当前 `Corruption` 已按原版规则生效：所有技能牌耗能变为 `0`，且在被打出时进入消耗堆；相关逻辑已收口到通用“卡牌运行时规则”层，便于继续扩展其他运行时覆写效果
- 当前 `Rampage` / `Rampage+` 已支持按同一张卡实例进行战斗内累计伤害；`Rampage+` 的每次增伤为 `+8`
- 当前战斗状态牌已包含 `Burn`、`Wound`、`Dazed`，并支持对应的抽牌、消耗和回合结束联动
- 当前 `Ghostly Armor` 使用通用 `Ethereal` 规则：回合结束时若仍在手牌中，则进入消耗堆
- 当前抽牌堆在内部按真实顺序结算；默认预览会隐藏真实抽牌顺序，持有 `Frozen Eye` 时才显示真实顺序
- 当前可编辑内容 `content/cards/ironclad_starter.json` 与打包内容 `src/slay_the_spire/data/content/cards/ironclad_starter.json` 需保持同步

项目仍处于开发阶段，玩法覆盖率和交互细节都会继续调整；以代码和测试为准，不以旧文档为准。

## 快速开始

### 1. 安装依赖

```bash
uv sync --dev
```

### 2. 开始新游戏

```bash
uv run slay-the-spire new
```

可选传入固定种子：

```bash
uv run slay-the-spire new --seed 5
```

也可以直接调用模块入口：

```bash
uv run python -m slay_the_spire.app.cli new --seed 5
```

`new` 当前支持的参数：

- `--seed`
- `--character`
- `--content-root`
- `--save-path`

说明：

- 不传 `--seed` 时会自动生成随机 seed。
- 不传 `--character` 时会进入 opening 角色选择；传 `--character ironclad` 时会跳过角色页直接进入 `Neow`。
- opening 阶段仍使用右侧编号菜单，但不会显示真实地图，也不支持 `save/load`。
- 旧的 `--ui` 参数已经移除；默认且唯一界面就是 Textual。

### 3. 读取存档

```bash
uv run slay-the-spire load --save-path saves/latest.json
```

也可以使用模块入口：

```bash
uv run python -m slay_the_spire.app.cli load --save-path saves/latest.json
```

`load` 当前支持的参数：

- `--content-root`
- `--save-path`

如果不传 `--save-path`，默认会读取 `saves/latest.json`。

### 4. 运行测试

```bash
uv run pytest
```

### 5. 打包

```bash
uv build
```

打包后检查 `dist/` 下的 wheel 和 sdist 是否为最新结果。

## 项目结构

- `src/slay_the_spire/app/`：CLI 入口、会话状态、菜单路由、默认路径解析
- `src/slay_the_spire/adapters/textual/`：Textual 界面与地图/日志组件
- `src/slay_the_spire/adapters/presentation/`：共享终端展示/渲染、非战斗界面、inspect 面板
- `src/slay_the_spire/adapters/persistence/`：JSON 存档读写
- `src/slay_the_spire/content/`：内容加载、注册表、目录装配
- `src/slay_the_spire/domain/`：战斗、地图、奖励、Hook、状态模型等领域逻辑
- `src/slay_the_spire/use_cases/`：开始游戏、出牌、进房间、事件、商店、休息、奖励、存读档
- `content/`：唯一内容真源，开发时维护的内容 JSON
- `src/slay_the_spire/data/content/`：构建 wheel 时临时生成的包内内容 JSON
- `tests/`：CLI、Textual、共享展示层、内容校验、领域逻辑、E2E 冒烟测试

## 本地 Wiki

项目提供了一个本地 Markdown wiki，用来汇总当前已实现的卡牌、遗物、敌人与事件：

- 文档路径：`docs/local_wiki/cards_and_relics.md`
- 刷新命令：`uv run python scripts/generate_local_wiki.py`

## 开发说明

- 本项目默认使用 `uv` 管理环境、依赖和命令执行。
- 默认内容目录优先读取仓库根目录 `content/`；只有安装包环境或显式传 `--content-root` 时才读取其他目录。
- 修改内容 JSON 时只维护 `content/`；`src/slay_the_spire/data/content/` 会在构建 wheel 时临时生成并随构建产物打包，不应手工编辑或提交。
- 每次改动代码、内容、命令入口、流程、测试基线或发布方式后，都应同步更新 `README.md`；只有协作约束或仓库工作规则变化时才需要更新 `AGENTS.md`。
- 默认存档路径是 `saves/latest.json`，当前存档 schema 版本是 `2`。
- 当前开发阶段默认不为旧存档或旧菜单状态保兼容，除非需求明确要求。

## 测试建议

- 修改菜单、渲染或会话路由时，优先检查 `tests/adapters/presentation/`、`tests/e2e/`。
- 修改 Textual UI 时，优先检查 `tests/adapters/textual/test_slay_app.py`。
- 修改内容注册表或 JSON 结构时，优先检查 `tests/content/test_registry_validation.py`。
- 修改存档结构时，优先检查 `tests/use_cases/test_save_load.py`，并同步关注 `schema_version`。

## License

本项目采用 MIT License，详见 `LICENSE`。
