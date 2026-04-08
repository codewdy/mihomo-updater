from __future__ import annotations

import logging
from pathlib import Path

from download_github import download_github_url

logger = logging.getLogger(__name__)

DEFAULT_GEOIP_URL = (
    "https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geoip.metadb"
)


def download_geoip_metadb(
    dest_dir: str | Path,
    *,
    filename: str = "geoip.metadb",
    url: str = DEFAULT_GEOIP_URL,
    github_proxy: list[str] | None = None,
) -> Path:
    """
    下载 geoip.metadb 到数据目录；若文件已存在则跳过。

    :param dest_dir: 输出目录
    :param filename: 输出文件名（默认 ``geoip.metadb``）
    :param url: 下载地址
    :param github_proxy: 与配置项 ``github_proxy`` 相同；``None`` 使用默认代理回退
    :return: 输出文件路径
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / filename
    if out_path.is_file():
        logger.info("geoip 数据库已存在，跳过下载: %s", out_path)
        return out_path

    logger.info("开始下载 geoip 数据库: %s", url)
    body = download_github_url(
        url,
        label=filename,
        proxy_prefixes=github_proxy,
    )
    out_path.write_bytes(body)
    logger.info("geoip 数据库已写入: %s", out_path)
    return out_path
