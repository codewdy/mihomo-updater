from __future__ import annotations

import io
import logging
import shutil
import zipfile
from pathlib import Path

from config import Config
from download_github import download_github_url

logger = logging.getLogger(__name__)


def _strip_zip_root(names: list[str]) -> str | None:
    """若所有条目共享单一顶层目录，返回应剥离的前缀（含尾部 ``/``）。"""
    file_names = [n for n in names if n and not n.endswith("/")]
    if not file_names:
        return None
    roots = {n.split("/", 1)[0] for n in file_names}
    if len(roots) != 1:
        return None
    root = roots.pop()
    prefix = root + "/"
    if not all(n.startswith(prefix) or n == root for n in file_names):
        return None
    return prefix


def _extract_zip_safe(
    zf: zipfile.ZipFile,
    dest: Path,
    *,
    strip_prefix: str | None,
) -> None:
    dest = dest.resolve()
    for info in zf.infolist():
        name = info.filename
        if name.endswith("/"):
            continue
        rel = (
            name[len(strip_prefix) :]
            if strip_prefix and name.startswith(strip_prefix)
            else name
        )
        rel_path = Path(rel)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            raise ValueError(f"非法 zip 路径: {name!r}")
        target = (dest / rel_path).resolve()
        if not target.is_relative_to(dest):
            raise ValueError(f"zip 路径越界: {name!r}")
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info) as src, target.open("wb") as dst:
            shutil.copyfileobj(src, dst)


def download_metacubex_ui(config: Config) -> Path | None:
    """
    下载 Web UI（默认 metacubexd gh-pages zip）并解压到 ``{path}/{ui_subdir}``。

    ``ui_url`` 为空或仅空白时跳过，返回 ``None``。
    若目标目录下已有 ``index.html``（视为已安装），则跳过下载，返回 UI 目录绝对路径。
    """
    url = (config.ui_url or "").strip()
    if not url:
        logger.info("未配置 ui_url，跳过 Web UI 下载")
        return None

    data = Path(config.path).resolve()
    ui_dir = data / config.ui_subdir
    marker = ui_dir / "index.html"
    if marker.is_file():
        logger.info("Web UI 已存在，跳过下载: %s", ui_dir)
        return ui_dir

    logger.info("开始下载 Web UI: %s -> %s", url, ui_dir)
    body = download_github_url(
        url,
        label="metacubexd (gh-pages zip)",
        proxy_prefixes=config.github_proxy,
    )

    with zipfile.ZipFile(io.BytesIO(body)) as zf:
        strip = _strip_zip_root(zf.namelist())
        if ui_dir.exists():
            shutil.rmtree(ui_dir)
        ui_dir.mkdir(parents=True)
        _extract_zip_safe(zf, ui_dir, strip_prefix=strip)

    logger.info("Web UI 已解压到: %s", ui_dir)
    return ui_dir
