"""Language helpers for multilingual Lumina.

Whisper returns a language *name* (e.g. "hindi"). We map it to an espeak-ng
voice code and a display name for the LLM, and pick a natural Piper voice when
we have one for that language.
"""

# Whisper language name -> (espeak voice code, display name)
_LANGS = {
    "english": ("en", "English"), "hindi": ("hi", "Hindi"),
    "spanish": ("es", "Spanish"), "french": ("fr", "French"),
    "german": ("de", "German"), "italian": ("it", "Italian"),
    "portuguese": ("pt", "Portuguese"), "russian": ("ru", "Russian"),
    "arabic": ("ar", "Arabic"), "chinese": ("zh", "Chinese"),
    "japanese": ("ja", "Japanese"), "korean": ("ko", "Korean"),
    "tamil": ("ta", "Tamil"), "telugu": ("te", "Telugu"),
    "bengali": ("bn", "Bengali"), "marathi": ("mr", "Marathi"),
    "gujarati": ("gu", "Gujarati"), "kannada": ("kn", "Kannada"),
    "punjabi": ("pa", "Punjabi"), "malayalam": ("ml", "Malayalam"),
    "urdu": ("ur", "Urdu"), "nepali": ("ne", "Nepali"),
    "dutch": ("nl", "Dutch"), "turkish": ("tr", "Turkish"),
    "indonesian": ("id", "Indonesian"), "vietnamese": ("vi", "Vietnamese"),
    "thai": ("th", "Thai"), "polish": ("pl", "Polish"),
}


def is_english(whisper_lang: str) -> bool:
    return (whisper_lang or "english").strip().lower() in ("english", "en", "")


def espeak_code(whisper_lang: str) -> str:
    return _LANGS.get((whisper_lang or "").strip().lower(), ("en", "English"))[0]


def display_name(whisper_lang: str) -> str:
    key = (whisper_lang or "").strip().lower()
    return _LANGS.get(key, (None, (whisper_lang or "English").title()))[1]
