"""Textual 入口，兼容 SessionState。"""
from __future__ import annotations

from slay_the_spire.app.session import SessionState, SessionLoopResult
from slay_the_spire.adapters.textual.slay_app import SlayApp

def run_textual_session(*, session: SessionState) -> SessionLoopResult:
    """启动 Textual 应用接管 session。"""
    app = SlayApp(session)
    app.run()
    # 退出后返回最终的 session 和空的 outputs（因为界面已经被 textual 清除了）
    return SessionLoopResult(outputs=[], final_session=app._session)
