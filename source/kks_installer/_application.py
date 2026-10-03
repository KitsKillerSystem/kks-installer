"""Application policy. Content packages cannot expand these capabilities."""

APP_VERSION = "1.2.0"
INSTALLER_API = 1
PROFILE = "fo76-steam-en-fonts-strings-v1"
WRITER = "ba2-v1-gnrl-kks-writer-v1"
CAPABILITIES = [WRITER]
TRANSLATION_PROFILE = "fo76-steam-en-fonts-strings-translate-v2"
TRANSLATION_CAPABILITY = "interface-translate-en-v1"
TRANSLATION_CAPABILITIES = [WRITER, TRANSLATION_CAPABILITY]
# Public verification keys only. Private signing keys never ship with the app.
TRUSTED_KEYS = {
    "kks-release-2026-10": "1ff7681dfa502f1478154b412b7f37a284cca141436022f6c76bd653f0685103"
}
