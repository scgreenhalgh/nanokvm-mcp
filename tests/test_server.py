"""Tests for the server module - FastMCP server and tools."""

import os
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from nanokvm_mcp import server
from nanokvm_mcp.server import (
    get_client,
    nanokvm_power,
    nanokvm_led_status,
    nanokvm_hdmi_status,
    nanokvm_hdmi_reset,
    nanokvm_send_text,
    nanokvm_send_key,
    nanokvm_tap,
    nanokvm_click,
    nanokvm_move,
    nanokvm_scroll,
    nanokvm_screenshot,
    nanokvm_list_images,
    nanokvm_mount_iso,
    nanokvm_unmount_iso,
    nanokvm_mounted_image,
    nanokvm_reset_hid,
    nanokvm_info,
    nanokvm_hardware,
)


class TestGetClient:
    """Tests for the get_client function."""

    @pytest.fixture(autouse=True)
    def reset_client(self):
        """Reset global client before each test."""
        server._client = None
        yield
        server._client = None

    @pytest.mark.unit
    def test_get_client_creates_client(self, mock_env):
        """get_client should create client from environment variables."""
        client = get_client()

        assert client is not None
        assert client.host == "192.168.1.100"
        assert client.username == "testuser"
        assert client.password == "testpass"
        assert client.screen_width == 1920
        assert client.screen_height == 1080

    @pytest.mark.unit
    def test_get_client_reuses_client(self, mock_env):
        """get_client should reuse existing client."""
        client1 = get_client()
        client2 = get_client()

        assert client1 is client2

    @pytest.mark.unit
    def test_get_client_missing_host_raises(self, clear_env):
        """get_client should raise if NANOKVM_HOST is missing."""
        with pytest.raises(ValueError, match="NANOKVM_HOST"):
            get_client()

    @pytest.mark.unit
    def test_get_client_uses_defaults(self, monkeypatch):
        """get_client should use defaults for optional env vars."""
        monkeypatch.setenv("NANOKVM_HOST", "10.0.0.1")
        # Don't set other vars

        client = get_client()

        assert client.host == "10.0.0.1"
        assert client.username == "admin"
        assert client.password == "admin"
        assert client.screen_width == 1920
        assert client.screen_height == 1080

    @pytest.mark.unit
    def test_get_client_https(self, monkeypatch):
        """get_client should support HTTPS mode."""
        monkeypatch.setenv("NANOKVM_HOST", "10.0.0.1")
        monkeypatch.setenv("NANOKVM_HTTPS", "true")

        client = get_client()

        assert client.base_url == "https://10.0.0.1"


