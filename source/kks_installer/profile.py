"""Released KKS 1.0.0: exact English SWF/config archive targets and three string tables."""

import json
from .engine import Installer as BaseInstaller
from .platforms import SafetyError

FONT_ARCHIVE = "Data/SeventySix - Interface_en.ba2"
CONFIG_ARCHIVE = "Data/SeventySix - Interface.ba2"
STRINGS = {f"Data/strings/seventysix_en.{ext}" for ext in ["strings", "dlstrings", "ilstrings"]}
PRIOR_STATES = {
    ".kks-installer-1.0.0-rc.1": "KKS Installer 1.0.0-rc.1",
    ".kks-installer-0.1.2": "KKS Installer 0.1.2 (Final QA)",
    ".kks-installer-0.1.1": "the previous KKS Installer 0.1.1",
    ".kks-installer": "KKSInstaller.exe from installer 0.1.0",
    ".kks-font-diagnostic": "KKSFontTest.exe (SWF isolation test)",
    ".kks-fontconfig-coverage-test": "KKSFontConfigTest.exe (coverage test)",
}


class Installer(BaseInstaller):
    def __init__(self, game, release, log=None):
        if set(release.by_path) != {FONT_ARCHIVE, CONFIG_ARCHIVE} | STRINGS:
            raise SafetyError(
                "This release must manage exactly two English font/config archives and three string tables"
            )
        for archive, asset in [
            (FONT_ARCHIVE, "interface/fonts_en.swf"),
            (CONFIG_ARCHIVE, "interface/fontconfig_en.txt"),
        ]:
            t = release.by_path[archive]
            if t["kind"] != "archive" or [a["name"] for a in t["assets"]] != [asset]:
                raise SafetyError("Unexpected embedded font/config target")
        if any(release.by_path[p]["kind"] != "loose" for p in STRINGS):
            raise SafetyError("String tables must use their established loose-file paths")
        identity = {i["path"] for i in release.data["identity"]}
        if identity != {
            "Fallout76.exe",
            "Data/SeventySix.esm",
            "Data/SeventySix - Localization.ba2",
        }:
            raise SafetyError(
                "The reviewed executable, ESM and localization identity fingerprints are required"
            )
        super().__init__(game, release, log)

    def _identity(self, *, skip_exe=False):
        # Resolve prior-installation state first to give a useful restoration instruction.
        for state, app in PRIOR_STATES.items():
            if self.target(state + "/pending.json").exists():
                raise SafetyError(
                    "Recover the previous interrupted operation with "
                    + app
                    + " before installing this release."
                )
            receipt = self.target(state + "/receipt.json")
            if receipt.is_file():
                try:
                    status = json.loads(receipt.read_bytes()).get("status")
                except Exception as e:
                    raise SafetyError(
                        "The previous installation receipt is unreadable: " + state
                    ) from e
                if status != "restored":
                    raise SafetyError(
                        "Use Restore in " + app + " first, then return to this installer."
                    )
        super()._identity(skip_exe=skip_exe)
        for relative in [
            "Data/interface/fonts_en.swf",
            "Data/interface/fontconfig_en.txt",
            "Data/interface/fontconfig.txt",
        ]:
            if self.target(relative).exists():
                raise SafetyError(
                    "A loose font override conflicts with the verified configuration: "
                    + relative
                    + ". Restore the earlier font installation first."
                )

    def inspect(self):
        result = super().inspect()
        result["font_strategy"] = (
            "Legendary final advances and spacer polished; unchanged UTF-8 custom-renaming fontconfig."
        )
        result["full_package_in_game_verified"] = True
        result["qa_candidate"] = False
        if result["status"] == "installed":
            result["message"] = "KKS 1.0.0 is installed and verified."
        return result
