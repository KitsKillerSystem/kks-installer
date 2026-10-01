"""Native offline installer: select, check, update, repair and restore."""

from pathlib import Path
import queue, threading, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ._application import APP_VERSION
from .manager import Manager
from .platforms import discover
from .windows_drop import enable_file_drop

BG = "#111b18"
PANEL = "#1b2923"
PANEL2 = "#24362d"
INK = "#ecf1e9"
MUTED = "#acbdb0"
GREEN = "#b7f36c"
LINE = "#3c5143"
RED = "#ffb89a"


class App:
    def __init__(self, package=None, game=None):
        self.root = tk.Tk()
        self.root.title("KKS Installer · " + APP_VERSION)
        width = min(980, self.root.winfo_screenwidth() - 60)
        height = min(860, self.root.winfo_screenheight() - 80)
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(min(840, width), min(680, height))
        self.root.configure(bg=BG)
        self.root.option_add("*Font", ("Segoe UI", 10))
        self.busy = False
        self.events = queue.Queue()
        self.last_status = None
        self.selected = None
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "KKS.Horizontal.TProgressbar",
            troughcolor=PANEL,
            bordercolor=PANEL,
            background=GREEN,
            lightcolor=GREEN,
            darkcolor=GREEN,
        )
        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="both", expand=True, padx=24, pady=12)
        top = tk.Frame(outer, bg=BG)
        top.pack(fill="x")
        tk.Label(top, text="KKS", font=("Segoe UI", 26, "bold"), fg=GREEN, bg=BG).pack(side="left")
        tk.Label(
            top, text="KIT’S KILLER SYSTEM", font=("Segoe UI", 11, "bold"), fg=INK, bg=BG
        ).pack(side="left", padx=20)
        tk.Label(top, text="INSTALLER " + APP_VERSION, fg=MUTED, bg=BG).pack(side="right")
        tk.Label(
            outer,
            text="Choose a complete KKS content ZIP. You can jump straight to a newer compatible release.",
            fg=MUTED,
            bg=BG,
            anchor="w",
            wraplength=840,
            justify="left",
        ).pack(fill="x", pady=(8, 12))
        location = self.panel(outer)
        location.pack(fill="x")
        self.label(location, "FALLOUT 76 LOCATION").pack(fill="x", padx=16, pady=(12, 6))
        row = tk.Frame(location, bg=PANEL)
        row.pack(fill="x", padx=16, pady=(0, 13))
        self.path = tk.StringVar()
        self.entry = tk.Entry(
            row, textvariable=self.path, bg=PANEL2, fg=INK, insertbackground=INK, relief="flat"
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=9)
        self.browse = self.button(row, "Browse…", self.choose_game)
        self.browse.pack(side="left", padx=(10, 0))
        self.check = self.button(row, "Check", lambda: self.start("check"))
        self.check.pack(side="left", padx=(8, 0))
        package_panel = self.panel(outer)
        package_panel.pack(fill="x", pady=(12, 0))
        self.label(package_panel, "CONTENT PACKAGE").pack(fill="x", padx=16, pady=(12, 5))
        package_row = tk.Frame(package_panel, bg=PANEL)
        package_row.pack(fill="x", padx=16, pady=(0, 13))
        self.package_text = tk.StringVar(
            value="Drop a ZIP here or choose a package. Keep the ZIP unopened."
        )
        tk.Label(
            package_row,
            textvariable=self.package_text,
            fg=INK,
            bg=PANEL,
            anchor="w",
            justify="left",
            wraplength=590,
        ).pack(side="left", fill="x", expand=True)
        self.package_button = self.button(package_row, "Choose package…", self.choose_package)
        self.package_button.pack(side="right", padx=(10, 0))
        status = self.panel(outer)
        status.pack(fill="x", pady=12)
        self.status_title = tk.Label(
            status,
            text="Ready when you are.",
            font=("Segoe UI", 18, "bold"),
            fg=INK,
            bg=PANEL,
            anchor="w",
        )
        self.status_title.pack(fill="x", padx=16, pady=(14, 5))
        self.status_message = tk.Label(
            status,
            text="Choose your game folder and a content package to begin.",
            fg=MUTED,
            bg=PANEL,
            anchor="w",
            justify="left",
            wraplength=820,
        )
        self.status_message.pack(fill="x", padx=16, pady=(0, 14))
        self.progress = ttk.Progressbar(
            outer, style="KKS.Horizontal.TProgressbar", mode="indeterminate"
        )
        self.progress.pack(fill="x", pady=(0, 12))
        actions = tk.Frame(outer, bg=BG)
        actions.pack(fill="x")
        self.primary = self.button(actions, "Install content", self.primary_action, True)
        self.primary.pack(side="left")
        self.repair = self.button(actions, "Repair", lambda: self.start("repair"))
        self.repair.pack(side="left", padx=10)
        self.restore = self.button(actions, "Restore vanilla", lambda: self.start("restore"))
        self.restore.pack(side="left")
        for b in (self.primary, self.repair, self.restore):
            b.configure(state="disabled")
        self.label(outer, "ACTIVITY", BG).pack(fill="x", pady=(10, 6))
        self.log = tk.Text(
            outer,
            height=5,
            bg=PANEL,
            fg=MUTED,
            relief="flat",
            font=("Consolas", 10),
            wrap="word",
            padx=12,
            pady=10,
            state="disabled",
        )
        tk.Label(
            outer,
            text="Works offline · Backups remain in your game folder · No xTranslator required",
            fg=MUTED,
            bg=BG,
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(side="bottom", fill="x", pady=(10, 0))
        self.log.pack(fill="both", expand=True)
        self.path.trace_add("write", self.path_changed)
        candidates = discover() if not game else []
        if game or candidates:
            self.path.set(game or candidates[0])
        try:
            self.drop_binding = enable_file_drop(self.root, self.dropped)
        except OSError:
            self.drop_binding = None
            self.append("Use Choose package to select your content ZIP.")
        self.root.after(100, self.pump)
        if package:
            self.root.after(200, lambda: self.select_package(package))
        elif self.path.get():
            self.root.after(200, lambda: self.start("check"))

    def panel(self, parent):
        return tk.Frame(parent, bg=PANEL, highlightbackground=LINE, highlightthickness=1)

    def label(self, parent, text, bg=PANEL):
        return tk.Label(
            parent, text=text, font=("Segoe UI", 9, "bold"), fg=MUTED, bg=bg, anchor="w"
        )

    def button(self, parent, text, command, primary=False):
        return tk.Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI", 11, "bold" if primary else "normal"),
            bg=GREEN if primary else PANEL2,
            fg=BG if primary else INK,
            activebackground="#cafb90" if primary else LINE,
            activeforeground=BG if primary else INK,
            disabledforeground="#758677",
            relief="flat",
            borderwidth=0,
            padx=17,
            pady=10,
            cursor="hand2",
        )

    def append(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def path_changed(self, *args):
        if not self.busy:
            self.last_status = None
            self.selected = None
            self.package_text.set("Drop a ZIP here or choose a package. Keep the ZIP unopened.")
            for b in (self.primary, self.repair, self.restore):
                b.configure(state="disabled")

    def choose_game(self):
        path = filedialog.askdirectory(
            title="Choose the folder containing Fallout76.exe", initialdir=self.path.get() or None
        )
        if path:
            self.path.set(path)
            self.start("check")

    def choose_package(self):
        path = filedialog.askopenfilename(
            title="Choose a complete KKS content ZIP", filetypes=[("KKS content package", "*.zip")]
        )
        if path:
            self.select_package(path)

    def dropped(self, paths):
        if self.busy:
            self.append("Wait for the current operation, then drop the package again.")
            return
        if len(paths) != 1 or Path(paths[0]).suffix.lower() != ".zip":
            messagebox.showinfo("Choose one ZIP", "Drop one complete KKS content ZIP.")
            return
        self.select_package(paths[0])

    def select_package(self, path):
        if not self.path.get():
            game = filedialog.askdirectory(title="Choose the folder containing Fallout76.exe")
            if not game:
                return
            self.path.set(game)
        self.start("select", path)

    def primary_action(self):
        self.start("recover" if self.last_status == "recovery_required" else "install")

    def close(self):
        if self.busy:
            messagebox.showinfo(
                "KKS is working",
                "Wait for the operation to finish. If it is interrupted, KKS keeps the recovery journal and backups.",
            )
        else:
            self.root.destroy()

    def start(self, action, zip_path=None):
        if self.busy:
            return
        game = self.path.get().strip()
        if not game:
            self.choose_game()
            return
        self.busy = True
        self.last_status = None
        for w in (
            self.entry,
            self.browse,
            self.check,
            self.package_button,
            self.primary,
            self.repair,
            self.restore,
        ):
            w.configure(state="disabled")
        self.progress.start(12)
        self.status_title.configure(
            text=(
                "Checking package…"
                if action == "select"
                else "Checking your installation…" if action == "check" else "Working…"
            ),
            fg=INK,
        )
        self.status_message.configure(
            text="KKS is verifying the package, game files and restoration data. Keep Fallout 76 closed during changes."
        )
        selected = self.selected
        self.append(
            {
                "select": "Verifying the selected package…",
                "check": "Checking saved installation and compatibility…",
                "install": "Installing the selected content package…",
                "repair": "Repairing installed content…",
                "restore": "Restoring verified vanilla…",
                "recover": "Recovering the interrupted operation…",
            }[action]
        )

        def work():
            try:
                manager = Manager(game, lambda text: self.events.put(("log", text)))
                release = (
                    manager.package(selected)
                    if selected and action not in ("select", "restore", "recover", "repair")
                    else None
                )
                if action == "select":
                    release = manager.select(zip_path)
                    self.events.put(("selected", (release.manifest_digest, release.name)))
                    result = manager.inspect(release)
                elif action == "check":
                    result = manager.inspect(release)
                else:
                    result = (
                        manager.recover() if action == "recover" else manager.run(action, release)
                    )
                    self.events.put(("log", result.get("message", result["status"])))
                    result = manager.inspect()
                self.events.put(("success", result))
            except Exception as e:
                self.events.put(("error", str(e)))

        threading.Thread(target=work, daemon=False).start()

    def pump(self):
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == "log":
                    self.append(data)
                    continue
                if kind == "selected":
                    self.selected, name = data
                    self.package_text.set(name + " · signature and all five files verified")
                    continue
                self.busy = False
                self.progress.stop()
                self.progress.configure(value=0)
                for w in (self.entry, self.browse, self.check, self.package_button):
                    w.configure(state="normal")
                if kind == "error":
                    self.status_title.configure(text="Needs attention before continuing", fg=RED)
                    self.status_message.configure(text=data[:600])
                    self.append(data)
                else:
                    status = data["status"]
                    self.last_status = status
                    titles = {
                        "ready": "Ready to install.",
                        "update_available": "Ready to update.",
                        "installed": "KKS is installed.",
                        "legacy_installed": "KKS 1.0 installation found.",
                        "repairable": "KKS needs a repair.",
                        "package_required": "Choose a content package.",
                        "recovery_required": "Recover the interrupted change.",
                    }
                    self.status_title.configure(text=titles.get(status, status), fg=GREEN)
                    message = data.get("message", "Verified.")
                    if data.get("selected_content"):
                        message += " Selected: " + data["selected_content"] + "."
                    if data.get("installed_content"):
                        message += " Installed: " + data["installed_content"] + "."
                    if "changed_payload_files" in data:
                        message += f' {data["changed_payload_files"]} of 5 content files differ.'
                    self.status_message.configure(text=message)
                    self.append(message)
                    self.primary.configure(
                        text=(
                            "Recover previous state"
                            if status == "recovery_required"
                            else (
                                "Install update"
                                if status == "update_available"
                                else "Install content"
                            )
                        ),
                        state=(
                            "normal"
                            if status in ("ready", "update_available", "recovery_required")
                            else "disabled"
                        ),
                    )
                    self.repair.configure(
                        state="normal" if data.get("repair_available") else "disabled"
                    )
                    self.restore.configure(
                        state="normal" if data.get("restore_available") else "disabled"
                    )
        except queue.Empty:
            pass
        self.root.after(100, self.pump)

    def run(self):
        self.root.mainloop()


def launch(package=None, game=None):
    App(package, game).run()
