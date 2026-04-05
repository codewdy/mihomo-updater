from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

from config import Config, load_config
from download_mihomo import read_http_body_with_progress
from mixin import apply_mixin

logger = logging.getLogger(__name__)


class MihomoAPIError(RuntimeError):
    """external-controller 返回错误或网络失败（详情已写入日志）。"""


def read_mihomo_api_auth_token(config: Config) -> str:
    """
    在覆盖 ``config.path/config.yaml`` **之前**调用。

    mihomo 在热重载完成前仍用**当前已加载配置**里的 ``secret`` 校验 API；
    若先写入新文件再用 babysitter 里的新 ``secret`` 发请求，会 401 Unauthorized。
    因此应使用磁盘上**尚未被覆盖**的配置中的 ``secret`` 作为 Bearer token。
    """
    p = Path(config.path) / "config.yaml"
    if not p.is_file():
        return config.secret
    try:
        data: Any = yaml.safe_load(p.read_text(encoding="utf-8"))
    except Exception:
        logger.debug(
            "读取现有 config.yaml 以确定 API secret 失败，改用 babysitter 配置中的 secret",
        )
        return config.secret
    if not isinstance(data, dict):
        return config.secret
    if "secret" not in data:
        return ""
    v = data["secret"]
    if v is None:
        return ""
    return str(v)


def _extract_api_error_message(body: str) -> str:
    """解析 mihomo API 错误 JSON（通常为 {\"message\": \"...\"}）。"""
    text = body.strip()
    if not text:
        return ""
    try:
        obj: Any = json.loads(text)
    except json.JSONDecodeError:
        return text[:2000]
    if isinstance(obj, dict):
        msg = obj.get("message")
        if isinstance(msg, str) and msg.strip():
            return msg.strip()
    return text[:2000]


def download_clash_config(config: Config) -> None:
    logger.info("开始下载 Clash 配置: %s", config.url)
    req = Request(config.url, method="GET")
    req.add_header(
        "User-Agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )
    with urlopen(req) as resp:
        raw = read_http_body_with_progress(
            resp, label="Clash 配置", log=logger
        )
    text = raw.decode("utf-8")
    data: Any = yaml.safe_load(text)

    data = apply_mixin(data, config)

    out = Path(config.path) / "config.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            data, f, allow_unicode=True, default_flow_style=False, sort_keys=False
        )
    logger.info("Clash 配置已写入: %s", out)


def reload_mihomo_config(
    config: Config,
    *,
    timeout: float = 30.0,
    auth_token: str | None = None,
) -> None:
    """
    通过 external-controller API 热重载磁盘上的配置（需已写入 config.path/config.yaml）。
    参见 https://wiki.metacubex.one/en/api/ — PUT /configs?force=true
    成功一般为 HTTP 204/200 且无正文；失败为 4xx/5xx 及 JSON message。

    :param auth_token: Bearer token；``None`` 时使用 ``config.secret``。传空字符串表示不设鉴权头（与内核无 secret 时一致）。
    """
    url = f"http://127.0.0.1:{config.api_port}/configs?force=true"
    body = json.dumps({"path": "", "payload": ""}).encode("utf-8")
    req = Request(url, data=body, method="PUT")
    req.add_header("Content-Type", "application/json")
    token = config.secret if auth_token is None else auth_token
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urlopen(req, timeout=timeout) as resp:
            code = resp.getcode()
            raw = resp.read()
    except HTTPError as e:
        err_text = e.read().decode("utf-8", errors="replace")
        msg = _extract_api_error_message(err_text) or e.reason or "HTTP 错误"
        logger.error(
            "mihomo API 重载配置失败: HTTP %s, %s",
            e.code,
            msg,
        )
        raise MihomoAPIError(f"HTTP {e.code}: {msg}") from e
    except URLError as e:
        reason = e.reason
        detail = str(reason) if reason is not None else str(e)
        logger.error("mihomo API 重载配置请求失败: %s", detail)
        raise MihomoAPIError(detail) from e

    text = raw.decode("utf-8", errors="replace").strip()
    if code not in (200, 204):
        msg = _extract_api_error_message(text) or text or "(无正文)"
        logger.error(
            "mihomo API 重载配置失败: 非预期状态码 %s, %s",
            code,
            msg,
        )
        raise MihomoAPIError(f"HTTP {code}: {msg}")

    if text:
        # 正常成功多为 204 无正文；若有正文则记录便于排查
        logger.warning(
            "mihomo API 重载配置: HTTP %s 返回非空正文: %s",
            code,
            text[:2000],
        )
    else:
        logger.debug("mihomo API 重载配置成功 (HTTP %s)", code)


if __name__ == "__main__":
    import sys

    config = load_config(sys.argv[-1])
    print(config)

    download_clash_config(config)
