"""配置加载与凭证隔离。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
_REQUIRED_SECTIONS = ("app", "server", "health", "model")


class ConfigError(ValueError):
    """配置错误。入参：错误说明字符串；出参：异常对象；失败时：由调用方捕获并终止启动。"""


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """加载并校验 config.yaml。

    入参：path 配置文件路径，默认仓库根目录的 config.yaml。
    出参：配置字典。
    失败时：文件缺失、YAML 解析失败、必填段缺失或发现硬编码凭证时抛 ConfigError。
    """
    config_path = Path(path)
    try:
        raw = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"无法读取配置文件：{config_path}") from exc

    try:
        config = yaml.safe_load(raw) or {}
    except yaml.YAMLError as exc:
        raise ConfigError("config.yaml 不是合法 YAML") from exc

    if not isinstance(config, dict):
        raise ConfigError("config.yaml 顶层必须是映射")

    missing = [key for key in _REQUIRED_SECTIONS if key not in config]
    if missing:
        raise ConfigError(f"config.yaml 缺少必填段：{', '.join(missing)}")

    model = config.get("model")
    if not isinstance(model, dict):
        raise ConfigError("model 段必须是映射")

    # 安全审查：密钥或模型地址写进仓库就会泄露，且无法按环境轮换；
    # 因此这里拒绝一切内联凭证值，只允许出现环境变量名。
    for literal_key in ("api_key", "base_url", "token", "secret"):
        if literal_key in model:
            raise ConfigError(f"model.{literal_key} 禁止写死，请改用环境变量名")

    return config


def get_model_credentials(config: dict[str, Any]) -> tuple[str | None, str | None]:
    """读取模型接入的环境变量。

    入参：config 已加载的配置字典。
    出参：(base_url, api_key) 二元组；未设置的环境变量返回 None。
    失败时：model 段结构非法抛 ConfigError；本函数不发起任何模型请求。
    """
    model = config.get("model")
    if not isinstance(model, dict):
        raise ConfigError("model 段必须是映射")

    base_url_name = model.get("base_url_env")
    api_key_name = model.get("api_key_env")
    if not isinstance(base_url_name, str) or not isinstance(api_key_name, str):
        raise ConfigError("model.base_url_env / model.api_key_env 必须是环境变量名字符串")

    # 权限校验：只按配置声明的环境变量名读取，绝不回退到代码或仓库内的默认值，
    # 否则同一套凭证会被误用到所有环境。
    return os.environ.get(base_url_name), os.environ.get(api_key_name)
