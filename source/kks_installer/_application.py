"""Application policy. Content packages cannot expand these capabilities."""

APP_VERSION = "1.9.0"
BUILD_LABEL = "Candidate"
INSTALLER_API = 1
PROFILE = "fo76-steam-en-fonts-strings-v1"
WRITER = "ba2-v1-gnrl-kks-writer-v1"
CAPABILITIES = [WRITER]
TRANSLATION_PROFILE = "fo76-steam-en-fonts-strings-translate-v2"
TRANSLATION_CAPABILITY = "interface-translate-en-v1"
TRANSLATION_CAPABILITIES = [WRITER, TRANSLATION_CAPABILITY]
LOCALIZATION_PROFILE = "fo76-steam-en-fonts-strings-localization-v3"
LOCALIZATION_CAPABILITIES = [WRITER, "localization-translate-en-v1"]
GERMAN_PROFILE = "fo76-steam-de-fonts-strings-localization-v1"
GERMAN_CAPABILITIES = [WRITER, "localization-translate-de-v1"]
RUSSIAN_PROFILE = "fo76-steam-ru-fonts-strings-localization-v1"
RUSSIAN_OPTIONAL_CAPABILITY = "optional-features-ru-v1"
FR_DE_OPTIONAL_CAPABILITY = "optional-features-fr-de-v1"
FRENCH_PROFILE = "fo76-steam-fr-fonts-strings-localization-v1"
PORTUGUESE_PROFILE = "fo76-steam-ptbr-fonts-strings-localization-v1"
PORTUGUESE_OPTIONAL_CAPABILITY = "optional-features-ptbr-v1"
LOCALIZED_PROFILES = {"de": GERMAN_PROFILE, "ru": RUSSIAN_PROFILE, "fr": FRENCH_PROFILE, "ptbr": PORTUGUESE_PROFILE}
LEGACY_CONTENT_LANGUAGES = ("en", "de", "ru", "fr", "ptbr")
NEW_CONTENT_LANGUAGES = ("es", "esmx", "it", "ja", "ko", "pl", "zhhans", "zhhant")
LOCALIZED_PROFILES.update({lang: f"fo76-steam-{lang}-fonts-strings-localization-v1"
                           for lang in NEW_CONTENT_LANGUAGES})
CONTENT_LANGUAGES = LEGACY_CONTENT_LANGUAGES + NEW_CONTENT_LANGUAGES
CONTENT_NAMES = {"en": "English", "de": "Deutsch", "ru": "Русский", "fr": "Français",
                 "ptbr": "Português (Brasil)", "es": "Español", "esmx": "Español (Latinoamérica)",
                 "it": "Italiano", "ja": "日本語", "ko": "한국어", "pl": "Polski",
                 "zhhans": "简体中文", "zhhant": "繁體中文"}
FONT_LANGUAGES = {lang: lang if lang in ("ru", "ja", "ko", "zhhans", "zhhant") else "en"
                  for lang in CONTENT_LANGUAGES}
# Public verification keys only. Private signing keys never ship with the app.
TRUSTED_KEYS = {
    "kks-release-2026-10": "1ff7681dfa502f1478154b412b7f37a284cca141436022f6c76bd653f0685103"
}
