"""阶段1验证脚本：配置加载、凭证隔离、健康检查与响应包络。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import ConfigError, get_model_credentials, load_config
from app.main import create_app, make_envelope

VALID_CONFIG = """\
app:
  name: 远川物流干线查单与异常响应智能体
  stage: 1
  env: dev
server:
  host: 127.0.0.1
  port: 8000
health:
  path: /health
model:
  base_url_env: YUANCHUAN_MODEL_BASE_URL
  api_key_env: YUANCHUAN_MODEL_API_KEY
"""


def test_load_config_success(tmp_path):
    """有效配置可加载。入参：tmp_path；出参：无；失败：断言报错。"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(VALID_CONFIG, encoding="utf-8")
    config = load_config(config_file)
    assert config["app"]["stage"] == 1
    assert config["health"]["path"] == "/health"


def test_load_config_rejects_hardcoded_secret(tmp_path):
    """硬编码密钥必须被拒绝。入参：tmp_path；出参：无；失败：未抛 ConfigError。"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        VALID_CONFIG + "  api_key: sk-should-not-be-here\n", encoding="utf-8"
    )
    with pytest.raises(ConfigError):
        load_config(config_file)


def test_credentials_only_from_env(monkeypatch, tmp_path):
    """凭证只读环境变量。入参：monkeypatch / tmp_path；出参：无；失败：断言报错。"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(VALID_CONFIG, encoding="utf-8")
    config = load_config(config_file)
    monkeypatch.setenv("YUANCHUAN_MODEL_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("YUANCHUAN_MODEL_API_KEY", "test-only-token")
    assert get_model_credentials(config) == (
        "https://example.invalid/v1",
        "test-only-token",
    )


def test_error_envelope():
    """错误码驱动 ok 判定。入参：无；出参：无；失败：断言报错。"""
    body = make_envelope(code="DATA_STALE", msg="超过一个刷新周期")
    assert body["ok"] is False
    assert body["error"] == {"code": "DATA_STALE", "msg": "超过一个刷新周期"}


def test_health_endpoint(tmp_path):
    """健康检查返回统一包络且不泄露凭证。入参：tmp_path；出参：无；失败：断言报错。"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(VALID_CONFIG, encoding="utf-8")
    client = TestClient(create_app(load_config(config_file)))
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["status"] == "ok"
    assert body["data"]["stage"] == 1
    assert body["error"] == {"code": "", "msg": ""}
    assert "api_key" not in response.text
