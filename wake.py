"""Wake-word detection using openWakeWord.

A purpose-built wake-word neural model — far more accurate and far fewer false
triggers than phoneme/grammar spotting. Uses the shared melspectrogram +
embedding models plus a Silero VAD gate to reject non-speech.

config.OWW_MODEL may be a built-in name ("hey_jarvis", "alexa", ...) or a path
to a custom .onnx (e.g. a trained "hey_lumina.onnx").
"""
from openwakeword.model import Model

import config


class WakeDetector:
    def __init__(self):
        self.model = Model(
            wakeword_models=[config.OWW_MODEL],
            inference_framework="onnx",
            vad_threshold=config.OWW_VAD_THRESHOLD,
        )
        self.key = list(self.model.models.keys())[0]

    def score(self, frame_int16) -> float:
        """frame_int16: numpy int16 mono @16k. Returns wake confidence 0..1."""
        return self.model.predict(frame_int16).get(self.key, 0.0)

    def reset(self):
        self.model.reset()
