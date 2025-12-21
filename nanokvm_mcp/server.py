"""FastMCP server for NanoKVM control."""

import logging
import os
from io import BytesIO
from typing import Literal

from mcp.server.fastmcp import FastMCP, Image
from PIL import Image as PILImage

from .client import NanoKVMClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastMCP server
mcp = FastMCP("NanoKVM")

# Global client instance (initialized on first use)
_client: NanoKVMClient | None = None


def get_client() -> NanoKVMClient:
    """Get or create NanoKVM client from environment variables."""
    global _client
    if _client is None:
        host = os.environ.get("NANOKVM_HOST")
        if not host:
            raise ValueError("NANOKVM_HOST environment variable is required")

        _client = NanoKVMClient(
            host=host,
            username=os.environ.get("NANOKVM_USER", "admin"),
            password=os.environ.get("NANOKVM_PASS", "admin"),
            screen_width=int(os.environ.get("NANOKVM_SCREEN_WIDTH", "1920")),
            screen_height=int(os.environ.get("NANOKVM_SCREEN_HEIGHT", "1080")),
            use_https=os.environ.get("NANOKVM_HTTPS", "").lower() == "true",
            verify_ssl=os.environ.get("NANOKVM_VERIFY_SSL", "true").lower() != "false",
        )
    return _client


# =============================================================================
# Power Control Tools
# =============================================================================


@mcp.tool()
async def nanokvm_power(
    action: Literal["power", "power_long", "reset"] = "power",
) -> str:
    """
    Control the target machine's power.

    Args:
        action: Power action to perform
            - "power": Short press power button (800ms) - normal on/off
            - "power_long": Long press power button (5000ms) - force off
            - "reset": Press reset button (DEPRECATED for Pi 5 - use power_cycle)

    Note: Raspberry Pi 5 has NO hardware reset button. The "reset" action
    will not work on Pi 5. Use nanokvm_power_cycle() instead.
    """
    client = get_client()

    if action == "power":
        await client.power_short()
        return "Power button pressed (short press)"
    elif action == "power_long":
        await client.power_long()
        return "Power button pressed (long press - force off)"
    elif action == "reset":
        await client.reset()
        return "Reset button pressed (NOTE: Does nothing on Pi 5 - use power_cycle)"
    else:
        raise ValueError(f"Invalid action: {action}")


@mcp.tool()
async def nanokvm_power_cycle(off_duration_ms: int = 3000) -> str:
    """
    Power cycle the target machine (force off, wait, power on).

    This is the recommended way to "reset" a Raspberry Pi 5 since
    it has no hardware reset button. The sequence is:
    1. Force power off (5 second button hold)
    2. Wait for specified duration
    3. Power on (short button press)

    Args:
        off_duration_ms: Time to wait after power off before powering on (ms).
                        Default 3000ms (3 seconds) ensures clean power cycle.
                        Use longer values (5000+) if you have slow storage.

    Returns:
        Status message indicating power cycle completion
    """
    client = get_client()
    await client.power_cycle(off_duration_ms)
    return f"Power cycle complete (waited {off_duration_ms}ms between off and on)"


@mcp.tool()
async def nanokvm_led_status() -> dict:
    """
    Get the power and HDD LED status of the target machine.

    Returns:
        Dictionary with 'pwr' and 'hdd' boolean values indicating LED states.
        - pwr: True if power LED is on (machine is powered)
        - hdd: True if HDD LED is on (disk activity)
    """
    client = get_client()
    return await client.get_led_status()


# =============================================================================
# HDMI Tools
# =============================================================================


@mcp.tool()
async def nanokvm_hdmi_status() -> dict:
    """
    Get HDMI connection status and resolution.

    Returns:
        Dictionary with HDMI state including:
        - connected: Whether HDMI signal is detected
        - width: Video width in pixels
        - height: Video height in pixels
    """
    client = get_client()
    return await client.get_hdmi_status()


