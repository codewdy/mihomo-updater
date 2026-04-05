from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

from config import Config
from mixin import apply_mixin


def download_clash_config(config: Config) -> None:
    req = Request(config.url, method="GET")
    req.add_header(
        "User-Agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )
    with urlopen(req) as resp:
        raw = resp.read()
    text = raw.decode("utf-8")
    data: Any = yaml.safe_load(text)

    data = apply_mixin(data, config)

    out = Path(config.path) / "config.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            data, f, allow_unicode=True, default_flow_style=False, sort_keys=False
        )


if __name__ == "__main__":
    import sys
    from config import Config

    config = yaml.safe_load(open(sys.argv[-1]).read())
    config = Config(**config)

    download_clash_config(config)
