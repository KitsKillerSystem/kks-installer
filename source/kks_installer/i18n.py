"""Local interface language only; never selects or edits a game/content language."""

from pathlib import Path
import ctypes, json, os, re, uuid

DE = {
    "Vanilla files restored. Backups retained.": "Originaldateien wiederhergestellt. Sicherungen bleiben erhalten.",
    "KKS installed and verified.": "KKS installiert und geprüft.",
    "Recovery needs attention: ": "Wiederherstellung muss geprüft werden: ",
    "Backups and journals are retained.": "Sicherungen und Wiederherstellungsprotokolle bleiben erhalten.",
    "KKS is installed and verified.": "KKS ist installiert und geprüft.",
    "Known files were reset or removed. Repair can restore KKS.": "Bekannte Dateien wurden zurückgesetzt oder entfernt. „Reparieren“ kann KKS wiederherstellen.",
    "This installation is compatible and ready.": "Diese Installation ist kompatibel und bereit.",
    "Content language: German. Set Fallout 76 to Deutsch in Steam.": "Inhaltssprache: Deutsch. Stelle Fallout 76 in Steam auf Deutsch.",
    "Content language: English.": "Inhaltssprache: Englisch.",
    "CONTENT\nINSTALLER": "MOD-\nINSTALLER",
    "A BETTER-ORDERED WASTELAND.": "ORDNUNG FÜRS ÖDLAND.",
    "Make yourself at home.": "Willkommen im Ödland.",
    "Choose your game folder and a complete KKS content ZIP.": "Wähle den Spielordner und eine vollständige KKS-Inhalts-ZIP.",
    "01  /  GAME DIRECTORY": "01  /  SPIELORDNER",
    "02  /  CONTENT PACKAGE": "02  /  INHALTSPAKET",
    "03  /  INSTALLATION STATUS": "03  /  INSTALLATIONSSTATUS",
    "ACTIVITY": "PROTOKOLL",
    "Browse…": "Durchsuchen…",
    "Check": "Prüfen",
    "Choose package…": "Paket auswählen…",
    "Install content": "Installieren",
    "Repair": "Reparieren",
    "Restore vanilla": "Original wiederherstellen",
    "Install update": "Aktualisieren",
    "Recover previous state": "Zustand wiederherstellen",
    "Ready when you are.": "Bereit, wenn du es bist.",
    "Drop one content ZIP onto this window, or choose it below.": "Ziehe eine Inhalts-ZIP in dieses Fenster oder wähle sie unten aus.",
    "Drop a ZIP here or choose a package. Keep the ZIP unopened.": "Ziehe eine ZIP hierher oder wähle ein Paket. Die ZIP nicht entpacken.",
    "Select a package to check compatibility.": "Wähle ein Paket, um die Kompatibilität zu prüfen.",
    "Offline by design.  Your vanilla backups stay with your game.": "Funktioniert offline. Die Originalsicherungen bleiben im Spielordner.",
    "Use Choose package to select your content ZIP.": "Wähle deine Inhalts-ZIP über „Paket auswählen“.",
    "Choose the folder containing Fallout76.exe": "Wähle den Ordner mit Fallout76.exe",
    "Choose a complete KKS content ZIP": "Wähle eine vollständige KKS-Inhalts-ZIP",
    "KKS content package": "KKS-Inhaltspaket",
    "Choose one ZIP": "Eine ZIP auswählen",
    "Drop one complete KKS content ZIP.": "Ziehe genau eine vollständige KKS-Inhalts-ZIP hierher.",
    "Wait for the current operation, then drop the package again.": "Warte, bis der laufende Vorgang beendet ist, und ziehe das Paket dann erneut hierher.",
    "KKS is working": "KKS arbeitet",
    "Wait for the operation to finish. If it is interrupted, KKS keeps the recovery journal and backups.": "Warte, bis der Vorgang beendet ist. Bei einer Unterbrechung bleiben Wiederherstellungsprotokoll und Sicherungen erhalten.",
    "Checking package…": "Paket wird geprüft…",
    "Checking your installation…": "Installation wird geprüft…",
    "Working…": "Vorgang läuft…",
    "KKS is verifying the package, game files and restoration data. Keep Fallout 76 closed during changes.": "KKS prüft das Paket, die Spieldateien und die Wiederherstellungsdaten. Fallout 76 muss während der Änderungen geschlossen bleiben.",
    "Verifying the selected package…": "Ausgewähltes Paket wird geprüft…",
    "Checking saved installation and compatibility…": "Gespeicherte Installation und Kompatibilität werden geprüft…",
    "Installing the selected content package…": "Ausgewähltes Inhaltspaket wird installiert…",
    "Repairing installed content…": "Installierte Inhalte werden repariert…",
    "Restoring verified vanilla…": "Geprüfte Originaldateien werden wiederhergestellt…",
    "Recovering the interrupted operation…": "Unterbrochener Vorgang wird wiederhergestellt…",
    "Needs attention before continuing": "Vor dem Fortfahren prüfen",
    "Ready to install.": "Bereit zur Installation.",
    "Ready to update.": "Bereit zur Aktualisierung.",
    "KKS is installed.": "KKS ist installiert.",
    "KKS 1.0 installation found.": "KKS-1.0-Installation gefunden.",
    "KKS needs a repair.": "KKS muss repariert werden.",
    "Choose a content package.": "Wähle ein Inhaltspaket.",
    "Recover the interrupted change.": "Unterbrochene Änderung wiederherstellen.",
    "Verified.": "Geprüft.",
    "Verifying the supported game build…": "Unterstützte Spielversion wird geprüft…",
    "Previous file state restored. All backups are retained.": "Vorheriger Dateizustand wiederhergestellt. Alle Sicherungen bleiben erhalten.",
    "Saving and verifying restoration backups…": "Originalsicherungen werden erstellt und geprüft…",
    "Applying verified files…": "Geprüfte Dateien werden übernommen…",
    "Reopening and validating installed files…": "Installierte Dateien werden erneut geöffnet und geprüft…",
    "Close Fallout 76 before continuing": "Schließe Fallout 76, bevor du fortfährst.",
    "The game executable is in use. Close the game and pause game updates": "Die Spieldatei wird verwendet. Schließe Fallout 76 und pausiere Spielupdates.",
    "Another KKS operation is already running": "Ein anderer KKS-Vorgang läuft bereits.",
    "Choose the Fallout 76 folder containing Fallout76.exe and Data": "Wähle den Fallout-76-Ordner mit Fallout76.exe und Data.",
    "Restore vanilla before switching the KKS content language": "Stelle vor dem Wechsel der KKS-Inhaltssprache die Originaldateien wieder her.",
    "Restore vanilla before selecting a package that removes managed game targets": "Stelle zuerst die Originaldateien wieder her, bevor du zu diesem Paket wechselst.",
    "The selected package matches this game and is ready to install.": "Das ausgewählte Paket passt zu dieser Spielversion und kann installiert werden.",
    "This complete package can be installed directly; intermediate updates are not required.": "Dieses vollständige Paket kann direkt installiert werden. Zwischenupdates sind nicht erforderlich.",
    "Choose a complete KKS content ZIP to check compatibility and install.": "Wähle eine vollständige KKS-Inhalts-ZIP, um die Kompatibilität zu prüfen und zu installieren.",
    "An interrupted change needs recovery before another operation.": "Eine unterbrochene Änderung muss vor dem nächsten Vorgang wiederhergestellt werden.",
    "Recover the interrupted managed operation first.": "Stelle zuerst den unterbrochenen Installationsvorgang wieder her.",
    "An interrupted operation needs recovery before installation can continue.": "Ein unterbrochener Vorgang muss vor der weiteren Installation wiederhergestellt werden.",
    "Verified vanilla files restored. All restoration history is retained.": "Geprüfte Originaldateien wiederhergestellt. Der gesamte Wiederherstellungsverlauf bleibt erhalten.",
    "There is no pending recovery.": "Es steht keine Wiederherstellung aus.",
    "The managed file state was recovered. Run Check to see whether repair is still needed.": "Der verwaltete Dateizustand wurde wiederhergestellt. Klicke auf „Prüfen“, um einen möglichen Reparaturbedarf zu ermitteln.",
    "The completed installation was verified and its saved state recovered.": "Die abgeschlossene Installation wurde geprüft und ihr gespeicherter Zustand wiederhergestellt.",
    "The previous managed file state was recovered; retry the update when ready.": "Der vorherige verwaltete Dateizustand wurde wiederhergestellt. Du kannst die Aktualisierung erneut versuchen.",
    "Verified vanilla is the recovery checkpoint. Select the content package to install again.": "Die geprüften Originaldateien sind wiederhergestellt. Wähle das Inhaltspaket zur erneuten Installation.",
    "The interrupted managed operation was recovered.": "Der unterbrochene Installationsvorgang wurde wiederhergestellt.",
    "KKS 1.0 is installed. Select a content package to migrate, or restore vanilla without the old EXE.": "KKS 1.0 ist installiert. Wähle ein Inhaltspaket zur Aktualisierung oder stelle die Originaldateien wieder her. Die alte EXE ist dafür nicht nötig.",
    "This package is older than or conflicts with an installed release. Select a newer complete package": "Dieses Paket ist älter als eine bereits installierte Ausgabe oder steht mit ihr in Konflikt. Wähle ein neueres vollständiges Paket.",
    "This content package needs a newer KKS Installer": "Dieses Inhaltspaket benötigt einen neueren KKS Installer.",
    "Select a complete KKS content ZIP": "Wähle eine vollständige KKS-Inhalts-ZIP.",
    "This package is not signed by a trusted KKS publisher": "Dieses Paket ist nicht von einem vertrauenswürdigen KKS-Herausgeber signiert.",
    "The KKS package signature is invalid": "Die Signatur des KKS-Pakets ist ungültig.",
    "ZIP files do not match the signed asset profile": "Der ZIP-Inhalt stimmt nicht mit dem signierten Paketprofil überein.",
    "Content language must match the fixed Steam asset profile": "Die Inhaltssprache muss zum festgelegten Steam-Paketprofil passen.",
    "German packages require Installer 1.3.0 or newer": "Deutsche Pakete benötigen Installer 1.3.0 oder neuer.",
    "No managed KKS installation is available": "Es wurde keine verwaltete KKS-Installation gefunden.",
    "Supported vanilla files found.": "Unterstützte Originaldateien gefunden.",
    "KKS files are installed and verified.": "KKS-Dateien sind installiert und geprüft.",
    "KKS files need repair.": "KKS-Dateien müssen repariert werden.",
    "Vanilla files have been restored.": "Die Originaldateien wurden wiederhergestellt.",
    "Private beta: set Fallout 76 to German in Steam before installing Deutsch content.": "Private Beta: Stelle Fallout 76 in Steam auf Deutsch, bevor du deutsche Inhalte installierst.",
}

