# Textual-Only Runtime Design

Date: 2026-03-27
Status: Approved for implementation

## 1. 背景

当前项目同时保留了：

- `textual` 作为可选 TUI 运行模式
- 基于 `rich` 的纯终端运行模式
- 一批位于 `adapters/terminal/` 下、但已经被 `textual` 复用的共享展示工具

这带来两个问题：

- 启动入口与文档仍暗示项目支持双 UI 模式，和当前目标不一致
- `terminal` 目录既包含已废弃的运行模式代码，也包含仍在使用的共享 Rich 展示能力，长期会误导维护

## 2. 目标

- 让 `textual` 成为唯一启动与运行模式
- 删除纯终端 runner 和 `--ui terminal|textual` 分流
- 将 `textual` 仍依赖的 Rich 展示工具迁到不带“terminal 模式”语义的共享目录
- 保持现有玩法流程、菜单映射、inspect、奖励与 Boss 结算行为不变

## 3. 非目标

- 不重写 `SessionState`、`route_menu_choice()` 或战斗/奖励领域逻辑
- 不重做 Textual 布局和交互模型
- 不在本轮重构中修改玩家可见规则或内容 JSON

## 4. 方案

### 4.1 唯一运行入口

- `src/slay_the_spire/app/cli.py` 去掉 `--ui` 参数
- `new` 与 `load` 两个命令统一直接进入 `run_textual_session()`
- 帮助文案、测试和项目说明同步更新为 Textual-only

### 4.2 共享 Rich 展示层迁移

把 `adapters/terminal/` 下仍被生产代码复用的展示能力迁到新的共享目录，例如 `src/slay_the_spire/adapters/rich_ui/`。迁移对象包括：

- 主题与样式常量
- 卡牌/菜单/状态的 Rich 文本部件
- inspect 详情格式化
- 供 `session.py` 生成 Rich renderable 的房间渲染入口

迁移策略以“移动文件并改 import”为主，不在同一轮引入行为重写。

### 4.3 删除 terminal-only 代码

删除：

- `src/slay_the_spire/adapters/terminal/app.py`
- `src/slay_the_spire/adapters/terminal/prompts.py`
- 纯 terminal runner 的测试

对 `tests/adapters/terminal/` 中实际验证共享 Rich 展示逻辑的测试，迁到新的共享层测试位置，而不是直接删掉。

## 5. 风险控制

- 采用 TDD：先锁定 CLI、共享 Rich 渲染与 Textual 行为，再迁移代码
- 迁移时保留函数名和外部行为，先过测试再做清理
- 完成后至少验证：
  - `uv run pytest`
  - `uv run slay-the-spire new --seed 5`

## 6. 验收标准

- CLI 不再接受 `--ui`
- 启动新游戏与读档均默认进入 Textual
- 生产代码中不再引用 `src/slay_the_spire/adapters/terminal/app.py` 或 `prompts.py`
- 共享 Rich 展示能力不再放在 `adapters/terminal/` 命名空间下
- 全量测试通过，真实启动成功
