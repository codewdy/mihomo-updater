from __future__ import annotations

import logging
from collections.abc import Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from download_mihomo import DEFAULT_UA, read_http_body_with_progress

logger = logging.getLogger(__name__)

DEFAULT_GH_PROXY_PREFIXES: tuple[str, ...] = ("https://gh-proxy.org/",)


def _coerce_proxy_prefixes(
    proxy_prefixes: str | Sequence[str] | None,
    *,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    """将 ``None``、单个字符串或序列规范化为去空白后的非空前缀元组。"""
    if proxy_prefixes is None:
        return default
    if isinstance(proxy_prefixes, str):
        s = proxy_prefixes.strip()
        return (s,) if s else ()
    out: list[str] = []
    for p in proxy_prefixes:
        if isinstance(p, str):
            t = p.strip()
            if t:
                out.append(t)
    return tuple(out)


def _github_proxy_eligible(url: str) -> bool:
    """是否适合在失败时通过代理前缀再拉取（GitHub 主站与 raw 域名）。"""
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    if not host:
        return False
    if host == "github.com" or host.endswith(".github.com"):
        return True
    return host.endswith("githubusercontent.com")


def _already_behind_any_proxy(url: str, proxy_prefixes: tuple[str, ...]) -> bool:
    for prefix in proxy_prefixes:
        base = prefix.rstrip("/") + "/"
        if url.startswith(base):
            return True
    return False


def download_github_url(
    url: str,
    *,
    label: str | None = None,
    user_agent: str = DEFAULT_UA,
    timeout: float | None = 60.0,
    proxy_prefixes: str | Sequence[str] | None = None,
) -> bytes:
    """
    下载 GitHub 相关 URL（源码归档、raw 等）。直连失败时按顺序尝试
    ``{前缀}{原 URL}``，例如
    ``https://gh-proxy.org/https://github.com/org/repo/archive/refs/heads/main.zip``。

    :param proxy_prefixes: 代理前缀；``None`` 使用 ``DEFAULT_GH_PROXY_PREFIXES``；
        可传单个字符串或若干前缀，前者失败后依次试后者。空序列表示不启用代理回退。
    """
    prefixes = _coerce_proxy_prefixes(
        proxy_prefixes, default=DEFAULT_GH_PROXY_PREFIXES
    )
    lg = label or url

    def fetch(u: str, log_label: str) -> bytes:
        req = Request(u, method="GET")
        req.add_header("User-Agent", user_agent)
        with urlopen(req, timeout=timeout) as resp:
            return read_http_body_with_progress(resp, label=log_label, log=logger)

    if _already_behind_any_proxy(url, prefixes):
        return fetch(url, lg)

    try:
        return fetch(url, lg)
    except (HTTPError, URLError, OSError) as e:
        if not _github_proxy_eligible(url) or not prefixes:
            raise
        logger.warning(
            "GitHub 直连失败（%s），将依次尝试 %d 个代理前缀",
            e,
            len(prefixes),
        )
        last_err: BaseException | None = None
        last_proxied = ""
        for idx, pref in enumerate(prefixes):
            last_proxied = pref.rstrip("/") + "/" + url
            try:
                return fetch(
                    last_proxied,
                    f"{lg} (proxy {idx + 1}/{len(prefixes)})",
                )
            except (HTTPError, URLError, OSError) as err:
                last_err = err
                logger.warning(
                    "代理前缀失败 [%d/%d] %s — %s",
                    idx + 1,
                    len(prefixes),
                    pref,
                    err,
                )
        assert last_err is not None
        logger.error("所有代理前缀均失败，最后尝试: %s", last_proxied)
        raise last_err
