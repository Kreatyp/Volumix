"""Spielt einen leisen Sinuston, damit eine Audio-Sitzung Pegel zeigt.

Aufruf: ton.py [dauer_sekunden]
"""
import math, os, struct, sys, tempfile, wave, winsound

dauer = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
rate, amp = 44100, 0.08
wav = os.path.join(tempfile.gettempdir(), "volumix_ton.wav")
with wave.open(wav, "w") as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(rate)
    f.writeframes(b"".join(
        struct.pack("<h", int(amp * 32767 * math.sin(2 * math.pi * 440 * i / rate)))
        for i in range(int(rate * dauer))))
winsound.PlaySound(wav, winsound.SND_FILENAME)
