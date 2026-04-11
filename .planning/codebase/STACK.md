# Technology Stack

**Analysis Date:** 2026-04-11

## Languages

**Primary:**
- Python 3.12+ - 主业务代码与测试，见 `pyproject.toml`、`src/slay_the_spire/`、`tests/`

**Secondary:**
- JSON - 游戏内容与存档数据，见 `content/`、`src/slay_the_spire/data/content/`、`saves/latest.json`
- Markdown - 项目文档与本地 Wiki 输出，见 `README.md`、`docs/`、`scripts/generate_local_wiki.py`

## Runtime

**Environment:**
- CPython 3.12+（仓库约束）- 见 `pyproject.toml` 的 `requires-python = ">=3.12"`

**Package Manager:**
- `uv`（版本未在仓库固定）- 见 `README.md` 中 `uv sync` / `uv run` / `uv build`
- Lockfile: present（`uv.lock`）

## Frameworks

**Core:**
- `textual>=8.1.1` - 默认且唯一 TUI 运行界面，见 `pyproject.toml`、`src/slay_the_spire/adapters/textual/slay_app.py`
- `rich>=14.3.3` - 终端渲染与共享展示组件，见 `pyproject.toml`、`src/slay_the_spire/adapters/presentation/renderer.py`

**Testing:**
- `pytest>=8.0` - 单元/集成/E2E 测试执行，见 `pyproject.toml`、`tests/`

**Build/Dev:**
- `setuptools>=64` + `wheel` - 构建后端与打包，见 `pyproject.toml`
- `uv` - 依赖同步、运行、构建入口，见 `README.md`

## Key Dependencies

**Critical:**
- `textual` - 驱动主交互与 UI 事件循环，见 `src/slay_the_spire/adapters/textual/textual_runner.py`
- `rich` - 驱动屏幕布局、面板、文本渲染，见 `src/slay_the_spire/adapters/presentation/widgets.py`

**Infrastructure:**
- Python 标准库 `argparse` / `pathlib` / `json` / `dataclasses` - CLI、路径、序列化、状态模型，见 `src/slay_the_spire/app/cli.py`、`src/slay_the_spire/adapters/persistence/save_files.py`

## Configuration

**Environment:**
- 未检测到 `.env` 依赖；运行参数通过 CLI 显式传入，见 `src/slay_the_spire/app/cli.py`
- 关键运行参数：`--content-root`、`--save-path`、`--seed`、`--character`，见 `src/slay_the_spire/app/cli.py`

**Build:**
- `pyproject.toml` - 依赖、入口脚本、pytest、setuptools 配置
- `setup.py` - 打包补充声明
- `MANIFEST.in` - 打包文件包含规则

## Platform Requirements

**Development:**
- 本地终端环境（支持 Textual TUI）+ Python 3.12+ + `uv`，见 `README.md`
- 本地可写文件系统（存档写入 `saves/`），见 `src/slay_the_spire/app/session.py`、`src/slay_the_spire/adapters/persistence/save_files.py`

**Production:**
- 本地单机 CLI/TUI 运行（非服务端部署），见 `README.md`
- 可打包为 wheel/sdist，本地安装后通过 `slay-the-spire` 命令启动，见 `pyproject.toml`、`README.md`

---

*Stack analysis: 2026-04-11*
