"""Pytest fixtures and configuration for NanoKVM MCP tests."""

import asyncio
import json
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from nanokvm_mcp.client import NanoKVMClient


# =============================================================================
# Mock Response Factories
# =============================================================================


def make_api_response(data: Any = None, code: int = 0, msg: str = "success") -> dict:
    """Create a standard NanoKVM API response."""
    return {"code": code, "msg": msg, "data": data}


def make_http_response(
    data: dict,
    status_code: int = 200,
    cookies: dict | None = None,
) -> httpx.Response:
    """Create a mock httpx.Response."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = data
    response.raise_for_status = MagicMock()
    response.cookies = cookies or {}
    return response


# =============================================================================
# Client Fixtures
# =============================================================================


@pytest.fixture
def client_config() -> dict:
    """Default client configuration for tests."""
    return {
        "host": "192.168.1.100",
        "username": "admin",
        "password": "admin",
        "screen_width": 1920,
        "screen_height": 1080,
        "use_https": False,
    }


@pytest.fixture
def client(client_config: dict) -> NanoKVMClient:
    """Create a NanoKVMClient instance for testing."""
    return NanoKVMClient(**client_config)


@pytest.fixture
def authenticated_client(client: NanoKVMClient) -> NanoKVMClient:
    """Create a pre-authenticated client."""
    client._token = "test-token-12345"
    return client


# =============================================================================
# HTTP Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_http_client() -> AsyncMock:
    """Create a mock httpx.AsyncClient."""
    mock = AsyncMock(spec=httpx.AsyncClient)
    mock.cookies = httpx.Cookies()
    return mock


@pytest.fixture
def mock_login_response() -> httpx.Response:
    """Mock successful login response."""
    response = make_http_response(
        data=make_api_response(),
        cookies={"nano-kvm-token": "test-token-12345"},
    )
    response.cookies = httpx.Cookies()
    response.cookies.set("nano-kvm-token", "test-token-12345")
    return response


@pytest.fixture
def mock_led_status_response() -> dict:
    """Mock LED status response data."""
    return make_api_response(data={"pwr": True, "hdd": False})


@pytest.fixture
def mock_hdmi_status_response() -> dict:
    """Mock HDMI status response data."""
    return make_api_response(data={"state": 1, "width": 1920, "height": 1080})


@pytest.fixture
def mock_device_info_response() -> dict:
    """Mock device info response data."""
    return make_api_response(
        data={
            "ip": "192.168.1.100",
            "mdns": "nanokvm.local",
            "image": "2.1.0",
            "application": "2.1.0",
            "device_key": "abc123",
        }
    )


# =============================================================================
# WebSocket Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_websocket() -> AsyncMock:
    """Create a mock WebSocket connection."""
    ws = AsyncMock()
    ws.closed = False
    ws.send = AsyncMock()
    ws.recv = AsyncMock(return_value=json.dumps({"status": "ok"}))
    ws.close = AsyncMock()
    return ws


# =============================================================================
# MJPEG Stream Fixtures
# =============================================================================


@pytest.fixture
def jpeg_frame() -> bytes:
    """Minimal valid JPEG data for testing."""
    # Minimal JPEG: SOI + APP0 + minimal data + EOI
    return (
        b'\xff\xd8'  # SOI (Start of Image)
        b'\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'  # APP0
        b'\xff\xdb\x00C\x00'  # DQT
        + b'\x08' * 64  # Quantization table
        + b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00'  # SOF0
        + b'\xff\xc4\x00\x1f\x00'  # DHT
        + b'\x00' * 28  # Huffman table
        + b'\xff\xda\x00\x08\x01\x01\x00\x00?\x00'  # SOS
        + b'\x7f'  # Minimal scan data
        + b'\xff\xd9'  # EOI (End of Image)
    )


@pytest.fixture
def mjpeg_stream(jpeg_frame: bytes) -> bytes:
    """Mock MJPEG stream with boundary markers."""
    boundary = b"--frame\r\n"
    content_type = b"Content-Type: image/jpeg\r\n\r\n"
    return boundary + content_type + jpeg_frame + b"\r\n"


# =============================================================================
# Environment Fixtures
# =============================================================================


@pytest.fixture
def mock_env(monkeypatch) -> dict:
    """Set up mock environment variables."""
    env = {
        "NANOKVM_HOST": "192.168.1.100",
        "NANOKVM_USER": "testuser",
        "NANOKVM_PASS": "testpass",
        "NANOKVM_SCREEN_WIDTH": "1920",
        "NANOKVM_SCREEN_HEIGHT": "1080",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return env


@pytest.fixture
def clear_env(monkeypatch) -> None:
    """Clear NanoKVM environment variables."""
    for key in [
        "NANOKVM_HOST",
        "NANOKVM_USER",
        "NANOKVM_PASS",
        "NANOKVM_SCREEN_WIDTH",
        "NANOKVM_SCREEN_HEIGHT",
        "NANOKVM_HTTPS",
    ]:
        monkeypatch.delenv(key, raising=False)
