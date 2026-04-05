from config import Config


def apply_mixin(clash_config: dict, config: Config) -> dict:
    clash_config["mixed-port"] = config.port
    clash_config["allow-lan"] = config.allow_lan
    clash_config["external-controller"] = f"0.0.0.0:{config.api_port}"
    clash_config["secret"] = config.secret
    return clash_config
