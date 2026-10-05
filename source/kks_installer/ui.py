"""Native offline installer: select, check, update, repair and restore."""

from pathlib import Path
import queue, threading, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ._application import APP_VERSION, BUILD_LABEL
from .i18n import translate, load_language, save_language, LANGUAGE_NAMES, CONTENT_HINTS
from .manager import Manager
from .platforms import discover
from .windows_drop import enable_file_drop

BG = "#e8e2d4"
PANEL = "#f5f0e5"
PANEL2 = "#d9d2c2"
INK = "#252d2b"
MUTED = "#59625c"
GREEN = "#536b3e"
LINE = "#afa997"
RED = "#a4402c"
ACCENT = "#ce653c"
DARK = "#27312e"


class App:
    def __init__(self, package=None, game=None, language=None):
        self.language = language or load_language()
        self.log_lines = []
        self.status_title_key = "Ready when you are."
        self.primary_key = "Install content"
        self.root = tk.Tk()
        self.root.title("KKS Installer · " + APP_VERSION + " · " + BUILD_LABEL)
        width = min(1080, self.root.winfo_screenwidth() - 60)
        height = min(790, self.root.winfo_screenheight() - 80)
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(min(900, width), min(700, height))
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
            troughcolor=PANEL2,
            bordercolor=PANEL2,
            background=GREEN,
            lightcolor=GREEN,
            darkcolor=GREEN,
            thickness=5,
        )

        # A compact field-manual layout: a fixed identity spine and one clear
        # working surface. Native controls retain keyboard focus and resizing.
        spine = tk.Frame(self.root, bg=DARK, width=170)
        spine.pack(side="left", fill="y")
        spine.pack_propagate(False)
        tk.Frame(spine, bg=ACCENT, height=9).pack(fill="x")
        tk.Label(
            spine,
            text="KKS",
            font=("Bahnschrift", 48, "bold"),
            fg=BG,
            bg=DARK,
            anchor="w",
        ).pack(fill="x", padx=18, pady=(22, 0))
        tk.Label(
            spine,
            text="KIT’S\nKILLER\nSYSTEM",
            font=("Bahnschrift", 15),
            fg=BG,
            bg=DARK,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=22)
        tk.Frame(spine, bg="#65716a", height=1).pack(fill="x", padx=22, pady=23)
        tk.Label(
            spine,
            text="CONTENT\nINSTALLER",
            font=("Consolas", 10),
            fg="#b4bfb5",
            bg=DARK,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=22)
        tk.Label(
            spine,
            text="v" + APP_VERSION,
            font=("Consolas", 10),
            fg="#b4bfb5",
            bg=DARK,
            anchor="w",
        ).pack(fill="x", padx=22, pady=(6, 0))
        tk.Label(
            spine,
            text="FALLOUT 76\nSTEAM / EN + DE",
            font=("Consolas", 9),
            fg="#b4bfb5",
            bg=DARK,
            justify="left",
            anchor="w",
        ).pack(side="bottom", fill="x", padx=22, pady=24)
        tk.Label(
            spine,
            text="Language / Sprache",
            fg=BG,
            bg=DARK,
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill="x", padx=18, pady=(20, 5))
        self.language_value = tk.StringVar(value=LANGUAGE_NAMES[self.language])
        self.language_box = ttk.Combobox(
            spine,
            textvariable=self.language_value,
            values=tuple(LANGUAGE_NAMES.values()),
            state="readonly",
            width=13,
        )
        self.language_box.pack(fill="x", padx=18)
        self.language_box.bind("<<ComboboxSelected>>", self.change_language)

        outer = tk.Frame(self.root, bg=BG)
        outer.pack(side="left", fill="both", expand=True, padx=28, pady=12)
        tk.Label(
            outer,
            text="A BETTER-ORDERED WASTELAND.",
            font=("Consolas", 10, "bold"),
            fg=RED,
            bg=BG,
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            outer,
            text="Make yourself at home.",
            font=("Bahnschrift", 25),
            fg=INK,
            bg=BG,
            anchor="w",
        ).pack(fill="x", pady=(3, 5))
        tk.Label(
            outer,
            text="Choose your game folder and a complete KKS content ZIP.",
            fg=MUTED,
            bg=BG,
            anchor="w",
        ).pack(fill="x")
        tk.Frame(outer, bg=INK, height=2).pack(fill="x", pady=(12, 10))

        self.label(outer, "01  /  GAME DIRECTORY", BG).pack(fill="x", pady=(0, 7))
        row = tk.Frame(outer, bg=BG)
        row.pack(fill="x")
        self.path = tk.StringVar()
        self.entry = tk.Entry(
            row,
            textvariable=self.path,
            bg=PANEL,
            fg=INK,
            insertbackground=INK,
            relief="flat",
            highlightthickness=1,
            highlightbackground=LINE,
            highlightcolor=GREEN,
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=7)
        self.browse = self.button(row, "Browse…", self.choose_game)
        self.browse.pack(side="left", padx=(8, 0))
        self.check = self.button(row, "Check", lambda: self.start("check"))
        self.check.pack(side="left", padx=(6, 0))

        self.label(outer, "02  /  CONTENT PACKAGE", BG).pack(fill="x", pady=(12, 7))
        package_row = tk.Frame(outer, bg=PANEL, highlightbackground=LINE, highlightthickness=1)
        package_row.pack(fill="x")
        self.package_text = tk.StringVar(
            value="Drop one content ZIP onto this window, or choose it below."
        )
        self.package_key = self.package_text.get()
        self.package_label = tk.Label(
            package_row,
            textvariable=self.package_text,
            fg=INK,
            bg=PANEL,
            anchor="w",
            justify="left",
            wraplength=480,
        )
        self.package_label.pack(fill="x", padx=13, pady=(8, 5))
        self.package_button = self.button(package_row, "Choose package…", self.choose_package)
        self.package_button.pack(anchor="w", padx=12, pady=(0, 8))
        self.label(outer, "03  /  INSTALLATION STATUS", BG).pack(fill="x", pady=(12, 7))
        status = tk.Frame(outer, bg=PANEL)
        status.pack(fill="x")
        self.status_title = tk.Label(
            status,
            text="Ready when you are.",
            font=("Bahnschrift", 19),
            fg=INK,
            bg=PANEL,
            anchor="w",
        )
        self.status_title.pack(fill="x", padx=13, pady=(8, 5))
        message_row = tk.Frame(status, bg=PANEL)
        message_row.pack(fill="x", padx=13, pady=(0, 8))
        self.status_message = tk.Text(
            message_row,
            height=3,
            width=1,
            wrap="word",
            fg=MUTED,
            bg=PANEL,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            font=("Segoe UI", 10),
            state="disabled",
        )
        message_scroll = ttk.Scrollbar(message_row, command=self.status_message.yview)
        self.status_message.configure(yscrollcommand=message_scroll.set)
        message_scroll.pack(side="right", fill="y")
        self.status_message.pack(side="left", fill="x", expand=True)
        self.status_text("Select a package to check compatibility.")
        self.progress = ttk.Progressbar(
            outer, style="KKS.Horizontal.TProgressbar", mode="indeterminate"
        )
        self.progress.pack(fill="x", pady=(0, 10))
        actions = tk.Frame(outer, bg=BG)
        actions.pack(fill="x")
        self.primary = self.button(actions, "Install content", self.primary_action, True)
        self.primary.pack(side="left")
        self.repair = self.button(actions, "Repair", lambda: self.start("repair"))
        self.repair.pack(side="left", padx=8)
        self.restore = self.button(actions, "Restore vanilla", lambda: self.start("restore"))
        self.restore.pack(side="left")
        for button in (self.primary, self.repair, self.restore):
            button.configure(state="disabled")
        self.label(outer, "ACTIVITY", BG).pack(fill="x", pady=(10, 6))
        self.log = tk.Text(
            outer,
            height=4,
            bg=PANEL,
            fg=MUTED,
            relief="flat",
            font=("Consolas", 9),
            wrap="word",
            padx=11,
            pady=8,
            state="disabled",
        )
        tk.Label(
            outer,
            text="Offline by design.  Your vanilla backups stay with your game.",
            fg=MUTED,
            bg=BG,
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(side="bottom", fill="x", pady=(8, 0))
        self.log.pack(fill="both", expand=True)
        self.static_text = []

        def remember(widget):
            if widget not in (self.status_title, self.primary, self.package_label):
                if "text" in widget.keys() and not widget.cget("textvariable"):
                    text = widget.cget("text")
                    if text:
                        self.static_text.append((widget, text))
            for child in widget.winfo_children():
                remember(child)

        remember(self.root)
        self.render_language()

        def resize_labels(event):
            self.package_label.configure(wraplength=max(360, event.width - 30))

        outer.bind("<Configure>", resize_labels)
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

    def t(self, text):
        return translate(text, self.language)

    def change_language(self, event=None):
        if self.busy:
            return
        self.language = next(
            code for code, name in LANGUAGE_NAMES.items() if name == self.language_value.get()
        )
        save_language(self.language)
        self.render_language()

    def render_language(self):
        for widget, text in self.static_text:
            widget.configure(text=self.t(text))
        self.status_title.configure(text=self.t(self.status_title_key))
        self.primary.configure(text=self.t(self.primary_key))
        self.package_text.set(self.t(self.package_key))
        self.status_text(self.status_text_key)
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.insert(
            "end",
            "\n".join(self.t(x) for x in self.log_lines) + ("\n" if self.log_lines else ""),
        )
        self.log.configure(state="disabled")

    def set_title(self, text, color=INK):
        self.status_title_key = text
        self.status_title.configure(text=self.t(text), fg=color)

    def set_package(self, text):
        self.package_key = text
        self.package_text.set(self.t(text))

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
            fg="#ffffff" if primary else INK,
            activebackground="#415631" if primary else "#c6beab",
            activeforeground="#ffffff" if primary else INK,
            disabledforeground="#8b9282",
            relief="flat",
            borderwidth=0,
            padx=17,
            pady=8,
            cursor="hand2",
        )

    def status_text(self, text):
        self.status_text_key = text
        self.status_message.configure(state="normal")
        self.status_message.delete("1.0", "end")
        self.status_message.insert("1.0", self.t(text))
        self.status_message.configure(state="disabled")
        self.status_message.yview_moveto(0)

    def append(self, text):
        self.log_lines.append(text)
        self.log.configure(state="normal")
        self.log.insert("end", self.t(text) + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def path_changed(self, *args):
        if not self.busy:
            self.last_status = None
            self.selected = None
            self.set_package("Drop a ZIP here or choose a package. Keep the ZIP unopened.")
            for b in (self.primary, self.repair, self.restore):
                b.configure(state="disabled")

    def choose_game(self):
        path = filedialog.askdirectory(
            title=self.t("Choose the folder containing Fallout76.exe"),
            initialdir=self.path.get() or None,
        )
        if path:
            self.path.set(path)
            self.start("check")

    def choose_package(self):
        path = filedialog.askopenfilename(
            title=self.t("Choose a complete KKS content ZIP"),
            filetypes=[(self.t("KKS content package"), "*.zip")],
        )
        if path:
            self.select_package(path)

    def dropped(self, paths):
        if self.busy:
            self.append("Wait for the current operation, then drop the package again.")
            return
        if len(paths) != 1 or Path(paths[0]).suffix.lower() != ".zip":
            messagebox.showinfo(
                self.t("Choose one ZIP"), self.t("Drop one complete KKS content ZIP.")
            )
            return
        self.select_package(paths[0])

    def select_package(self, path):
        if not self.path.get():
            game = filedialog.askdirectory(
                title=self.t("Choose the folder containing Fallout76.exe")
            )
            if not game:
                return
            self.path.set(game)
        self.start("select", path)

    def primary_action(self):
        self.start("recover" if self.last_status == "recovery_required" else "install")

    def close(self):
        if self.busy:
            messagebox.showinfo(
                self.t("KKS is working"),
                self.t(
                    "Wait for the operation to finish. If it is interrupted, KKS keeps the recovery journal and backups."
                ),
            )
        else:
            if self.drop_binding is not None:
                self.drop_binding.close()
            for timer in self.root.tk.call("after", "info"):
                self.root.after_cancel(timer)
            self.root.destroy()

    def start(self, action, zip_path=None):
        if self.busy:
            return
        game = self.path.get().strip()
        if not game:
            self.choose_game()
            return
        self.busy = True
        self.language_box.configure(state="disabled")
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
        self.set_title(
            (
                "Checking package…"
                if action == "select"
                else "Checking your installation…" if action == "check" else "Working…"
            ),
        )
        self.status_text(
            "KKS is verifying the package, game files and restoration data. Keep Fallout 76 closed during changes."
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
                    if release.manifest["game"]["language"] != "en":
                        self.events.put(
                            (
                                "log",
                                CONTENT_HINTS[release.manifest["game"]["language"]],
                            )
                        )
                    self.events.put(
                        (
                            "selected",
                            (
                                release.manifest_digest,
                                release.name,
                                len(release.files),
                                release.manifest["game"]["language"],
                            ),
                        )
                    )
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
                    self.selected, name, file_count, language = data
                    self.set_package(
                        name
                        + f" · signature and all {file_count} files verified"
                        + "\n"
                        + (CONTENT_HINTS[language])
                    )
                    continue
                self.busy = False
                self.language_box.configure(state="readonly")
                self.progress.stop()
                self.progress.configure(value=0)
                for w in (self.entry, self.browse, self.check, self.package_button):
                    w.configure(state="normal")
                if kind == "error":
                    self.set_title("Needs attention before continuing", RED)
                    self.status_text(data)
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
                    self.set_title(titles.get(status, status), GREEN)
                    message = data.get("message", "Verified.")
                    if data.get("selected_content"):
                        message += " Selected: " + data["selected_content"] + "."
                    if data.get("installed_content"):
                        message += " Installed: " + data["installed_content"] + "."
                    if "changed_payload_files" in data:
                        message += f' {data["changed_payload_files"]} of {data["payload_file_count"]} content files differ.'
                    self.status_text(message)
                    self.append(message)
                    self.primary_key = (
                        "Recover previous state"
                        if status == "recovery_required"
                        else (
                            "Install update" if status == "update_available" else "Install content"
                        )
                    )
                    self.primary.configure(
                        text=self.t(self.primary_key),
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
