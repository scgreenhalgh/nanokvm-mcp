"""Tests for the client module - NanoKVM API client."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from nanokvm_mcp.client import NanoKVMClient
from nanokvm_mcp.hid import MouseEvent, MouseButton


class TestNanoKVMClientInit:
    """Tests for NanoKVMClient initialization."""

    @pytest.mark.unit
    def test_init_with_defaults(self):
        """Client should initialize with default values."""
        client = NanoKVMClient(host="192.168.1.100")

        assert client.host == "192.168.1.100"
        assert client.username == "admin"
        assert client.password == "admin"
        assert client.screen_width == 1920
        assert client.screen_height == 1080
        assert client.base_url == "http://192.168.1.100"
        assert client.ws_url == "ws://192.168.1.100/api/ws"

    @pytest.mark.unit
    def test_init_with_custom_values(self):
        """Client should accept custom configuration."""
        client = NanoKVMClient(
            host="10.0.0.50",
            username="user1",
            password="secret",
            screen_width=1280,
            screen_height=720,
            use_https=True,
        )

        assert client.host == "10.0.0.50"
        assert client.username == "user1"
        assert client.password == "secret"
        assert client.screen_width == 1280
        assert client.screen_height == 720
        assert client.base_url == "https://10.0.0.50"
        assert client.ws_url == "wss://10.0.0.50/api/ws"

    @pytest.mark.unit
    def test_init_state(self):
        """Client should start with no active connections."""
        client = NanoKVMClient(host="192.168.1.100")

        assert client._token is None
        assert client._http_client is None
        assert client._ws is None


class TestNanoKVMClientAuthentication:
    """Tests for authentication functionality."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_ensure_authenticated_success(self, client):
        """Should authenticate and store token on success."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"code": 0, "msg": "success"}
        mock_response.cookies = httpx.Cookies()
        mock_response.cookies.set("nano-kvm-token", "test-token")
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_http_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_http.cookies = httpx.Cookies()
            mock_get_client.return_value = mock_http

            await client._ensure_authenticated()

            assert client._token == "test-token"
            mock_http.post.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_ensure_authenticated_already_authenticated(self, client):
        """Should not re-authenticate if token exists."""
        client._token = "existing-token"

        with patch.object(client, "_get_http_client") as mock_get_client:
            await client._ensure_authenticated()

            mock_get_client.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_ensure_authenticated_no_token_cookie(self, client):
        """Should handle responses without token cookie."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"code": 0, "msg": "success"}
        mock_response.cookies = httpx.Cookies()  # No token
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_http_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            # Should not raise - some NanoKVM versions don't require auth
            await client._ensure_authenticated()


