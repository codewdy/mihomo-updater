from __future__ import annotations

import gzip
import json
import platform
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

GITHUB_LATEST = (
    "https://api.github.com/repos/MetaCubeX/mihomo/releases/latest"
)
DEFAULT_UA = (
    "mihomo-updater/1.0 (Linux; +https://github.com/MetaCubeX/mihomo)"
)


def mihomo_linux_arch_suffixes() -> list[str]:
    """根据当前主机推断 mihomo Linux 包名中的架构段（可多个候选，按顺序尝试）。"""
    if sys.platform != "linux":
        raise OSError("仅支持 Linux，当前 platform 为 " + repr(sys.platform))

    machine = platform.machine().lower()
    is_64bit_userspace = platform.architecture()[0] == "64bit"

    if machine in ("x86_64", "amd64"):
        return ["amd64"]
    if machine in ("aarch64", "arm64"):
        return ["arm64"]
    if machine in ("i386", "i686", "x86"):
        return ["386"]
    if machine in ("armv7l", "armv7", "armv6l", "armv6", "armv5tel", "armv5l"):
        if machine.startswith("armv6"):
            return ["armv6"]
        if machine.startswith("armv5"):
            return ["armv5"]
        return ["armv7"]
    if machine == "armv8l":
        return ["arm64"] if is_64bit_userspace else ["armv7"]
    if machine in ("loongarch64", "loong64"):
        return ["loong64-abi2", "loong64-abi1"]
    if machine in ("riscv64", "riscv"):
        return ["riscv64"]
    if machine in ("ppc64le", "powerpc64le"):
        return ["ppc64le"]
    if machine in ("s390x",):
        return ["s390x"]
    if machine in ("mips64",):
        return ["mips64"]
    if machine in ("mips64el", "mips64le"):
        return ["mips64le"]
    if machine in ("mips", "mipsel"):
        return ["mipsle-softfloat", "mipsle-hardfloat"]

    raise OSError(f"未适配的 Linux 架构: {machine!r}")


def _http_json(url: str) -> Any:
    req = Request(url, method="GET")
    req.add_header("User-Agent", DEFAULT_UA)
    req.add_header("Accept", "application/vnd.github+json")
    with urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _expected_gz_names(tag: str, suffixes: list[str]) -> list[str]:
    return [f"mihomo-linux-{s}-{tag}.gz" for s in suffixes]


def download_mihomo(
    dest_dir: str | Path,
    *,
    tag: str | None = None,
    filename: str = "mihomo",
) -> Path:
    """
    从 GitHub Release 下载与当前 Linux 架构匹配的 mihomo 可执行文件（.gz 单文件包）。

    :param dest_dir: 输出目录
    :param tag: 如 ``v1.19.22``；为 None 时使用 latest release
    :param filename: 解压后的文件名（默认 ``mihomo``）
    :return: 写入的可执行文件路径
    """
    suffixes = mihomo_linux_arch_suffixes()
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / filename

    if tag is None:
        release = _http_json(GITHUB_LATEST)
        tag = str(release["tag_name"])
        assets: list[dict[str, Any]] = release.get("assets") or []
    else:
        if not tag.startswith("v"):
            tag = f"v{tag}"
        api_url = f"https://api.github.com/repos/MetaCubeX/mihomo/releases/tags/{tag}"
        try:
            release = _http_json(api_url)
        except HTTPError as e:
            if e.code == 404:
                raise OSError(f"找不到该 release: {tag!r}") from e
            raise
        assets = release.get("assets") or []

    wanted = set(_expected_gz_names(tag, suffixes))
    download_url: str | None = None
    chosen: str | None = None
    for a in assets:
        name = a.get("name")
        if not isinstance(name, str):
            continue
        if name in wanted:
            u = a.get("browser_download_url")
            if isinstance(u, str):
                download_url = u
                chosen = name
                break

    if not download_url or not chosen:
        tried = ", ".join(sorted(wanted))
        raise OSError(
            f"当前 release {tag} 中未找到与本机架构匹配的包（已尝试: {tried}）"
        )

    req = Request(download_url, method="GET")
    req.add_header("User-Agent", DEFAULT_UA)
    with urlopen(req) as resp:
        compressed = resp.read()

    binary = gzip.decompress(compressed)
    out_path.write_bytes(binary)
    out_path.chmod(0o755)
    return out_path


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="下载 Linux 版 mihomo（按本机架构）")
    p.add_argument(
        "-d",
        "--dest",
        default=".",
        help="输出目录（默认当前目录）",
    )
    p.add_argument(
        "-t",
        "--tag",
        default=None,
        help="release 标签，如 v1.19.22；省略则使用 latest",
    )
    args = p.parse_args()
    path = download_mihomo(args.dest, tag=args.tag)
    print(path)