PREFIXES = {
    "Unsupported or changed game build: ": "Nicht unterstützte oder geänderte Spielversion: ",
    "A loose interface override conflicts with KKS: ": "Eine lose Interface-Datei steht mit KKS in Konflikt: ",
    "Building and validating ": "Erstellen und Prüfen: ",
    "A cached payload is missing or damaged. Select the same content ZIP again: ": "Eine zwischengespeicherte Datei fehlt oder ist beschädigt. Wähle dieselbe Inhalts-ZIP erneut: ",
    "Foreign or unsupported file: ": "Fremde oder nicht unterstützte Datei: ",
    "Not enough free space": "Nicht genügend freier Speicherplatz",
    "Operation stopped: ": "Vorgang gestoppt: ",
}


def translate(text, language):
    if language != "de":
        return text
    if text in DE:
        return DE[text]
    # Complete user-facing sentence fragments; paths and package names stay exact.
    for source, target in sorted(DE.items(), key=lambda p: len(p[0]), reverse=True):
        if len(source) > 18:
            text = text.replace(source, target)
    for source, target in PREFIXES.items():
        text = text.replace(source, target)
    text = re.sub(
        r" · signature and all (\d+) files verified",
        r" · Signatur und alle \1 Dateien geprüft",
        text,
    )
    text = re.sub(
        r"(\d+) of (\d+) content files differ\.",
        r"\1 von \2 Inhaltsdateien unterscheiden sich.",
        text,
    )
    text = re.sub(r"^Verified (KKS .*) content package\.$", r"Inhaltspaket \1 geprüft.", text)
    text = text.replace(" Selected: ", " Ausgewählt: ").replace(" Installed: ", " Installiert: ")
    text = text.replace(" installed and verified.", " installiert und geprüft.")
    return text


def preference_path():
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "KKS/installer-language.json"


def load_language():
    try:
        p = preference_path()
        if p.stat().st_size <= 1024:
            value = json.loads(p.read_text("utf8")).get("language")
            if value in ("en", "de"):
                return value
    except (OSError, ValueError, AttributeError):
        pass
    try:
        if os.name == "nt" and ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == 7:
            return "de"
    except (AttributeError, OSError):
        pass
    return "en"


def save_language(language):
    if language not in ("en", "de"):
        return False
    try:
        p = preference_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + "." + uuid.uuid4().hex + ".tmp")
        tmp.write_text(json.dumps({"language": language}) + "\n", "utf8")
        os.replace(tmp, p)
        return True
    except OSError:
        return False