class TestNanoKVMClientPowerControl:
    """Tests for power control methods."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_power_short(self, authenticated_client):
        """power_short should call power with 800ms duration."""
        with patch.object(authenticated_client, "power", new_callable=AsyncMock) as mock_power:
            mock_power.return_value = {"code": 0}

            result = await authenticated_client.power_short()

            mock_power.assert_called_once_with("power", 800)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_power_long(self, authenticated_client):
        """power_long should call power with 5000ms duration."""
        with patch.object(authenticated_client, "power", new_callable=AsyncMock) as mock_power:
            mock_power.return_value = {"code": 0}

            result = await authenticated_client.power_long()

            mock_power.assert_called_once_with("power", 5000)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_reset(self, authenticated_client):
        """reset should call power with reset type."""
        with patch.object(authenticated_client, "power", new_callable=AsyncMock) as mock_power:
            mock_power.return_value = {"code": 0}

            result = await authenticated_client.reset()

            mock_power.assert_called_once_with("reset", 800)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_power_request_format(self, authenticated_client):
        """power should send correct request format."""
        with patch.object(authenticated_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"code": 0}

            await authenticated_client.power("power", 800)

            mock_req.assert_called_once_with(
                "POST",
                "/api/vm/gpio",
                json={"type": "power", "duration": 800},
            )


class TestNanoKVMClientHDMI:
    """Tests for HDMI control methods."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_hdmi_status(self, authenticated_client, mock_hdmi_status_response):
        """get_hdmi_status should return HDMI state."""
        with patch.object(authenticated_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_hdmi_status_response

            result = await authenticated_client.get_hdmi_status()

            assert result["state"] == 1
            assert result["width"] == 1920
            assert result["height"] == 1080
            mock_req.assert_called_once_with("GET", "/api/vm/hdmi")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_reset_hdmi(self, authenticated_client):
        """reset_hdmi should call correct endpoint."""
        with patch.object(authenticated_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"code": 0}

            await authenticated_client.reset_hdmi()

            mock_req.assert_called_once_with("POST", "/api/vm/hdmi/reset")


class TestNanoKVMClientHID:
    """Tests for HID control methods."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_paste_text(self, authenticated_client):
        """paste_text should send text to paste endpoint."""
        with patch.object(authenticated_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"code": 0}

            await authenticated_client.paste_text("Hello World")

            mock_req.assert_called_once_with(
                "POST",
                "/api/hid/paste",
                json={"content": "Hello World", "langue": ""},
            )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_paste_text_german_layout(self, authenticated_client):
        """paste_text should support German keyboard layout."""
        with patch.object(authenticated_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"code": 0}

            await authenticated_client.paste_text("Grüß Gott", language="de")

            mock_req.assert_called_once_with(
                "POST",
                "/api/hid/paste",
                json={"content": "Grüß Gott", "langue": "de"},
            )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_paste_text_max_length(self, authenticated_client):
        """paste_text should reject text over 1024 characters."""
        with pytest.raises(ValueError, match="1024 characters"):
            await authenticated_client.paste_text("a" * 1025)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_reset_hid(self, authenticated_client):
        """reset_hid should call correct endpoint."""
        with patch.object(authenticated_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"code": 0}

            await authenticated_client.reset_hid()

            mock_req.assert_called_once_with("POST", "/api/hid/reset")


class TestNanoKVMClientWebSocketHID:
    """Tests for WebSocket HID methods."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_send_key_simple(self, authenticated_client, mock_websocket):
        """send_key should send correct WebSocket message."""
        with patch.object(authenticated_client, "_get_websocket", new_callable=AsyncMock) as mock_get_ws:
            mock_get_ws.return_value = mock_websocket

            await authenticated_client.send_key("enter")

            # Should send key down and key up
            assert mock_websocket.send.call_count == 2

            # Check key down message
            key_down = json.loads(mock_websocket.send.call_args_list[0][0][0])
            assert key_down[0] == 1  # Keyboard event type
            assert key_down[1] == 0x28  # Enter keycode

            # Check key up message
            key_up = json.loads(mock_websocket.send.call_args_list[1][0][0])
            assert key_up == [1, 0, 0, 0, 0, 0]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_send_key_with_modifiers(self, authenticated_client, mock_websocket):
        """send_key should include modifiers in message."""
        with patch.object(authenticated_client, "_get_websocket", new_callable=AsyncMock) as mock_get_ws:
            mock_get_ws.return_value = mock_websocket

            await authenticated_client.send_key("c", ctrl=True)

            key_down = json.loads(mock_websocket.send.call_args_list[0][0][0])
            assert key_down[0] == 1  # Keyboard event
            assert key_down[1] == 0x06  # 'c' keycode
            assert key_down[2] == 1  # Ctrl modifier

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_send_key_unknown_raises(self, authenticated_client):
        """send_key should raise for unknown keys."""
        with pytest.raises(ValueError, match="Unknown key"):
            await authenticated_client.send_key("unknownkey")


class TestNanoKVMClientMouse:
    """Tests for mouse control methods."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_mouse_move_coordinate_conversion(self, authenticated_client, mock_websocket):
        """mouse_move should convert screen coords to NanoKVM coords."""
        with patch.object(authenticated_client, "_get_websocket", new_callable=AsyncMock) as mock_get_ws:
            mock_get_ws.return_value = mock_websocket

            # Move to center of 1920x1080 screen
            await authenticated_client.mouse_move(960, 540)

            msg = json.loads(mock_websocket.send.call_args[0][0])

            assert msg[0] == 2  # Mouse event type
            assert msg[1] == MouseEvent.MOVE_ABSOLUTE
            assert msg[2] == MouseButton.NONE
            # Center should be approximately 0x3FFF (16383)
            assert 16000 < msg[3] < 17000  # X
            assert 16000 < msg[4] < 17000  # Y

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_mouse_move_corner_coords(self, authenticated_client, mock_websocket):
        """mouse_move should handle corner coordinates correctly."""
        with patch.object(authenticated_client, "_get_websocket", new_callable=AsyncMock) as mock_get_ws:
            mock_get_ws.return_value = mock_websocket

            # Top-left corner
            await authenticated_client.mouse_move(0, 0)
            msg = json.loads(mock_websocket.send.call_args[0][0])
            assert msg[3] == 1  # Min X
            assert msg[4] == 1  # Min Y

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_mouse_click(self, authenticated_client, mock_websocket):
        """mouse_click should send down and up events."""
        with patch.object(authenticated_client, "_get_websocket", new_callable=AsyncMock) as mock_get_ws:
            mock_get_ws.return_value = mock_websocket

            await authenticated_client.mouse_click("left")

            assert mock_websocket.send.call_count == 2

            down = json.loads(mock_websocket.send.call_args_list[0][0][0])
            assert down[0] == 2
            assert down[1] == MouseEvent.DOWN
            assert down[2] == MouseButton.LEFT

            up = json.loads(mock_websocket.send.call_args_list[1][0][0])
            assert up[1] == MouseEvent.UP

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_mouse_click_right(self, authenticated_client, mock_websocket):
        """mouse_click should support right button."""
        with patch.object(authenticated_client, "_get_websocket", new_callable=AsyncMock) as mock_get_ws:
            mock_get_ws.return_value = mock_websocket

            await authenticated_client.mouse_click("right")

            down = json.loads(mock_websocket.send.call_args_list[0][0][0])
            assert down[2] == MouseButton.RIGHT

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_tap(self, authenticated_client):
        """tap should be an alias for mouse_click with position."""
        with patch.object(authenticated_client, "mouse_click", new_callable=AsyncMock) as mock_click:
            await authenticated_client.tap(500, 300)

            mock_click.assert_called_once_with("left", 500, 300)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_mouse_scroll(self, authenticated_client, mock_websocket):
        """mouse_scroll should send scroll event."""
        with patch.object(authenticated_client, "_get_websocket", new_callable=AsyncMock) as mock_get_ws:
            mock_get_ws.return_value = mock_websocket

            await authenticated_client.mouse_scroll(3)

            msg = json.loads(mock_websocket.send.call_args[0][0])
            assert msg[0] == 2
            assert msg[1] == MouseEvent.SCROLL
            assert msg[4] == 3


class TestNanoKVMClientScreenshot:
    """Tests for screenshot functionality."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_screenshot_parses_mjpeg(self, authenticated_client, jpeg_frame):
        """screenshot should extract JPEG from MJPEG stream."""
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()

        async def mock_iter():
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg_frame

        mock_response.aiter_bytes = mock_iter
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(authenticated_client, "_ensure_authenticated", new_callable=AsyncMock):
            with patch.object(authenticated_client, "_get_http_client", new_callable=AsyncMock) as mock_client:
                mock_http = AsyncMock()
                mock_http.stream = MagicMock(return_value=mock_response)
                mock_client.return_value = mock_http

                result = await authenticated_client.screenshot()

                # Should return the JPEG data
                assert result.startswith(b'\xff\xd8')  # JPEG SOI
                assert result.endswith(b'\xff\xd9')  # JPEG EOI


class TestNanoKVMClientStorage:
    """Tests for storage management methods."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_images(self, authenticated_client):
        """list_images should return image list."""
        with patch.object(authenticated_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {
                "code": 0,
                "data": [
                    {"name": "ubuntu.iso", "path": "/data/ubuntu.iso"},
                    {"name": "debian.iso", "path": "/data/debian.iso"},
                ],
            }

            result = await authenticated_client.list_images()

            assert len(result) == 2
            assert result[0]["name"] == "ubuntu.iso"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_mount_image(self, authenticated_client):
        """mount_image should send correct request."""
        with patch.object(authenticated_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"code": 0}

            await authenticated_client.mount_image("/data/ubuntu.iso", cdrom=True)

            mock_req.assert_called_once_with(
                "POST",
                "/api/storage/image/mount",
                json={"file": "/data/ubuntu.iso", "cdrom": True},
            )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_unmount_image(self, authenticated_client):
        """unmount_image should send empty mount request."""
        with patch.object(authenticated_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"code": 0}

            await authenticated_client.unmount_image()

            mock_req.assert_called_once_with(
                "POST",
                "/api/storage/image/mount",
                json={},
            )


class TestNanoKVMClientClose:
    """Tests for connection cleanup."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_close_cleans_up(self, client):
        """close should clean up all connections."""
        mock_ws = AsyncMock()
        mock_http = AsyncMock()

        client._ws = mock_ws
        client._http_client = mock_http
        client._token = "test-token"

        await client.close()

        mock_ws.close.assert_called_once()
        mock_http.aclose.assert_called_once()
        assert client._ws is None
        assert client._http_client is None
        assert client._token is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_close_handles_no_connections(self, client):
        """close should handle case with no active connections."""
        # Should not raise
        await client.close()

        assert client._ws is None
        assert client._http_client is None
