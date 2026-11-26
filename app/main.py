"""FastAPI 应用入口：阶段1只提供配置加载与健康检查。"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from app.config import load_config


def make_envelope(
    data: dict[str, Any] | None = None, code: str = "", msg: str = ""
) -> dict[str, Any]:
    """构造统一响应包络。

    入参：data 业务数据；code 错误码；msg 错误说明。
    出参：含 ok / data / error 的字典。
    失败时：code 非空即视为失败，调用方不得把 data 当作有效结果。
    """
    return {
        "ok": not code,
        "data": data or {},
        "error": {"code": code, "msg": msg},
    }


def create_app(config: dict[str, Any] | None = None) -> FastAPI:
    """创建应用实例。

    入参：config 已加载的配置；None 时从默认 config.yaml 加载。
    出参：FastAPI 实例。
    失败时：配置非法抛 ConfigError，进程不应带病启动。
    """
    cfg = config if config is not None else load_config()
    application = FastAPI(
        title=cfg["app"]["name"], version=f"stage-{cfg['app']['stage']}"
    )
    health_path = cfg["health"]["path"]

    @application.get(health_path)
    def health() -> dict[str, Any]:
        """健康检查。

        入参：无。
        出参：统一响应包络，data 含 status / app / stage。
        失败时：配置已在启动时校验，运行时不返回业务数据或凭证。
        """
        # 权限校验：对未认证调用者只暴露运行状态，不暴露模型地址、密钥或运单数据。
        return make_envelope(
            data={
                "status": "ok",
                "app": cfg["app"]["name"],
                "stage": cfg["app"]["stage"],
            }
        )

    return application


app = create_app()
