"""NanoKVM API client with REST, WebSocket, and screenshot support."""

import asyncio
import base64
import json
import logging
from io import BytesIO
from typing import Any

import httpx
import websockets
from PIL import Image

from .auth import encrypt_password
from .hid import (
    KEYCODES,
    KeyboardModifier,
    MouseButton,
    MouseEvent,
    char_to_keycode,
    get_key_info,
)

logger = logging.getLogger(__name__)


class NanoKVMClient:
    """Async client for NanoKVM REST API, WebSocket HID, and video capture."""

    def __init__(
        self,
        host: str,
        username: str = "admin",
        password: str = "admin",
        screen_width: int = 1920,
        screen_height: int = 1080,
        use_https: bool = False,
        verify_ssl: bool = True,
    ):
        """
        Initialize NanoKVM client.

        Args:
            host: NanoKVM IP address or hostname
            username: Web UI username (default: admin)
            password: Web UI password (default: admin)
            screen_width: Target screen width for coordinate mapping
            screen_height: Target screen height for coordinate mapping
            use_https: Use HTTPS instead of HTTP
            verify_ssl: Verify SSL certificates (set False for self-signed certs)
        """
        self.host = host
        self.username = username
        self.password = password
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.verify_ssl = verify_ssl

        protocol = "https" if use_https else "http"
        self.base_url = f"{protocol}://{host}"
        self.ws_url = f"{'wss' if use_https else 'ws'}://{host}/api/ws"

        self._token: str | None = None
        self._http_client: httpx.AsyncClient | None = None
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._ws_lock = asyncio.Lock()

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with authentication."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                follow_redirects=True,
                verify=self.verify_ssl,
            )
        return self._http_client

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid authentication token."""
        if self._token is not None:
            return

        client = await self._get_http_client()
        encrypted_pass = encrypt_password(self.password)

        response = await client.post(
            "/api/auth/login",
            json={"username": self.username, "password": encrypted_pass},
        )
        response.raise_for_status()

        data = response.json()
        if data.get("code") != 0:
            raise Exception(f"Login failed: {data.get('msg', 'Unknown error')}")

        # Extract token - try cookies first, then JSON response
        token = response.cookies.get("nano-kvm-token")
        if not token:
            # Token may be in JSON response body
            token = data.get("data", {}).get("token")

        if token:
            self._token = token
            client.cookies.set("nano-kvm-token", token)
            logger.debug("Authentication successful")
        else:
            logger.warning("Login succeeded but no token received")

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make authenticated API request."""
        await self._ensure_authenticated()
        client = await self._get_http_client()

        response = await client.request(method, endpoint, **kwargs)
        response.raise_for_status()

        data = response.json()
        if data.get("code") != 0:
            raise Exception(f"API error: {data.get('msg', 'Unknown error')}")

        return data

    async def close(self) -> None:
        """Close all connections."""
        if self._ws:
            await self._ws.close()
            self._ws = None
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        self._token = None

    # -------------------------------------------------------------------------
    # Power Control
    # -------------------------------------------------------------------------

    async def power(self, action: str = "power", duration: int = 800) -> dict:
        """
        Control power button.

        Args:
            action: "power" for short press, "reset" for reset button
            duration: Press duration in ms (800=short, 5000=force off)

        Returns:
            API response data
        """
        return await self._request(
            "POST",
            "/api/vm/gpio",
            json={"type": action, "duration": duration},
        )

    async def power_short(self) -> dict:
        """Short press power button (800ms)."""
        return await self.power("power", 800)

    async def power_long(self) -> dict:
        """Long press power button (5000ms) - force off."""
        return await self.power("power", 5000)

    async def reset(self) -> dict:
        """
        Press reset button.

        DEPRECATED for Pi 5: The Raspberry Pi 5 has no hardware reset.
        Use power_cycle() instead for Pi 5.
        """
        return await self.power("reset", 800)

    async def power_cycle(self, off_duration_ms: int = 3000) -> dict:
        """
        Power cycle the target machine (force off, wait, power on).

        This is the recommended way to "reset" a Raspberry Pi 5 since
        it has no hardware reset button.

        Args:
            off_duration_ms: Time to wait after power off before powering on (ms).
                           Default 3000ms (3 seconds) ensures clean shutdown.

        Returns:
            API response from the final power-on command
        """
        # Force power off with 5 second hold
        await self.power_long()

        # Wait for specified duration
        await asyncio.sleep(off_duration_ms / 1000)

        # Power on with short press
        return await self.power_short()

    async def get_led_status(self) -> dict:
        """Get power and HDD LED status."""
        data = await self._request("GET", "/api/vm/gpio/led")
        return data.get("data", {})

    # -------------------------------------------------------------------------
    # HDMI Control
    # -------------------------------------------------------------------------

    async def get_hdmi_status(self) -> dict:
        """Get HDMI connection status and resolution."""
        data = await self._request("GET", "/api/vm/hdmi")
        return data.get("data", {})

    async def reset_hdmi(self) -> dict:
        """Reset HDMI connection."""
        return await self._request("POST", "/api/vm/hdmi/reset")

    async def enable_hdmi(self) -> dict:
        """Enable HDMI capture."""
        return await self._request("POST", "/api/vm/hdmi/enable")

    async def disable_hdmi(self) -> dict:
        """Disable HDMI capture."""
        return await self._request("POST", "/api/vm/hdmi/disable")

    # -------------------------------------------------------------------------
    # HID Control (REST API)
    # -------------------------------------------------------------------------

    async def paste_text(self, text: str, language: str = "") -> dict:
        """
        Type text using the paste API (max 1024 chars).

        Args:
            text: Text to type
            language: Keyboard layout ("de" for German, empty for US)

        Returns:
            API response data
        """
        if len(text) > 1024:
            raise ValueError("Text must be 1024 characters or less")

        return await self._request(
            "POST",
            "/api/hid/paste",
            json={"content": text, "langue": language},
        )

    async def reset_hid(self) -> dict:
        """Reset HID devices."""
        return await self._request("POST", "/api/hid/reset")

    async def get_hid_mode(self) -> str:
        """Get current HID mode ("normal" or "hid-only")."""
        data = await self._request("GET", "/api/hid/mode")
        return data.get("data", {}).get("mode", "normal")

    async def set_hid_mode(self, mode: str) -> dict:
        """Set HID mode ("normal" or "hid-only")."""
        return await self._request("POST", "/api/hid/mode", json={"mode": mode})

    # -------------------------------------------------------------------------
    # WebSocket HID Control
    # -------------------------------------------------------------------------

    async def _get_websocket(self) -> websockets.WebSocketClientProtocol:
        """Get or create WebSocket connection."""
        async with self._ws_lock:
            if self._ws is None or self._ws.closed:
                await self._ensure_authenticated()

                # Build cookie header
                cookies = f"nano-kvm-token={self._token}" if self._token else ""

                self._ws = await websockets.connect(
                    self.ws_url,
                    additional_headers={"Cookie": cookies} if cookies else None,
                )
                logger.debug("WebSocket connected")

            return self._ws

    async def _send_ws(self, message: list[int]) -> None:
        """Send WebSocket HID message."""
        ws = await self._get_websocket()
        await ws.send(json.dumps(message))

    async def send_key(
        self,
        key: str,
        ctrl: bool = False,
        shift: bool = False,
        alt: bool = False,
        meta: bool = False,
    ) -> None:
        """
        Send a key press via WebSocket.

        Args:
            key: Key name (e.g., 'enter', 'f1', 'a') or single character
            ctrl: Hold Ctrl
            shift: Hold Shift
            alt: Hold Alt
            meta: Hold Meta/Win/Cmd
        """
        key_info = get_key_info(key)
        if key_info is None:
            raise ValueError(f"Unknown key: {key}")

        keycode = key_info.code

        # Build modifier values
        ctrl_val = KeyboardModifier.CTRL_LEFT if ctrl else 0
        shift_val = KeyboardModifier.SHIFT_LEFT if (shift or key_info.shift) else 0
        alt_val = KeyboardModifier.ALT_LEFT if alt else 0
        meta_val = KeyboardModifier.META_LEFT if meta else 0

        # Key down: [1, keycode, ctrl, shift, alt, meta]
        await self._send_ws([1, keycode, ctrl_val, shift_val, alt_val, meta_val])

        # Small delay
        await asyncio.sleep(0.05)

        # Key up: [1, 0, 0, 0, 0, 0]
        await self._send_ws([1, 0, 0, 0, 0, 0])

    async def send_text_ws(self, text: str) -> None:
        """
        Type text character by character via WebSocket.

        For longer text, use paste_text() instead.

        Args:
            text: Text to type
        """
        for char in text:
            result = char_to_keycode(char)
            if result is None:
                logger.warning(f"Skipping unmappable character: {repr(char)}")
                continue

            keycode, modifier = result

            # Key down
            shift_val = modifier if modifier else 0
            await self._send_ws([1, keycode, 0, shift_val, 0, 0])

            await asyncio.sleep(0.03)

            # Key up
            await self._send_ws([1, 0, 0, 0, 0, 0])

            await asyncio.sleep(0.03)

    async def mouse_move(self, x: int, y: int) -> None:
        """
        Move mouse to absolute position.

        Args:
            x: X coordinate (0 to screen_width)
            y: Y coordinate (0 to screen_height)
        """
        # Convert screen coordinates to NanoKVM coordinates (1-32768)
        kvm_x = int((x / self.screen_width) * 0x7FFE) + 1
        kvm_y = int((y / self.screen_height) * 0x7FFE) + 1

        # Clamp values
        kvm_x = max(1, min(0x7FFF, kvm_x))
        kvm_y = max(1, min(0x7FFF, kvm_y))

        # [2, MoveAbsolute, button, x, y]
        await self._send_ws([2, MouseEvent.MOVE_ABSOLUTE, MouseButton.NONE, kvm_x, kvm_y])

    async def mouse_click(
        self,
        button: str = "left",
        x: int | None = None,
        y: int | None = None,
    ) -> None:
        """
        Click mouse button, optionally at specific position.

        Args:
            button: "left", "right", or "middle"
            x: Optional X coordinate to move to first
            y: Optional Y coordinate to move to first
        """
        button_map = {
            "left": MouseButton.LEFT,
            "right": MouseButton.RIGHT,
            "middle": MouseButton.MIDDLE,
        }
        btn = button_map.get(button.lower(), MouseButton.LEFT)

        if x is not None and y is not None:
            await self.mouse_move(x, y)
            await asyncio.sleep(0.05)

        # Mouse down
        await self._send_ws([2, MouseEvent.DOWN, btn, 0, 0])
        await asyncio.sleep(0.05)

        # Mouse up
        await self._send_ws([2, MouseEvent.UP, MouseButton.NONE, 0, 0])

    async def tap(self, x: int, y: int) -> None:
        """
        Tap at absolute screen position (touchscreen emulation).

        Args:
            x: X coordinate (0 to screen_width)
            y: Y coordinate (0 to screen_height)
        """
        await self.mouse_click("left", x, y)

    async def mouse_scroll(self, delta: int) -> None:
        """
        Scroll mouse wheel.

        Args:
            delta: Scroll amount (positive = down, negative = up)
        """
        await self._send_ws([2, MouseEvent.SCROLL, 0, 0, delta])

    # -------------------------------------------------------------------------
    # Screenshot
    # -------------------------------------------------------------------------

    async def screenshot(self, timeout: float = 5.0) -> bytes:
        """
        Capture screenshot from MJPEG stream.

        Uses the ?n=1 parameter to request a single frame, which is faster
        and less likely to disrupt other stream clients (like the web browser).

        Args:
            timeout: Maximum time to wait for a frame

        Returns:
            JPEG image data as bytes
        """
        await self._ensure_authenticated()
        client = await self._get_http_client()

        headers = {}
        if self._token:
            headers["Cookie"] = f"nano-kvm-token={self._token}"

        # Use ?n=1 to request a single frame - faster and less disruptive
        # than connecting to the continuous MJPEG stream
        async with client.stream(
            "GET",
            "/api/stream/mjpeg?n=1",
            headers=headers,
            timeout=timeout,
        ) as response:
            response.raise_for_status()

            buffer = b""
            async for chunk in response.aiter_bytes():
                buffer += chunk

                # Look for JPEG frame markers
                start = buffer.find(b'\xff\xd8')  # JPEG start
                if start == -1:
                    continue

                end = buffer.find(b'\xff\xd9', start)  # JPEG end
                if end == -1:
                    continue

                # Extract complete JPEG frame
                jpeg_data = buffer[start:end + 2]
                logger.debug(f"Captured screenshot: {len(jpeg_data)} bytes")
                return jpeg_data

        raise TimeoutError("Failed to capture screenshot frame")

    async def screenshot_base64(
        self,
        timeout: float = 5.0,
        max_width: int | None = None,
        max_height: int | None = None,
        quality: int = 85,
    ) -> str:
        """
        Capture screenshot and return as base64 string.

        Args:
            timeout: Maximum time to wait for a frame
            max_width: Maximum width (will resize proportionally if exceeded)
            max_height: Maximum height (will resize proportionally if exceeded)
            quality: JPEG quality (1-100, default 85)

        Returns:
            Base64 encoded JPEG image
        """
        jpeg_data = await self.screenshot(timeout)

        # Resize if needed
        if max_width or max_height:
            img = Image.open(BytesIO(jpeg_data))
            original_width, original_height = img.size

            # Calculate new size maintaining aspect ratio
            new_width, new_height = original_width, original_height

            if max_width and original_width > max_width:
                ratio = max_width / original_width
                new_width = max_width
                new_height = int(original_height * ratio)

            if max_height and new_height > max_height:
                ratio = max_height / new_height
                new_height = max_height
                new_width = int(new_width * ratio)

            if (new_width, new_height) != (original_width, original_height):
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logger.debug(f"Resized screenshot: {original_width}x{original_height} -> {new_width}x{new_height}")

            # Re-encode with specified quality
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=quality, optimize=True)
            jpeg_data = buffer.getvalue()

        return base64.b64encode(jpeg_data).decode('utf-8')

    async def screenshot_pil(self, timeout: float = 5.0) -> Image.Image:
        """
        Capture screenshot and return as PIL Image.

        Args:
            timeout: Maximum time to wait for a frame

        Returns:
            PIL Image object
        """
        jpeg_data = await self.screenshot(timeout)
        return Image.open(BytesIO(jpeg_data))

    # -------------------------------------------------------------------------
    # Storage
    # -------------------------------------------------------------------------

    async def list_images(self) -> list[dict]:
        """List available ISO images."""
        data = await self._request("GET", "/api/storage/image")
        return data.get("data", [])

    async def get_mounted_image(self) -> dict | None:
        """Get currently mounted image."""
        data = await self._request("GET", "/api/storage/image/mounted")
        return data.get("data")

    async def mount_image(self, file: str, cdrom: bool = True) -> dict:
        """
        Mount an ISO image.

        Args:
            file: Path to ISO file on NanoKVM
            cdrom: Mount as CD-ROM (True) or disk (False)

        Returns:
            API response data
        """
        return await self._request(
            "POST",
            "/api/storage/image/mount",
            json={"file": file, "cdrom": cdrom},
        )

    async def unmount_image(self) -> dict:
        """Unmount currently mounted image."""
        return await self._request("POST", "/api/storage/image/mount", json={})

    # -------------------------------------------------------------------------
    # System Info
    # -------------------------------------------------------------------------

    async def get_info(self) -> dict:
        """Get NanoKVM device information."""
        data = await self._request("GET", "/api/vm/info")
        return data.get("data", {})

    async def get_hardware(self) -> dict:
        """Get hardware information."""
        data = await self._request("GET", "/api/vm/hardware")
        return data.get("data", {})

    async def reboot_nanokvm(self) -> dict:
        """Reboot the NanoKVM device itself."""
        return await self._request("POST", "/api/vm/system/reboot")
