from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class Config(BaseModel):
    url: str
    path: str = "data"
    port: int = 7890
    allow_lan: bool = False
    api_port: int = 9090
    secret: str = ""
    config_update_interval: int = 0
    github_proxy: list[str] = ["https://gh-proxy.com/", "https://ghproxy.vip/"]
    ui_url: str = (
        "https://github.com/MetaCubeX/metacubexd/archive/refs/heads/gh-pages.zip"
    )
    ui_subdir: str = "ui"


def _env_tag_constructor(loader: yaml.SafeLoader, node: yaml.Node) -> str:
    if not isinstance(node, yaml.ScalarNode):
        raise yaml.constructor.ConstructorError(
            None,
            None,
            "!env 需要一个标量（环境变量名）",
            node.start_mark,
        )
    name = str(loader.construct_scalar(node)).strip()
    if not name:
        raise yaml.constructor.ConstructorError(
            None, None, "!env 环境变量名不能为空", node.start_mark
        )
    try:
        return os.environ[name]
    except KeyError as e:
        raise KeyError(f"环境变量未设置: {name!r}（YAML !env）") from e


class EnvConfigLoader(yaml.SafeLoader):
    pass


EnvConfigLoader.add_constructor("!env", _env_tag_constructor)

# ${VAR} 必须已设置；${VAR:-} 或 ${VAR:-默认值} 可在未设置时使用默认值
_ENV_SUB = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def _expand_env_string(s: str) -> str:
    def repl(m: re.Match[str]) -> str:
        name, default = m.group(1), m.group(2)
        if default is not None:
            return os.environ.get(name, default)
        if name not in os.environ:
            raise KeyError(f"环境变量未设置: {name!r}（字符串 ${{...}} 插值）")
        return os.environ[name]

    return _ENV_SUB.sub(repl, s)


def expand_env_in_obj(obj: Any) -> Any:
    if isinstance(obj, str):
        return _expand_env_string(obj)
    if isinstance(obj, dict):
        return {k: expand_env_in_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [expand_env_in_obj(i) for i in obj]
    return obj


def load_config(path: str | Path) -> Config:
    """从 YAML 加载配置，支持 !env 与 ${{VAR}} / ${{VAR:-default}}。"""
    path = Path(path)
    raw = yaml.load(path.read_text(encoding="utf-8"), Loader=EnvConfigLoader)
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise TypeError(f"根节点必须为 mapping，得到 {type(raw).__name__}")
    data = expand_env_in_obj(raw)
    return Config(**data)
