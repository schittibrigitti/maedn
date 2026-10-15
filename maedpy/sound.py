import atexit
import io
import math
import os
import struct
import tempfile
import tkinter as tk
import wave
from tkinter import ttk

try:
    import winsound
except ImportError:
    winsound = None

MAX_VOLUME_LEVEL = 3
LEVEL_AMPLITUDES = {1: 0.15, 2: 0.45, 3: 0.9}
SAMPLE_RATE = 44100
PING_FREQUENCY = 1320
PING_SECONDS = 0.4

_ping_cache = {}


def make_ping_wav(level):
    """Return WAV bytes of a decaying ping, or None when level is 0 (muted)."""
    amplitude = LEVEL_AMPLITUDES.get(level)
    if amplitude is None:
        return None
    if level not in _ping_cache:
        frames = bytearray()
        for i in range(int(SAMPLE_RATE * PING_SECONDS)):
            t = i / SAMPLE_RATE
            envelope = math.exp(-9 * t) * min(1.0, t / 0.003)
            wave_value = (
                math.sin(2 * math.pi * PING_FREQUENCY * t)
                + 0.3 * math.sin(2 * math.pi * 2 * PING_FREQUENCY * t)
            ) / 1.3
            frames += struct.pack('<h', int(32767 * amplitude * envelope * wave_value))
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(bytes(frames))
        _ping_cache[level] = buffer.getvalue()
    return _ping_cache[level]


_ping_files = {}


def _ping_path(level):
    if level not in _ping_files:
        data = make_ping_wav(level)
        handle = tempfile.NamedTemporaryFile(
            prefix=f'maedn_ping{level}_', suffix='.wav', delete=False
        )
        with handle:
            handle.write(data)
        _ping_files[level] = handle.name
        atexit.register(_remove_file, handle.name)
    return _ping_files[level]


def _remove_file(path):
    try:
        os.remove(path)
    except OSError:
        pass


def play_ping(level):
    if make_ping_wav(level) is None or winsound is None:
        return
    try:
        # SND_ASYNC does not work with SND_MEMORY, so play from a cached file
        winsound.PlaySound(_ping_path(level), winsound.SND_FILENAME | winsound.SND_ASYNC)
    except (RuntimeError, OSError):
        pass


class VolumeButton(tk.Canvas):
    """Speaker icon; each click cycles the volume 0 -> 1 -> 2 -> 3 -> 0."""

    def __init__(self, master, level=2, on_change=None):
        background = ttk.Style().lookup('TFrame', 'background') or 'white'
        super().__init__(
            master, width=40, height=28, background=background,
            highlightthickness=0, cursor='hand2'
        )
        self.level = level
        self.on_change = on_change
        self.bind('<Button-1>', self._on_click)
        self.redraw()

    def _on_click(self, event=None):
        self.set_level((self.level + 1) % (MAX_VOLUME_LEVEL + 1))

    def set_level(self, level):
        self.level = level
        self.redraw()
        if self.on_change is not None:
            self.on_change(level)

    def redraw(self):
        self.delete('all')
        color = '#1f2937'
        self.create_polygon(3, 10, 9, 10, 17, 3, 17, 25, 9, 18, 3, 18, fill=color, outline=color)
        if self.level == 0:
            self.create_line(21, 8, 35, 20, fill='#dc2626', width=3)
            self.create_line(21, 20, 35, 8, fill='#dc2626', width=3)
            return
        for wave_number in range(1, self.level + 1):
            radius = 5 + wave_number * 5
            self.create_arc(
                17 - radius, 14 - radius, 17 + radius, 14 + radius,
                start=-40, extent=80, style='arc', outline=color, width=2
            )
