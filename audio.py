"""Background microphone capture — the fix for 'input overflow'.

The old design read the mic on the same thread that also ran the recognizer and
(worse) blocked for seconds during TTS. Whenever that thread was busy, ALSA's
buffer filled and dropped audio -> garbled speech.

Here a sounddevice callback runs on PortAudio's own thread and does nothing but
copy each frame into a queue. The device is therefore drained continuously and
never overflows, no matter what the main loop is doing. Consumers pull frames
from the queue at their leisure; if they fall behind (e.g. during a long TTS
reply) the oldest frames are dropped instead of overflowing the hardware.
"""
import queue
import sys

import numpy as np
import sounddevice as sd

import config

FRAME = 1600  # 0.1 s @ 16 kHz — capture granularity


class AudioCapture:
    def __init__(self, max_seconds: float = 30.0):
        self._q: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=int(max_seconds / 0.1))
        self._stream = None
        self._open()

    def _open(self):
        self._stream = sd.InputStream(
            device=config.INPUT_DEVICE_INDEX,
            samplerate=config.SAMPLE_RATE,
            channels=config.CAPTURE_CHANNELS,
            dtype="int16",
            blocksize=FRAME,
            callback=self._cb,
        )

    def _cb(self, indata, frames, time_info, status):
        # Runs on PortAudio's thread. Keep it tiny: copy channel 0 and enqueue.
        mono = indata[:, 0].copy()
        try:
            self._q.put_nowait(mono)
        except queue.Full:
            # Consumer is behind (long reply). Drop oldest, keep newest.
            try:
                self._q.get_nowait()
                self._q.put_nowait(mono)
            except queue.Empty:
                pass

    def start(self):
        self._stream.start()

    def stop(self):
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    @property
    def live(self) -> bool:
        return self._stream is not None

    def pause(self):
        """Close the input stream so the OS hands the microphone back.

        Muting has to mean the mic is *off*, not that we quietly ignore what it
        hears — so we release the ALSA device entirely rather than just dropping
        frames. On the reSpeaker the LED ring goes dark, which is the honest
        signal a guest at the table needs.
        """
        if self._stream is None:
            return
        self.stop()
        self.flush()

    def resume(self):
        if self._stream is not None:
            return
        self._open()
        self._stream.start()
        self.flush()

    def read(self, timeout: float = 1.0) -> np.ndarray:
        """Return the next 0.1 s frame of int16 mono audio."""
        return self._q.get(timeout=timeout)

    def flush(self):
        """Discard everything buffered (call after speaking so we don't record
        our own voice / stale audio)."""
        with self._q.mutex:
            self._q.queue.clear()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()
