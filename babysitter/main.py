from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from config import load_config
from download_config import download_clash_config
from download_mihomo import download_mihomo

_REPO_ROOT = Path(__file__).resolve().parent.parent

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


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
    # 阻塞在 waitpid 上直至子进程结束，期间不占 CPU；退出时立刻返回，无需轮询 + sleep
    rc = proc.wait()
    if rc != 0:
        logger.error("mihomo 异常退出，退出码: %s", rc)
    raise SystemExit(rc if rc is not None else 1)


if __name__ == "__main__":
    main()
