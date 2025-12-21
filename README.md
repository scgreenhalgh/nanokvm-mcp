# NanoKVM MCP Server

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An MCP (Model Context Protocol) server for controlling [Sipeed NanoKVM](https://github.com/sipeed/NanoKVM) devices. This enables AI assistants like Claude to remotely control hardware via keyboard, mouse, power buttons, and screen capture.

## What is NanoKVM?

[NanoKVM](https://github.com/sipeed/NanoKVM) is an open-source, affordable IP-KVM device based on RISC-V. It allows remote access to computers at the BIOS level—perfect for managing servers, embedded systems, or any headless machine.

## What is MCP?

[Model Context Protocol](https://modelcontextprotocol.io/) is an open standard for connecting AI assistants to external tools and data sources. This server exposes NanoKVM functionality as MCP tools that Claude and other AI assistants can use.

## Features

| Category | Capabilities |
|----------|-------------|
| **Power Control** | Power on/off, reset, force shutdown via ATX header |
| **Keyboard** | Type text, send key combinations (Ctrl+C, Alt+F4, etc.) |
| **Mouse/Touch** | Click, move, scroll, tap at absolute screen coordinates |
| **Screenshots** | Capture display as JPEG from MJPEG video stream |
| **ISO Mounting** | Mount/unmount ISO images for remote OS installation |
| **Monitoring** | Power LED status, HDD activity, HDMI state, resolution |

## Installation

### From Source

```bash
git clone https://github.com/scgreenhalgh/nanokvm-mcp.git
cd nanokvm-mcp
pip install -e .
```

### Dependencies

- Python 3.10+
- `mcp` - Model Context Protocol SDK
- `httpx` - Async HTTP client
- `websockets` - WebSocket client for real-time HID
- `pycryptodome` - AES encryption for authentication
- `pillow` - Image processing for screenshots

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NANOKVM_HOST` | **Yes** | - | NanoKVM IP address or hostname |
| `NANOKVM_USER` | No | `admin` | Web UI username |
| `NANOKVM_PASS` | No | `admin` | Web UI password |
| `NANOKVM_SCREEN_WIDTH` | No | `1920` | Target screen width in pixels |
| `NANOKVM_SCREEN_HEIGHT` | No | `1080` | Target screen height in pixels |
| `NANOKVM_HTTPS` | No | `false` | Use HTTPS instead of HTTP |

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "nanokvm": {
      "command": "python",
      "args": ["-m", "nanokvm_mcp.server"],
      "env": {
        "NANOKVM_HOST": "192.168.1.100",
        "NANOKVM_USER": "admin",
        "NANOKVM_PASS": "admin",
        "NANOKVM_SCREEN_WIDTH": "1920",
        "NANOKVM_SCREEN_HEIGHT": "1080"
      }
    }
  }
}
```

### Claude Code

Add to your Claude Code MCP configuration:

```json
{
  "mcpServers": {
    "nanokvm": {
      "command": "python",
      "args": ["-m", "nanokvm_mcp.server"],
      "env": {
        "NANOKVM_HOST": "192.168.1.100"
      }
    }
  }
}
```

## Available MCP Tools

### Power Control

| Tool | Parameters | Description |
|------|------------|-------------|
| `nanokvm_power` | `action`: `power`, `power_long`, `reset` | Control power button or reset |
| `nanokvm_led_status` | - | Get power and HDD LED states |

**Actions:**
- `power` - Short press (800ms) - normal power on/off
- `power_long` - Long press (5000ms) - force power off
- `reset` - Press reset button

### Display

| Tool | Parameters | Description |
|------|------------|-------------|
| `nanokvm_hdmi_status` | - | Get HDMI connection state and resolution |
| `nanokvm_hdmi_reset` | - | Reset HDMI connection |
| `nanokvm_screenshot` | - | Capture display as base64 JPEG |

### Keyboard Input

| Tool | Parameters | Description |
|------|------------|-------------|
| `nanokvm_send_text` | `text`, `language` | Type text (max 1024 chars) |
| `nanokvm_send_key` | `key`, `ctrl`, `shift`, `alt`, `meta` | Send single key with modifiers |

**Supported Keys:**
- Letters: `a`-`z`
- Numbers: `0`-`9`
- Function keys: `f1`-`f12`
- Navigation: `up`, `down`, `left`, `right`, `home`, `end`, `pageup`, `pagedown`
- Control: `enter`, `escape`, `tab`, `backspace`, `delete`, `insert`, `space`

### Mouse/Touch Input

| Tool | Parameters | Description |
|------|------------|-------------|
| `nanokvm_tap` | `x`, `y` | Tap at screen coordinates |
| `nanokvm_click` | `button`, `x`, `y` | Click button, optionally at position |
| `nanokvm_move` | `x`, `y` | Move cursor to position |
| `nanokvm_scroll` | `amount` | Scroll wheel (positive=down) |

**Coordinate System:**
- Origin (0, 0) is top-left corner
- Coordinates are in screen pixels based on `SCREEN_WIDTH` and `SCREEN_HEIGHT`
- Internally mapped to NanoKVM's 1-32767 absolute coordinate range

### Storage

| Tool | Parameters | Description |
|------|------------|-------------|
| `nanokvm_list_images` | - | List available ISO images |
| `nanokvm_mount_iso` | `file`, `as_cdrom` | Mount ISO image |
| `nanokvm_unmount_iso` | - | Unmount current ISO |
| `nanokvm_mounted_image` | - | Get mounted image info |

### System

| Tool | Parameters | Description |
|------|------------|-------------|
| `nanokvm_reset_hid` | - | Reset keyboard/mouse devices |
| `nanokvm_info` | - | Get NanoKVM device info |
| `nanokvm_hardware` | - | Get hardware information |

## Usage Examples

Once configured, ask Claude to:

| Request | Tool Used |
|---------|-----------|
| "Is the server powered on?" | `nanokvm_led_status` |
| "Power on the machine" | `nanokvm_power` |
| "Reset the server" | `nanokvm_power` with `action="reset"` |
| "Force shutdown" | `nanokvm_power` with `action="power_long"` |
| "Type 'root' and press enter" | `nanokvm_send_text` + `nanokvm_send_key` |
| "Press Ctrl+Alt+Delete" | `nanokvm_send_key` with modifiers |
| "Take a screenshot" | `nanokvm_screenshot` |
| "Click at position 500, 300" | `nanokvm_click` |
| "Mount the Ubuntu ISO" | `nanokvm_mount_iso` |

## Programmatic Usage

You can also use the client library directly:

```python
import asyncio
from nanokvm_mcp import NanoKVMClient

async def main():
    # Initialize client
    client = NanoKVMClient(
        host="192.168.1.100",
        username="admin",
        password="admin",
        screen_width=1920,
        screen_height=1080,
    )

    try:
        # Check power status
        status = await client.get_led_status()
        print(f"Power LED: {status['pwr']}, HDD LED: {status['hdd']}")

        # Get HDMI info
        hdmi = await client.get_hdmi_status()
        print(f"Resolution: {hdmi['width']}x{hdmi['height']}")

        # Type some text
        await client.paste_text("Hello, World!")

        # Send Enter key
        await client.send_key("enter")

        # Take a screenshot
        screenshot = await client.screenshot()
        with open("screenshot.jpg", "wb") as f:
            f.write(screenshot)

        # Click at coordinates
        await client.tap(500, 300)

        # Power cycle
        await client.reset()

    finally:
        await client.close()

asyncio.run(main())
```

## API Reference

See [API_REFERENCE.md](API_REFERENCE.md) for complete documentation of the NanoKVM REST API and WebSocket protocol, including:

- Authentication (AES-256-CBC encryption)
- All REST endpoints with request/response formats
- WebSocket HID protocol for keyboard and mouse
- USB HID keycodes reference
- Direct SSH HID access via `/dev/hidg*`

## How It Works

### Architecture

```
┌─────────────────┐     HTTP/WS      ┌─────────────────┐
│   MCP Client    │◄────────────────►│    NanoKVM      │
│  (Claude, etc.) │                  │                 │
└────────┬────────┘                  │  ┌───────────┐  │
         │                           │  │ REST API  │  │
    MCP Protocol                     │  └───────────┘  │
         │                           │  ┌───────────┐  │
┌────────▼────────┐                  │  │ WebSocket │  │
│  nanokvm-mcp    │                  │  │   /api/ws │  │
│     Server      │                  │  └───────────┘  │
│                 │                  │  ┌───────────┐  │
│ • Power control │                  │  │   MJPEG   │  │
│ • HID input     │                  │  │  Stream   │  │
│ • Screenshots   │                  │  └───────────┘  │
└─────────────────┘                  └─────────────────┘
```

### Communication Methods

| Feature | Method | Endpoint |
|---------|--------|----------|
| Authentication | REST | `POST /api/auth/login` |
| Power control | REST | `POST /api/vm/gpio` |
| Text input | REST | `POST /api/hid/paste` |
| Key/Mouse events | WebSocket | `/api/ws` |
| Screenshots | REST | `GET /api/stream/mjpeg` (parsed) |
| ISO mounting | REST | `POST /api/storage/image/mount` |

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/scgreenhalgh/nanokvm-mcp.git
cd nanokvm-mcp

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

### Project Structure

```
nanokvm-mcp/
├── nanokvm_mcp/
│   ├── __init__.py      # Package exports
│   ├── server.py        # FastMCP server with tool definitions
│   ├── client.py        # NanoKVM API client (REST + WebSocket)
│   ├── auth.py          # AES password encryption
│   └── hid.py           # USB HID keycodes and helpers
├── pyproject.toml       # Package configuration
├── README.md            # This file
└── API_REFERENCE.md     # Complete API documentation
```

## Troubleshooting

### Connection Refused

1. Verify NanoKVM is reachable: `ping <NANOKVM_HOST>`
2. Check web UI is accessible: `http://<NANOKVM_HOST>`
3. Verify credentials are correct

### Authentication Failed

1. Default credentials are `admin`/`admin`
2. Check if password was changed in NanoKVM web UI
3. Authentication can be disabled in `/etc/kvm/server.yaml`

### HID Input Not Working

1. Try `nanokvm_reset_hid` tool
2. Check "Reset HID" in NanoKVM web UI
3. Verify USB cable connection to target machine
4. Check `/dev/hidg*` devices exist on NanoKVM via SSH

### Screenshot Timeout

1. Ensure HDMI is connected and signal detected
2. Check `nanokvm_hdmi_status` for connection state
3. Try `nanokvm_hdmi_reset` to reinitialize

## License

MIT

## Related Projects

- [Sipeed NanoKVM](https://github.com/sipeed/NanoKVM) - The hardware this server controls
- [Model Context Protocol](https://modelcontextprotocol.io/) - The protocol specification
- [FastMCP](https://gofastmcp.com/) - Python MCP framework
