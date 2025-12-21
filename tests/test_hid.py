"""Tests for the hid module - HID keycodes and helpers."""

import pytest

from nanokvm_mcp.hid import (
    KEYCODES,
    SHIFTED_CHARS,
    KeyboardModifier,
    KeyInfo,
    MouseButton,
    MouseEvent,
    char_to_keycode,
    get_key_info,
)


class TestKeyboardModifier:
    """Tests for KeyboardModifier enum."""

    @pytest.mark.unit
    def test_modifier_values(self):
        """Verify modifier bit values match NanoKVM protocol."""
        assert KeyboardModifier.NONE == 0
        assert KeyboardModifier.CTRL_LEFT == 1
        assert KeyboardModifier.SHIFT_LEFT == 2
        assert KeyboardModifier.ALT_LEFT == 4
        assert KeyboardModifier.META_LEFT == 8
        assert KeyboardModifier.CTRL_RIGHT == 16
        assert KeyboardModifier.SHIFT_RIGHT == 32
        assert KeyboardModifier.ALT_RIGHT == 64
        assert KeyboardModifier.META_RIGHT == 128

    @pytest.mark.unit
    def test_modifiers_are_combinable(self):
        """Modifiers should be combinable with bitwise OR."""
        combined = KeyboardModifier.CTRL_LEFT | KeyboardModifier.SHIFT_LEFT
        assert combined == 3

        combined = KeyboardModifier.CTRL_LEFT | KeyboardModifier.ALT_LEFT | KeyboardModifier.SHIFT_LEFT
        assert combined == 7


class TestMouseEvent:
    """Tests for MouseEvent enum."""

    @pytest.mark.unit
    def test_mouse_event_values(self):
        """Verify mouse event values match NanoKVM protocol."""
        assert MouseEvent.DOWN == 1
        assert MouseEvent.UP == 2
        assert MouseEvent.MOVE_ABSOLUTE == 3
        assert MouseEvent.SCROLL == 4
        assert MouseEvent.MOVE_RELATIVE == 5


class TestMouseButton:
    """Tests for MouseButton enum."""

    @pytest.mark.unit
    def test_mouse_button_values(self):
        """Verify mouse button values match NanoKVM protocol."""
        assert MouseButton.NONE == 0
        assert MouseButton.LEFT == 0
        assert MouseButton.MIDDLE == 1
        assert MouseButton.RIGHT == 2


class TestKeycodes:
    """Tests for the KEYCODES dictionary."""

    @pytest.mark.unit
    def test_letter_keycodes(self):
        """Letter keys should have correct USB HID codes."""
        assert KEYCODES['a'] == 0x04
        assert KEYCODES['z'] == 0x1D
        assert KEYCODES['m'] == 0x10

    @pytest.mark.unit
    def test_number_keycodes(self):
        """Number keys should have correct USB HID codes."""
        assert KEYCODES['1'] == 0x1E
        assert KEYCODES['0'] == 0x27
        assert KEYCODES['5'] == 0x22

    @pytest.mark.unit
    def test_function_keycodes(self):
        """Function keys should have correct USB HID codes."""
        assert KEYCODES['f1'] == 0x3A
        assert KEYCODES['f12'] == 0x45
        assert KEYCODES['f11'] == 0x44

    @pytest.mark.unit
    def test_special_keycodes(self):
        """Special keys should have correct USB HID codes."""
        assert KEYCODES['enter'] == 0x28
        assert KEYCODES['return'] == 0x28  # Alias
        assert KEYCODES['escape'] == 0x29
        assert KEYCODES['esc'] == 0x29  # Alias
        assert KEYCODES['backspace'] == 0x2A
        assert KEYCODES['tab'] == 0x2B
        assert KEYCODES['space'] == 0x2C

    @pytest.mark.unit
    def test_arrow_keycodes(self):
        """Arrow keys should have correct USB HID codes."""
        assert KEYCODES['up'] == 0x52
        assert KEYCODES['down'] == 0x51
        assert KEYCODES['left'] == 0x50
        assert KEYCODES['right'] == 0x4F

    @pytest.mark.unit
    def test_navigation_keycodes(self):
        """Navigation keys should have correct USB HID codes."""
        assert KEYCODES['home'] == 0x4A
        assert KEYCODES['end'] == 0x4D
        assert KEYCODES['pageup'] == 0x4B
        assert KEYCODES['pagedown'] == 0x4E
        assert KEYCODES['insert'] == 0x49
        assert KEYCODES['delete'] == 0x4C

    @pytest.mark.unit
    def test_modifier_keycodes(self):
        """Modifier keys should have correct USB HID codes."""
        assert KEYCODES['ctrl'] == 0xE0
        assert KEYCODES['shift'] == 0xE1
        assert KEYCODES['alt'] == 0xE2
        assert KEYCODES['meta'] == 0xE3
        assert KEYCODES['win'] == 0xE3  # Alias
        assert KEYCODES['cmd'] == 0xE3  # Alias


