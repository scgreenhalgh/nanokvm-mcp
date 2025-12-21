# NanoKVM API Reference

Complete API documentation for Sipeed NanoKVM devices, reverse-engineered from the [NanoKVM GitHub repository](https://github.com/sipeed/NanoKVM) and community contributions ([Issue #90](https://github.com/sipeed/NanoKVM/issues/90)).

## Table of Contents

- [Authentication](#authentication)
- [Power Control (GPIO)](#power-control-gpio)
- [HDMI Control](#hdmi-control)
- [HID Control](#hid-control)
- [WebSocket HID Protocol](#websocket-hid-protocol)
- [Video Streaming](#video-streaming)
- [Storage Management](#storage-management)
- [Network](#network)
- [System Information](#system-information)
- [Virtual Devices](#virtual-devices)

---

## Authentication

All API endpoints (except login) require authentication via the `nano-kvm-token` cookie.

### Login

```
POST /api/auth/login
```

**Request Body:**
```json
{
  "username": "admin",
  "password": "<encrypted_password>"
}
```

**Password Encryption:**
- Algorithm: AES-256-CBC
- Key: `nanokvm-sipeed-2024` (zero-padded to 32 bytes)
- Format: Base64(IV + encrypted_data)

**Python Example:**
```python
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64, os

def encrypt_password(password: str) -> str:
    key = b"nanokvm-sipeed-2024" + b'\x00' * 13  # Pad to 32 bytes
    iv = os.urandom(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(password.encode(), AES.block_size))
    return base64.b64encode(iv + encrypted).decode()
```

**Response:**
```json
{
  "code": 0,
  "msg": "success"
}
```
- Sets cookie: `nano-kvm-token=<jwt_token>`

### Logout

```
POST /api/auth/logout
```

### Get Account Info

```
GET /api/auth/account
```

### Change Password

```
POST /api/auth/password
```

**Request Body:**
```json
{
  "old_password": "<encrypted>",
  "new_password": "<encrypted>"
}
```

### Check Password Status

```
GET /api/auth/password
```

---

## Power Control (GPIO)

### Press Power/Reset Button

```
POST /api/vm/gpio
```

**Request Body:**
```json
{
  "type": "power",
  "duration": 800
}
```

| Parameter | Type | Values | Description |
|-----------|------|--------|-------------|
| `type` | string | `power`, `reset` | Button to press |
| `duration` | int | milliseconds | Press duration |

**Common Durations:**
- `800` - Short press (normal power on/off)
- `5000` - Long press (force power off)

**Response:**
```json
{
  "code": 0,
  "msg": "success"
}
```

### Get LED Status

```
GET /api/vm/gpio/led
```

**Response:**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "pwr": true,
    "hdd": false
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `pwr` | bool | Power LED state (true = machine is on) |
| `hdd` | bool | HDD activity LED state |

### Get GPIO State

```
GET /api/vm/gpio
```

---

## HDMI Control

### Get HDMI Status

```
GET /api/vm/hdmi
```

**Response:**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "state": 1,
    "width": 1920,
    "height": 1080
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `state` | int | 1 = connected, 0 = disconnected |
| `width` | int | Video width in pixels |
| `height` | int | Video height in pixels |

### Reset HDMI

```
POST /api/vm/hdmi/reset
```

### Enable HDMI Capture

```
POST /api/vm/hdmi/enable
```

### Disable HDMI Capture

```
POST /api/vm/hdmi/disable
```

---

## HID Control

### Paste Text (Type)

```
POST /api/hid/paste
```

**Request Body:**
```json
{
  "content": "Hello World",
  "langue": ""
}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `content` | string | Text to type (max 1024 characters) |
| `langue` | string | Keyboard layout: `""` = US QWERTY, `"de"` = German |

**Notes:**
- Each character is sent as a HID keypress with 30ms delay
- Unknown characters are skipped

### Reset HID Devices

```
POST /api/hid/reset
```

Use this if keyboard/mouse stops responding.

### Get HID Mode

```
GET /api/hid/mode
```

**Response:**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "mode": "normal"
  }
}
```

### Set HID Mode

```
POST /api/hid/mode
```

**Request Body:**
```json
{
  "mode": "normal"
}
```

| Value | Description |
|-------|-------------|
| `normal` | Standard HID operation |
| `hid-only` | HID-only mode |

---

## WebSocket HID Protocol

Real-time keyboard and mouse input via WebSocket.

### Connection

```
GET /api/ws
```

**Headers:**
```
Cookie: nano-kvm-token=<token>
```

### Message Format

Messages are JSON arrays where the first element identifies the event type.

### Keyboard Events (Type = 1)

```json
[1, keycode, ctrl, shift, alt, meta]
```

| Index | Field | Description |
|-------|-------|-------------|
| 0 | type | Always `1` for keyboard |
| 1 | keycode | USB HID keycode (0 = release) |
| 2 | ctrl | Ctrl modifier (0, 1=left, 16=right) |
| 3 | shift | Shift modifier (0, 2=left, 32=right) |
| 4 | alt | Alt modifier (0, 4=left, 64=right) |
| 5 | meta | Meta/Win modifier (0, 8=left, 128=right) |

**Key Release:**
```json
[1, 0, 0, 0, 0, 0]
```

**Example - Press Enter:**
```json
[1, 40, 0, 0, 0, 0]
```

**Example - Ctrl+C:**
```json
[1, 6, 1, 0, 0, 0]
```

**Common Keycodes:**

| Key | Code | Key | Code |
|-----|------|-----|------|
| A-Z | 0x04-0x1D | Enter | 0x28 |
| 1-0 | 0x1E-0x27 | Escape | 0x29 |
| F1-F12 | 0x3A-0x45 | Backspace | 0x2A |
| Space | 0x2C | Tab | 0x2B |
| Up | 0x52 | Down | 0x51 |
| Left | 0x50 | Right | 0x4F |
| Delete | 0x4C | Insert | 0x49 |

### Mouse Events (Type = 2)

```json
[2, event, button, x, y]
```

| Index | Field | Description |
|-------|-------|-------------|
| 0 | type | Always `2` for mouse |
| 1 | event | Event type (see below) |
| 2 | button | Button identifier |
| 3 | x | X coordinate or delta |
| 4 | y | Y coordinate or delta |

**Event Types:**

| Value | Name | Description |
|-------|------|-------------|
| 1 | DOWN | Mouse button press |
| 2 | UP | Mouse button release |
| 3 | MOVE_ABSOLUTE | Move to absolute position |
| 4 | SCROLL | Mouse wheel scroll |
| 5 | MOVE_RELATIVE | Move by relative delta |

**Button Values:**

| Value | Button |
|-------|--------|
| 0 | Left / None |
| 1 | Middle (wheel) |
| 2 | Right |

**Absolute Coordinates:**
- Range: 1 to 32767 (0x7FFF)
- (1, 1) = top-left corner
- (32767, 32767) = bottom-right corner

**Conversion Formula:**
```python
kvm_x = int((screen_x / screen_width) * 0x7FFE) + 1
kvm_y = int((screen_y / screen_height) * 0x7FFE) + 1
```

**Examples:**

```json
// Left click at center
[2, 1, 0, 16384, 16384]  // Down
[2, 2, 0, 0, 0]          // Up

// Right click
[2, 1, 2, 0, 0]          // Down
[2, 2, 0, 0, 0]          // Up

// Move to position
[2, 3, 0, 16384, 16384]

// Scroll down
[2, 4, 0, 0, 1]

// Scroll up
[2, 4, 0, 0, -1]
```

---

## Video Streaming

### MJPEG Stream

```
GET /api/stream/mjpeg
```

**Response:**
- Content-Type: `multipart/x-mixed-replace; boundary=frame`
- Continuous JPEG frames separated by `--frame` boundary

**Screenshot from MJPEG:**
```python
async def screenshot(client, base_url, token):
    headers = {"Cookie": f"nano-kvm-token={token}"}
    async with client.stream("GET", f"{base_url}/api/stream/mjpeg", headers=headers) as r:
        buffer = b""
        async for chunk in r.aiter_bytes():
            buffer += chunk
            start = buffer.find(b'\xff\xd8')  # JPEG start
            end = buffer.find(b'\xff\xd9')    # JPEG end
            if start != -1 and end > start:
                return buffer[start:end+2]
```

### H.264 Stream (WebRTC)

```
GET /api/stream/h264
```

### H.264 Direct Stream

```
GET /api/stream/h264/direct
```

### Frame Detection Control

```
POST /api/stream/mjpeg/detect
```

**Request Body:**
```json
{
  "enabled": true
}
```

```
POST /api/stream/mjpeg/detect/stop
```

---

## Storage Management

### List ISO Images

```
GET /api/storage/image
```

**Response:**
```json
{
  "code": 0,
  "msg": "success",
  "data": [
    {
      "name": "ubuntu.iso",
      "path": "/data/ubuntu.iso",
      "size": 4700000000
    }
  ]
}
```

### Get Mounted Image

```
GET /api/storage/image/mounted
```

**Response:**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "file": "/data/ubuntu.iso",
    "cdrom": true
  }
}
```

### Mount Image

```
POST /api/storage/image/mount
```

**Request Body:**
```json
{
  "file": "/data/ubuntu.iso",
  "cdrom": true
}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `file` | string | Path to ISO on NanoKVM |
| `cdrom` | bool | Mount as CD-ROM (true) or USB disk (false) |

### Unmount Image

```
POST /api/storage/image/mount
```

**Request Body:**
```json
{}
```

### Delete Image

```
POST /api/storage/image/delete
```

**Request Body:**
```json
{
  "file": "/data/ubuntu.iso"
}
```

### Get CD-ROM Flag

```
GET /api/storage/cdrom
```

---

## Network

### Wake-on-LAN

```
POST /api/network/wol
```

**Request Body:**
```json
{
  "mac": "AA:BB:CC:DD:EE:FF"
}
```

### Get WoL MAC History

```
GET /api/network/wol/mac
```

### Delete MAC from History

```
DELETE /api/network/wol/mac
```

### Set MAC Name

```
POST /api/network/wol/mac/name
```

### Get WiFi Info

```
GET /api/network/wifi
```

### Connect to WiFi

```
POST /api/network/wifi
```

**Request Body:**
```json
{
  "ssid": "NetworkName",
  "password": "password123"
}
```

---

## System Information

### Get Device Info

```
GET /api/vm/info
```

**Response:**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "ip": "192.168.1.100",
    "mdns": "nanokvm.local",
    "image": "2.1.0",
    "application": "2.1.0",
    "device_key": "xxxxx"
  }
}
```

### Get Hardware Info

```
GET /api/vm/hardware
```

### Reboot NanoKVM

```
POST /api/vm/system/reboot
```

### SSH Control

```
GET /api/vm/ssh
POST /api/vm/ssh
```

**Request Body (POST):**
```json
{
  "enabled": true
}
```

### Memory Limit

```
GET /api/vm/memory-limit
POST /api/vm/memory-limit
```

### Swap Configuration

```
GET /api/vm/swap
POST /api/vm/swap
```

**Request Body (POST):**
```json
{
  "size": 256
}
```

### Hostname

```
GET /api/vm/hostname
POST /api/vm/hostname
```

### mDNS

```
GET /api/vm/mdns
POST /api/vm/mdns
```

### TLS/HTTPS

```
GET /api/vm/tls
POST /api/vm/tls
```

### OLED Display

```
GET /api/vm/oled
POST /api/vm/oled
```

---

## Virtual Devices

### Get Virtual Device Status

```
GET /api/vm/device/virtual
```

**Response:**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "network": true,
    "disk": true
  }
}
```

### Toggle Virtual Device

```
POST /api/vm/device/virtual
```

**Request Body:**
```json
{
  "device": "network"
}
```

| Value | Description |
|-------|-------------|
| `network` | Virtual network device |
| `disk` | Virtual disk device |

---

## SSH Access (Direct HID)

For low-level HID access via SSH (alternative to WebSocket):

### Keyboard (`/dev/hidg0`) - 8 bytes

```
[modifier, 0x00, key1, key2, key3, key4, key5, key6]
```

```bash
# Press Enter
echo -ne '\x00\x00\x28\x00\x00\x00\x00\x00' > /dev/hidg0
# Release
echo -ne '\x00\x00\x00\x00\x00\x00\x00\x00' > /dev/hidg0
```

### Mouse (`/dev/hidg1`) - 4 bytes

```
[buttons, x_delta, y_delta, wheel]
```

```bash
# Left click
echo -ne '\x01\x00\x00\x00' > /dev/hidg1
echo -ne '\x00\x00\x00\x00' > /dev/hidg1
```

### Touchscreen (`/dev/hidg2`) - 6 bytes

```
[button, x_low, x_high, y_low, y_high, wheel]
```

Coordinates: 0x0001 to 0x7FFF (little-endian)

```bash
# Tap center (0x3FFF = 16383)
echo -ne '\x01\xff\x3f\xff\x3f\x00' > /dev/hidg2
echo -ne '\x00\xff\x3f\xff\x3f\x00' > /dev/hidg2
```

---

## File System Paths

| Path | Description |
|------|-------------|
| `/kvmapp/kvm/state` | HDMI state (1=connected) |
| `/kvmapp/kvm/width` | Video width |
| `/kvmapp/kvm/height` | Video height |
| `/kvmapp/kvm/res` | Transmission resolution |
| `/kvmapp/kvm/fps` | Max frame rate |
| `/kvmapp/kvm/now_fps` | Current frame rate |
| `/etc/kvm/server.yaml` | Server configuration |
| `/etc/kvm/hw` | Hardware version |
| `/data/` | ISO image storage (~21GB) |

---

## Error Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| -1 | General error |
| -4 | Resolution change in progress |
| 401 | Unauthorized (token expired) |

---

## Configuration File

`/etc/kvm/server.yaml`:

```yaml
protocol: http
port: 80
https_port: 443
log_level: warn
authentication: enable  # or "disable"
```

---

## References

- [NanoKVM GitHub](https://github.com/sipeed/NanoKVM)
- [API Documentation Issue #90](https://github.com/sipeed/NanoKVM/issues/90)
- [Screenshot Request Issue #261](https://github.com/sipeed/NanoKVM/issues/261)
- [Sipeed Wiki](https://wiki.sipeed.com/hardware/en/kvm/NanoKVM/development.html)
- [USB HID Usage Tables](https://usb.org/sites/default/files/hut1_22.pdf)