@mcp.tool()
async def nanokvm_hdmi_reset() -> str:
    """
    Reset the HDMI connection. Useful if video is not displaying correctly.
    """
    client = get_client()
    await client.reset_hdmi()
    return "HDMI connection reset"


# =============================================================================
# Text Input Tools
# =============================================================================


@mcp.tool()
async def nanokvm_send_text(text: str, language: str = "") -> str:
    """
    Type text on the target machine via keyboard emulation.

    Uses the NanoKVM paste API which is faster than individual key presses.
    Maximum 1024 characters per call.

    Args:
        text: The text to type (max 1024 characters)
        language: Keyboard layout - "" for US QWERTY, "de" for German
    """
    client = get_client()
    await client.paste_text(text, language)
    return f"Typed {len(text)} characters"


@mcp.tool()
async def nanokvm_send_key(
    key: str,
    ctrl: bool = False,
    shift: bool = False,
    alt: bool = False,
    meta: bool = False,
) -> str:
    """
    Send a single key press to the target machine.

    Args:
        key: Key to press. Can be:
            - Named keys: enter, escape, tab, backspace, delete, space
            - Function keys: f1, f2, ..., f12
            - Arrow keys: up, down, left, right
            - Navigation: home, end, pageup, pagedown, insert
            - Single characters: a, b, 1, 2, etc.
        ctrl: Hold Ctrl modifier
        shift: Hold Shift modifier
        alt: Hold Alt modifier
        meta: Hold Meta/Windows/Command modifier
    """
    client = get_client()
    await client.send_key(key, ctrl=ctrl, shift=shift, alt=alt, meta=meta)

    modifiers = []
    if ctrl:
        modifiers.append("Ctrl")
    if shift:
        modifiers.append("Shift")
    if alt:
        modifiers.append("Alt")
    if meta:
        modifiers.append("Meta")

    if modifiers:
        return f"Sent {'+'.join(modifiers)}+{key}"
    return f"Sent {key}"


# =============================================================================
# Mouse/Touch Tools
# =============================================================================


@mcp.tool()
async def nanokvm_tap(x: int, y: int) -> str:
    """
    Tap at a specific screen position (touchscreen/mouse emulation).

    Coordinates are in screen pixels based on NANOKVM_SCREEN_WIDTH and
    NANOKVM_SCREEN_HEIGHT environment variables.

    Args:
        x: X coordinate (0 = left edge, screen_width = right edge)
        y: Y coordinate (0 = top edge, screen_height = bottom edge)
    """
    client = get_client()
    await client.tap(x, y)
    return f"Tapped at ({x}, {y})"


@mcp.tool()
async def nanokvm_click(
    button: Literal["left", "right", "middle"] = "left",
    x: int | None = None,
    y: int | None = None,
) -> str:
    """
    Click a mouse button, optionally at a specific position.

    Args:
        button: Mouse button - "left", "right", or "middle"
        x: Optional X coordinate to move to before clicking
        y: Optional Y coordinate to move to before clicking
    """
    client = get_client()
    await client.mouse_click(button, x, y)

    if x is not None and y is not None:
        return f"{button.capitalize()} clicked at ({x}, {y})"
    return f"{button.capitalize()} clicked"


@mcp.tool()
async def nanokvm_move(x: int, y: int) -> str:
    """
    Move mouse cursor to absolute screen position.

    Args:
        x: X coordinate (0 = left edge)
        y: Y coordinate (0 = top edge)
    """
    client = get_client()
    await client.mouse_move(x, y)
    return f"Mouse moved to ({x}, {y})"


@mcp.tool()
async def nanokvm_scroll(amount: int) -> str:
    """
    Scroll the mouse wheel.

    Args:
        amount: Scroll amount. Positive = scroll down, negative = scroll up.
    """
    client = get_client()
    await client.mouse_scroll(amount)
    direction = "down" if amount > 0 else "up"
    return f"Scrolled {direction} by {abs(amount)}"