class TestShiftedChars:
    """Tests for the SHIFTED_CHARS dictionary."""

    @pytest.mark.unit
    def test_uppercase_letters(self):
        """Uppercase letters should map to lowercase keycodes."""
        assert SHIFTED_CHARS['A'] == 0x04  # Same as 'a'
        assert SHIFTED_CHARS['Z'] == 0x1D  # Same as 'z'

    @pytest.mark.unit
    def test_shifted_numbers(self):
        """Shifted number symbols should map to number keycodes."""
        assert SHIFTED_CHARS['!'] == 0x1E  # Shift+1
        assert SHIFTED_CHARS['@'] == 0x1F  # Shift+2
        assert SHIFTED_CHARS['#'] == 0x20  # Shift+3
        assert SHIFTED_CHARS['$'] == 0x21  # Shift+4
        assert SHIFTED_CHARS['%'] == 0x22  # Shift+5
        assert SHIFTED_CHARS['^'] == 0x23  # Shift+6
        assert SHIFTED_CHARS['&'] == 0x24  # Shift+7
        assert SHIFTED_CHARS['*'] == 0x25  # Shift+8
        assert SHIFTED_CHARS['('] == 0x26  # Shift+9
        assert SHIFTED_CHARS[')'] == 0x27  # Shift+0

    @pytest.mark.unit
    def test_shifted_punctuation(self):
        """Shifted punctuation should have correct mappings."""
        assert SHIFTED_CHARS['_'] == 0x2D  # Shift+-
        assert SHIFTED_CHARS['+'] == 0x2E  # Shift+=
        assert SHIFTED_CHARS['{'] == 0x2F  # Shift+[
        assert SHIFTED_CHARS['}'] == 0x30  # Shift+]
        assert SHIFTED_CHARS['|'] == 0x31  # Shift+\
        assert SHIFTED_CHARS[':'] == 0x33  # Shift+;
        assert SHIFTED_CHARS['"'] == 0x34  # Shift+'
        assert SHIFTED_CHARS['~'] == 0x35  # Shift+`
        assert SHIFTED_CHARS['<'] == 0x36  # Shift+,
        assert SHIFTED_CHARS['>'] == 0x37  # Shift+.
        assert SHIFTED_CHARS['?'] == 0x38  # Shift+/


