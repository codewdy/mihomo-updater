from config import Config


def apply_mixin(clash_config: dict, config: Config) -> dict:
    clash_config["mixed-port"] = config.port
    clash_config["allow-lan"] = config.allow_lan
    clash_config["external-controller"] = f"0.0.0.0:{config.api_port}"
    clash_config["secret"] = config.secret
    if (config.ui_url or "").strip():
        clash_config["external-ui"] = config.ui_subdir
    return clash_config