class TestPowerTools:
    """Tests for power control MCP tools."""

    @pytest.fixture(autouse=True)
    def setup_mock_client(self, mock_env):
        """Set up mock client for all tests."""
        server._client = None
        yield
        server._client = None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_nanokvm_power_short(self):
        """nanokvm_power with action=power should short press."""
        with patch("nanokvm_mcp.server.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.power_short = AsyncMock()
            mock_get.return_value = mock_client

            result = await nanokvm_power(action="power")

            mock_client.power_short.assert_called_once()
            assert "short press" in result.lower()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_nanokvm_power_long(self):
        """nanokvm_power with action=power_long should long press."""
        with patch("nanokvm_mcp.server.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.power_long = AsyncMock()
            mock_get.return_value = mock_client

            result = await nanokvm_power(action="power_long")

            mock_client.power_long.assert_called_once()
            assert "long press" in result.lower() or "force" in result.lower()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_nanokvm_power_reset(self):
        """nanokvm_power with action=reset should reset."""
        with patch("nanokvm_mcp.server.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.reset = AsyncMock()
            mock_get.return_value = mock_client

            result = await nanokvm_power(action="reset")

            mock_client.reset.assert_called_once()
            assert "reset" in result.lower()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_nanokvm_led_status(self):
        """nanokvm_led_status should return LED states."""
        with patch("nanokvm_mcp.server.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get_led_status = AsyncMock(return_value={"pwr": True, "hdd": False})
            mock_get.return_value = mock_client

            result = await nanokvm_led_status()

            assert result["pwr"] is True
            assert result["hdd"] is False


class TestHDMITools:
    """Tests for HDMI control MCP tools."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_nanokvm_hdmi_status(self):
        """nanokvm_hdmi_status should return HDMI state."""
        with patch("nanokvm_mcp.server.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get_hdmi_status = AsyncMock(
                return_value={"state": 1, "width": 1920, "height": 1080}
            )
            mock_get.return_value = mock_client

            result = await nanokvm_hdmi_status()

            assert result["state"] == 1
            assert result["width"] == 1920

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_nanokvm_hdmi_reset(self):
        """nanokvm_hdmi_reset should reset HDMI."""
        with patch("nanokvm_mcp.server.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.reset_hdmi = AsyncMock()
            mock_get.return_value = mock_client

            result = await nanokvm_hdmi_reset()

            mock_client.reset_hdmi.assert_called_once()
            assert "reset" in result.lower()


class TestInputTools:
    """Tests for input MCP tools (keyboard, mouse)."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_nanokvm_send_text(self):
        """nanokvm_send_text should type text."""
        with patch("nanokvm_mcp.server.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.paste_text = AsyncMock()
            mock_get.return_value = mock_client

            result = await nanokvm_send_text("Hello World")

            mock_client.paste_text.assert_called_once_with("Hello World", "")
            assert "11" in result  # Length of "Hello World"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_nanokvm_send_text_with_language(self):
        """nanokvm_send_text should pass language parameter."""
        with patch("nanokvm_mcp.server.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.paste_text = AsyncMock()
            mock_get.return_value = mock_client

            await nanokvm_send_text("Grüß Gott", language="de")

            mock_client.paste_text.assert_called_once_with("Grüß Gott", "de")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_nanokvm_send_key_simple(self):
        """nanokvm_send_key should send key press."""
        with patch("nanokvm_mcp.server.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.send_key = AsyncMock()
            mock_get.return_value = mock_client

            result = await nanokvm_send_key("enter")

            mock_client.send_key.assert_called_once_with(
                "enter", ctrl=False, shift=False, alt=False, meta=False
            )
            assert "enter" in result.lower()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_nanokvm_send_key_with_modifiers(self):
        """nanokvm_send_key should include modifiers."""
        with patch("nanokvm_mcp.server.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.send_key = AsyncMock()
            mock_get.return_value = mock_client

            result = await nanokvm_send_key("c", ctrl=True)

            mock_client.send_key.assert_called_once_with(
                "c", ctrl=True, shift=False, alt=False, meta=False
            )
            assert "Ctrl" in result

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_nanokvm_tap(self):
        """nanokvm_tap should tap at coordinates."""
        with patch("nanokvm_mcp.server.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.tap = AsyncMock()
            mock_get.return_value = mock_client

            result = await nanokvm_tap(500, 300)

            mock_client.tap.assert_called_once_with(500, 300)
            assert "500" in result
            assert "300" in result

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_nanokvm_click(self):
        """nanokvm_click should click button."""
        with patch("nanokvm_mcp.server.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.mouse_click = AsyncMock()
            mock_get.return_value = mock_client

            result = await nanokvm_click(button="right", x=100, y=200)

            mock_client.mouse_click.assert_called_once_with("right", 100, 200)
            assert "Right" in result

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_nanokvm_move(self):
        """nanokvm_move should move cursor."""
        with patch("nanokvm_mcp.server.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.mouse_move = AsyncMock()
            mock_get.return_value = mock_client

            result = await nanokvm_move(800, 600)

            mock_client.mouse_move.assert_called_once_with(800, 600)
            assert "800" in result
            assert "600" in result

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_nanokvm_scroll(self):
        """nanokvm_scroll should scroll wheel."""
        with patch("nanokvm_mcp.server.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.mouse_scroll = AsyncMock()
            mock_get.return_value = mock_client

            result = await nanokvm_scroll(3)

            mock_client.mouse_scroll.assert_called_once_with(3)
            assert "down" in result.lower()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_nanokvm_scroll_up(self):
        """nanokvm_scroll should indicate up direction."""
        with patch("nanokvm_mcp.server.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.mouse_scroll = AsyncMock()
            mock_get.return_value = mock_client

            result = await nanokvm_scroll(-3)

            assert "up" in result.lower()


class TestScreenshotTool:
    """Tests for screenshot MCP tool."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_nanokvm_screenshot(self):
        """nanokvm_screenshot should return FastMCP Image object."""
        # Create a minimal valid JPEG (1x1 red pixel)
        # This is a real JPEG that PIL can parse
        minimal_jpeg = bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
            0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
            0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
            0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
            0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
            0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
            0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
            0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
            0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
            0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
            0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
            0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
            0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
            0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
            0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
            0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45,
            0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
            0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75,
            0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
            0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3,
            0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6,
            0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9,
            0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
            0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4,
            0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01,
            0x00, 0x00, 0x3F, 0x00, 0xFB, 0xD5, 0xDB, 0x20, 0xA8, 0xF1, 0x53, 0x16,
            0x5F, 0xFF, 0xD9
        ])

        with patch("nanokvm_mcp.server.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.screenshot = AsyncMock(return_value=minimal_jpeg)
            mock_get.return_value = mock_client

            result = await nanokvm_screenshot()

            mock_client.screenshot.assert_called_once()
            # Result should be a FastMCP Image object
            from mcp.server.fastmcp import Image as MCPImage
            assert isinstance(result, MCPImage)
            assert hasattr(result, 'data')
            # Data should start with JPEG magic bytes
            assert result.data[:2] == b'\xff\xd8'


class TestStorageTools:
    """Tests for storage MCP tools."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_nanokvm_list_images(self):
        """nanokvm_list_images should return image list."""
        with patch("nanokvm_mcp.server.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.list_images = AsyncMock(
                return_value=[{"name": "test.iso", "path": "/data/test.iso"}]
            )
            mock_get.return_value = mock_client

            result = await nanokvm_list_images()

            assert len(result) == 1
            assert result[0]["name"] == "test.iso"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_nanokvm_mount_iso(self):
        """nanokvm_mount_iso should mount image."""
        with patch("nanokvm_mcp.server.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.mount_image = AsyncMock()
            mock_get.return_value = mock_client

            result = await nanokvm_mount_iso("/data/ubuntu.iso", as_cdrom=True)

            mock_client.mount_image.assert_called_once_with("/data/ubuntu.iso", True)
            assert "ubuntu.iso" in result
            assert "CD-ROM" in result

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_nanokvm_mount_iso_as_disk(self):
        """nanokvm_mount_iso should mount as USB disk."""
        with patch("nanokvm_mcp.server.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.mount_image = AsyncMock()
            mock_get.return_value = mock_client

            result = await nanokvm_mount_iso("/data/disk.img", as_cdrom=False)

            mock_client.mount_image.assert_called_once_with("/data/disk.img", False)
            assert "USB disk" in result

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_nanokvm_unmount_iso(self):
        """nanokvm_unmount_iso should unmount image."""
        with patch("nanokvm_mcp.server.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.unmount_image = AsyncMock()
            mock_get.return_value = mock_client

            result = await nanokvm_unmount_iso()

            mock_client.unmount_image.assert_called_once()
            assert "unmount" in result.lower()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_nanokvm_mounted_image(self):
        """nanokvm_mounted_image should return mounted info."""
        with patch("nanokvm_mcp.server.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get_mounted_image = AsyncMock(
                return_value={"file": "/data/test.iso", "cdrom": True}
            )
            mock_get.return_value = mock_client

            result = await nanokvm_mounted_image()

            assert result["file"] == "/data/test.iso"


class TestSystemTools:
    """Tests for system MCP tools."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_nanokvm_reset_hid(self):
        """nanokvm_reset_hid should reset HID devices."""
        with patch("nanokvm_mcp.server.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.reset_hid = AsyncMock()
            mock_get.return_value = mock_client

            result = await nanokvm_reset_hid()

            mock_client.reset_hid.assert_called_once()
            assert "reset" in result.lower()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_nanokvm_info(self):
        """nanokvm_info should return device info."""
        with patch("nanokvm_mcp.server.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get_info = AsyncMock(
                return_value={"ip": "192.168.1.100", "image": "2.1.0"}
            )
            mock_get.return_value = mock_client

            result = await nanokvm_info()

            assert result["ip"] == "192.168.1.100"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_nanokvm_hardware(self):
        """nanokvm_hardware should return hardware info."""
        with patch("nanokvm_mcp.server.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get_hardware = AsyncMock(return_value={"type": "pro"})
            mock_get.return_value = mock_client

            result = await nanokvm_hardware()

            assert result["type"] == "pro"
