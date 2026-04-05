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
from download_mihomo import download_mihomo

_REPO_ROOT = Path(__file__).resolve().parent.parent

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def _auto_refresh_config(cfg: Config) -> None:
    api_token = read_mihomo_api_auth_token(cfg)
    try:
        download_clash_config(cfg)
    except Exception:
        logger.exception("自动更新：下载配置文件失败")
        return
    try:
        reload_mihomo_config(cfg, auth_token=api_token)
    except MihomoAPIError:
        pass
    except Exception:
        logger.exception("自动更新：通过 API 重载配置失败")


def main() -> None:
    os.chdir(_REPO_ROOT)
    cfg_file = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("config.yaml")
    cfg = load_config(cfg_file)

    try:
        download_mihomo(cfg.path)
    except Exception:
        logger.exception("下载 mihomo 失败")

    try:
        download_clash_config(cfg)
    except Exception:
        logger.exception("下载配置文件失败")

    data_dir = Path(cfg.path).resolve()
    mihomo_bin = data_dir / "mihomo"
    proc = subprocess.Popen(
        [str(mihomo_bin), "-d", str(data_dir)],
        stdin=subprocess.DEVNULL,
    )
    interval = cfg.config_update_interval
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
