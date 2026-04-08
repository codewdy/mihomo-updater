from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from config import Config, load_config
from download_config import (
    MihomoAPIError,
    download_clash_config,
    read_mihomo_api_auth_token,
    reload_mihomo_config,
)
from download_geoip import download_geoip_metadb
from download_mihomo import download_mihomo
from download_ui import download_metacubex_ui

_REPO_ROOT = Path(__file__).resolve().parent.parent

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def _auto_refresh_config(cfg: Config) -> None:
    logger.info("定时刷新：开始拉取配置并重载")
    api_token = read_mihomo_api_auth_token(cfg)
    try:
        download_clash_config(cfg)
    except Exception:
        logger.exception("自动更新：下载配置文件失败")
        return
    try:
        reload_mihomo_config(cfg, auth_token=api_token)
        logger.info("定时刷新：配置已重载")
    except MihomoAPIError:
        pass
    except Exception:
        logger.exception("自动更新：通过 API 重载配置失败")


def main() -> None:
    os.chdir(_REPO_ROOT)
    cfg_file = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("config.yaml")
    logger.info("加载配置: %s", cfg_file.resolve())
    cfg = load_config(cfg_file)
    logger.info("数据目录: %s", Path(cfg.path).resolve())

    logger.info("步骤 1/4：下载或更新 mihomo 二进制")
    try:
        download_mihomo(cfg.path, github_proxy=cfg.github_proxy)
    except Exception:
        logger.exception("下载 mihomo 失败")

    logger.info("步骤 2/4：初始化 geoip 数据库")
    try:
        download_geoip_metadb(cfg.path, github_proxy=cfg.github_proxy)
    except Exception:
        logger.exception("下载 geoip 数据库失败")

    logger.info("步骤 3/4：下载 Web UI（metacubexd）")
    try:
        download_metacubex_ui(cfg)
    except Exception:
        logger.exception("下载 Web UI 失败")

    logger.info("步骤 4/4：下载并写入 Clash 配置")
    try:
        download_clash_config(cfg)
    except Exception:
        logger.exception("下载配置文件失败")

    data_dir = Path(cfg.path).resolve()
    mihomo_bin = data_dir / "mihomo"
    logger.info("启动 mihomo: %s -d %s", mihomo_bin, data_dir)
    proc = subprocess.Popen(
        [str(mihomo_bin), "-d", str(data_dir)],
        stdin=subprocess.DEVNULL,
    )
    interval = cfg.config_update_interval
    if interval > 0:
        logger.info(
            "mihomo 已启动（pid=%s），将每 %s 秒检查并刷新配置",
            proc.pid,
            interval,
        )
    else:
        logger.info("mihomo 已启动（pid=%s），未启用定时刷新", proc.pid)
    while True:
        try:
            if interval > 0:
                rc = proc.wait(timeout=float(interval))
            else:
                rc = proc.wait()
                break
        except subprocess.TimeoutExpired:
            _auto_refresh_config(cfg)
            continue
        break
    if rc != 0:
        logger.error("mihomo 异常退出，退出码: %s", rc)
    raise SystemExit(rc if rc is not None else 1)


if __name__ == "__main__":
    main()
