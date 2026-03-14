import base64
import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import orjson
from camoufox.server import LAUNCH_SCRIPT, get_nodejs, to_camel_case_dict
from camoufox.utils import launch_options


def parse_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def parse_proxy(url: str | None):
    if not url:
        return None
    url = url.strip()
    if not url:
        return None
    p = urlparse(url)
    if not p.scheme or not p.hostname or not p.port:
        raise ValueError(f"Invalid proxy url: {url}")
    out = {"server": f"{p.scheme}://{p.hostname}:{p.port}"}
    if p.username:
        out["username"] = p.username
    if p.password:
        out["password"] = p.password
    return out


def main() -> None:
    headless = parse_bool(os.getenv("CAMOU_HEADLESS", "true"), True)
    port = int(os.getenv("CAMOU_PORT", "9222"))
    ws_path = os.getenv("CAMOU_WS_PATH", "camoufox")
    proxy = parse_proxy(os.getenv("PROXY_URL") or os.getenv("REGISTER_PROXY_URL"))
    disable_coop = parse_bool(os.getenv("CAMOU_DISABLE_COOP", "true"), True)
    geoip = parse_bool(os.getenv("CAMOU_GEOIP", "true"), True)

    config = launch_options(
        headless=headless,
        port=port,
        ws_path=ws_path,
        proxy=proxy,
        disable_coop=disable_coop,
        geoip=geoip,
    )
    if config.get("proxy") is None:
        config.pop("proxy", None)

    nodejs = get_nodejs()
    payload = orjson.dumps(to_camel_case_dict(config))
    process = subprocess.Popen(
        [nodejs, str(LAUNCH_SCRIPT)],
        cwd=Path(nodejs).parent / "package",
        stdin=subprocess.PIPE,
        text=True,
    )
    if process.stdin:
        process.stdin.write(base64.b64encode(payload).decode())
        process.stdin.close()
    process.wait()
    raise RuntimeError("Server process terminated unexpectedly")


if __name__ == "__main__":
    main()
