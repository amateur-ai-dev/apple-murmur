import time
from unittest.mock import patch, MagicMock


def test_double_tap_within_interval_fires_callback():
    from murmur.hotkey import HotkeyListener
    fired = []
    listener = HotkeyListener(on_double_tap=lambda: fired.append(1), interval_ms=300)
    t0 = time.time()
    listener._on_press_time(t0)
    listener._on_press_time(t0 + 0.1)
    # Wait briefly for background thread
    time.sleep(0.05)
    assert len(fired) == 1


def test_single_tap_does_not_fire_callback():
    from murmur.hotkey import HotkeyListener
    fired = []
    listener = HotkeyListener(on_double_tap=lambda: fired.append(1), interval_ms=300)
    listener._on_press_time(time.time())
    assert len(fired) == 0


def test_two_taps_outside_interval_do_not_fire():
    from murmur.hotkey import HotkeyListener
    fired = []
    listener = HotkeyListener(on_double_tap=lambda: fired.append(1), interval_ms=300)
    t0 = time.time()
    listener._on_press_time(t0)
    listener._on_press_time(t0 + 0.5)  # 500ms — outside 300ms window
    assert len(fired) == 0


def test_triple_tap_fires_only_once():
    from murmur.hotkey import HotkeyListener
    fired = []
    listener = HotkeyListener(on_double_tap=lambda: fired.append(1), interval_ms=300)
    t0 = time.time()
    listener._on_press_time(t0)
    listener._on_press_time(t0 + 0.1)
    listener._on_press_time(t0 + 0.2)
    time.sleep(0.05)
    assert len(fired) == 1
