# Slay the Spire TUI Prototype

一个基于 Python 3.12、`textual` 和 `rich` 构建的《Slay the Spire》终端原型项目。

项目当前以原版《Slay the Spire》1 代为内容基线，目标是实现一个本地单机、可存读档、可回放主流程的 TUI 版本，而不是图形界面或服务端项目。

## 当前状态

- 已支持角色：`ironclad`
- 已支持章节：`act1`、`act2`
- 已接通房间类型：普通战斗、事件、精英、商店、休息点、Boss
- 已支持地图分支、奖励领取、Boss 奖励、存档 / 读档
- 默认交互方式是 Textual TUI，底层复用共享的 `rich` 渲染组件

项目仍处于开发阶段，玩法、美术表现和内容覆盖率都还会继续迭代。

## 快速开始

### 1. 安装依赖

```bash
uv sync --dev
```

### 2. 开始新游戏

```bash
uv run slay-the-spire new --seed 5
```

也可以直接调用模块入口：

```bash
uv run python -m slay_the_spire.app.cli new --seed 5
```

### 3. 读取存档

```bash
uv run slay-the-spire load --save-path saves/latest.json
```

### 4. 运行测试

```bash
uv run pytest
```

## 项目结构

- `src/slay_the_spire/app/`：CLI 入口、会话状态、菜单路由
- `src/slay_the_spire/adapters/textual/`：Textual 界面与组件
- `src/slay_the_spire/adapters/rich_ui/`：共享 Rich 渲染与 inspect 视图
- `src/slay_the_spire/domain/`：战斗、地图、奖励、运行时 Hook 等领域逻辑
- `src/slay_the_spire/use_cases/`：开始游戏、出牌、进房间、事件、商店、休息、奖励、存读档
- `content/`：开发时优先维护的内容 JSON
- `src/slay_the_spire/data/content/`：随 wheel 一起打包的内容 JSON
- `tests/`：领域逻辑、内容校验、Textual / Rich UI 与 E2E 冒烟测试

## 开发说明

- 本项目默认使用 `uv` 管理环境、依赖和命令执行。
- 默认存档路径是 `saves/latest.json`，本地存档不纳入版本控制。
- 如果修改了内容 JSON，请同步更新 `content/` 和 `src/slay_the_spire/data/content/`，否则本地开发与打包后的运行结果可能不一致。

## License

本项目采用 MIT License，详见 `LICENSE`。