# =============================================================================
# Screenshot Tool
# =============================================================================


@mcp.tool()
async def nanokvm_screenshot(
    max_width: int = 1920,
    max_height: int = 1080,
    quality: int = 80,
) -> Image:
    """
    Capture a screenshot from the target machine's display.

    Returns the screenshot as a JPEG image that can be displayed or analyzed.
    By default, 4K images are resized to 1080p to keep the response size
    manageable.

    Args:
        max_width: Maximum width in pixels (default 1920, use 0 for no limit)
        max_height: Maximum height in pixels (default 1080, use 0 for no limit)
        quality: JPEG quality 1-100 (default 80)

    Returns:
        JPEG image of the current display
    """
    client = get_client()

    # Get raw JPEG bytes from the MJPEG stream
    jpeg_data = await client.screenshot()

    # Resize if needed
    if max_width > 0 or max_height > 0:
        img = PILImage.open(BytesIO(jpeg_data))
        original_width, original_height = img.size

        # Calculate new size maintaining aspect ratio
        new_width, new_height = original_width, original_height

        if max_width > 0 and original_width > max_width:
            ratio = max_width / original_width
            new_width = max_width
            new_height = int(original_height * ratio)

        if max_height > 0 and new_height > max_height:
            ratio = max_height / new_height
            new_height = max_height
            new_width = int(new_width * ratio)

        if (new_width, new_height) != (original_width, original_height):
            img = img.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
            logger.debug(
                f"Resized screenshot: {original_width}x{original_height} -> {new_width}x{new_height}"
            )

        # Re-encode with specified quality
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        jpeg_data = buffer.getvalue()

    # Return using FastMCP's Image type for proper MCP image handling
    return Image(data=jpeg_data, format="jpeg")


# =============================================================================
# Storage Tools
# =============================================================================


@mcp.tool()
async def nanokvm_list_images() -> list[dict]:
    """
    List available ISO images on the NanoKVM device.

    Returns:
        List of available images with file paths and metadata
    """
    client = get_client()
    return await client.list_images()


@mcp.tool()
async def nanokvm_mount_iso(file: str, as_cdrom: bool = True) -> str:
    """
    Mount an ISO image for the target machine.

    The target machine will see this as an attached CD-ROM or USB disk.

    Args:
        file: Path to ISO file on the NanoKVM device
        as_cdrom: Mount as CD-ROM (True) or USB disk (False)
    """
    client = get_client()
    await client.mount_image(file, as_cdrom)
    return f"Mounted {file} as {'CD-ROM' if as_cdrom else 'USB disk'}"


@mcp.tool()
async def nanokvm_unmount_iso() -> str:
    """
    Unmount the currently mounted ISO image.
    """
    client = get_client()
    await client.unmount_image()
    return "ISO unmounted"


@mcp.tool()
async def nanokvm_mounted_image() -> dict | None:
    """
    Get information about the currently mounted ISO image.

    Returns:
        Dictionary with mounted image info, or None if nothing mounted
    """
    client = get_client()
    return await client.get_mounted_image()


# =============================================================================
# HID Management Tools
# =============================================================================


@mcp.tool()
async def nanokvm_reset_hid() -> str:
    """
    Reset the HID (keyboard/mouse) devices.

    Use this if keyboard or mouse input stops working.
    """
    client = get_client()
    await client.reset_hid()
    return "HID devices reset"


# =============================================================================
# System Info Tools
# =============================================================================


@mcp.tool()
async def nanokvm_info() -> dict:
    """
    Get NanoKVM device information.

    Returns:
        Dictionary with device info including IP, firmware version, etc.
    """
    client = get_client()
    return await client.get_info()


@mcp.tool()
async def nanokvm_hardware() -> dict:
    """
    Get NanoKVM hardware information.

    Returns:
        Dictionary with hardware details
    """
    client = get_client()
    return await client.get_hardware()


# =============================================================================
# Server Entry Point
# =============================================================================


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