class TestGetKeyInfo:
    """Tests for the get_key_info function."""

    @pytest.mark.unit
    def test_get_key_info_lowercase_letter(self):
        """Lowercase letters should return KeyInfo without shift."""
        info = get_key_info('a')

        assert info is not None
        assert info.code == 0x04
        assert info.shift is False

    @pytest.mark.unit
    def test_get_key_info_uppercase_letter(self):
        """Uppercase letters should return KeyInfo with shift."""
        info = get_key_info('A')

        assert info is not None
        assert info.code == 0x04
        assert info.shift is True

    @pytest.mark.unit
    def test_get_key_info_named_key(self):
        """Named keys should be found case-insensitively."""
        info = get_key_info('Enter')

        assert info is not None
        assert info.code == 0x28
        assert info.shift is False

    @pytest.mark.unit
    def test_get_key_info_function_key(self):
        """Function keys should be recognized."""
        info = get_key_info('F11')

        assert info is not None
        assert info.code == 0x44
        assert info.shift is False

    @pytest.mark.unit
    def test_get_key_info_shifted_symbol(self):
        """Shifted symbols should return KeyInfo with shift."""
        info = get_key_info('!')

        assert info is not None
        assert info.code == 0x1E
        assert info.shift is True

    @pytest.mark.unit
    def test_get_key_info_unshifted_symbol(self):
        """Unshifted symbols should return KeyInfo without shift."""
        info = get_key_info('-')

        assert info is not None
        assert info.code == 0x2D
        assert info.shift is False

    @pytest.mark.unit
    def test_get_key_info_unknown_key(self):
        """Unknown keys should return None."""
        info = get_key_info('unknownkey')

        assert info is None

    @pytest.mark.unit
    def test_get_key_info_number(self):
        """Number characters should be recognized."""
        info = get_key_info('5')

        assert info is not None
        assert info.code == 0x22
        assert info.shift is False


class TestCharToKeycode:
    """Tests for the char_to_keycode function."""

    @pytest.mark.unit
    def test_char_to_keycode_space(self):
        """Space character should return space keycode."""
        result = char_to_keycode(' ')

        assert result is not None
        assert result[0] == KEYCODES['space']
        assert result[1] == 0

    @pytest.mark.unit
    def test_char_to_keycode_newline(self):
        """Newline should return enter keycode."""
        result = char_to_keycode('\n')

        assert result is not None
        assert result[0] == KEYCODES['enter']
        assert result[1] == 0

    @pytest.mark.unit
    def test_char_to_keycode_tab(self):
        """Tab should return tab keycode."""
        result = char_to_keycode('\t')

        assert result is not None
        assert result[0] == KEYCODES['tab']
        assert result[1] == 0

    @pytest.mark.unit
    def test_char_to_keycode_lowercase(self):
        """Lowercase letters should not have shift modifier."""
        result = char_to_keycode('a')

        assert result is not None
        assert result[0] == 0x04
        assert result[1] == 0

    @pytest.mark.unit
    def test_char_to_keycode_uppercase(self):
        """Uppercase letters should have shift modifier."""
        result = char_to_keycode('A')

        assert result is not None
        assert result[0] == 0x04
        assert result[1] == KeyboardModifier.SHIFT_LEFT

    @pytest.mark.unit
    def test_char_to_keycode_shifted_symbol(self):
        """Shifted symbols should have shift modifier."""
        result = char_to_keycode('@')

        assert result is not None
        assert result[0] == 0x1F
        assert result[1] == KeyboardModifier.SHIFT_LEFT

    @pytest.mark.unit
    def test_char_to_keycode_unmappable(self):
        """Unmappable characters should return None."""
        result = char_to_keycode('©')  # Copyright symbol

        assert result is None

    @pytest.mark.unit
    def test_char_to_keycode_number(self):
        """Number characters should not have shift modifier."""
        result = char_to_keycode('7')

        assert result is not None
        assert result[0] == 0x24
        assert result[1] == 0


class TestKeyInfo:
    """Tests for the KeyInfo named tuple."""

    @pytest.mark.unit
    def test_keyinfo_creation(self):
        """KeyInfo should be creatable with code and shift."""
        info = KeyInfo(code=0x04, shift=True)

        assert info.code == 0x04
        assert info.shift is True

    @pytest.mark.unit
    def test_keyinfo_default_shift(self):
        """KeyInfo should default shift to False."""
        info = KeyInfo(code=0x04)

        assert info.code == 0x04
        assert info.shift is False

    @pytest.mark.unit
    def test_keyinfo_is_tuple(self):
        """KeyInfo should be unpacked like a tuple."""
        info = KeyInfo(code=0x04, shift=True)
        code, shift = info

        assert code == 0x04
        assert shift is True
