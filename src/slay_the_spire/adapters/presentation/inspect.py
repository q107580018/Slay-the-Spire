from __future__ import annotations

from inspect import isfunction as _isfunction

from slay_the_spire.adapters.rich_ui import inspect as _impl


def _export_function(name: str):
    fn = getattr(_impl, name)

    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)

    wrapper.__name__ = name
    wrapper.__qualname__ = name
    wrapper.__module__ = __name__
    wrapper.__doc__ = getattr(fn, "__doc__", None)
    return wrapper


for _name, _value in vars(_impl).items():
    if _isfunction(_value):
        globals()[_name] = _export_function(_name)

__all__ = [name for name, value in globals().items() if _isfunction(value) and not name.startswith("_")]
