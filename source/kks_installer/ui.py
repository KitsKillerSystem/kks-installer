"""Native offline installer: select, check, update, repair and restore."""

from pathlib import Path
from typing import NamedTuple
import queue, threading, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ._application import APP_VERSION
from .i18n import translate, load_language, save_language, LANGUAGE_NAMES, CONTENT_HINTS
from .manager import Manager
from .platforms import discover
from .windows_drop import enable_file_drop
from .equipment import FULL, LABELS
from .perks import ON, LABELS as PERK_LABELS
from .string_modes import FOOD_DEFAULT, JUNK_DEFAULT, FOOD_LABELS, JUNK_LABELS

BG = "#eee3ca"
PANEL = "#f7efdf"
PANEL2 = "#d9cbb0"
INK = "#242820"
MUTED = "#605a49"
GREEN = "#49613d"
LINE = "#a99a7c"
RED = "#9c3b21"
ACCENT = "#b65325"
DARK = "#23271f"



class _Poster:
    """One approved image, tiled only through its quiet paper/upper-spine bands."""
    def __init__(self, root):
        self.root, self.canvases, self.labels = root, [], []
        original = tk.PhotoImage(file=str(Path(__file__).resolve().parent / "assets" / "halloween-plate.png"))
        # Separate calls preserve detail; a combined Tk copy would subsample first.
        self.base = original.zoom(2, 2).subsample(3, 3)
        self.image = self.base
        self.size = None
        self.repaint_pending = None
        root.bind("<Configure>", self.resize, add="+")

    def canvas(self, parent):
        canvas = tk.Canvas(parent, width=1, height=1, highlightthickness=0,
                           borderwidth=0, takefocus=False)
        self.attach(canvas)
        return canvas

    def attach(self, canvas):
        item = canvas.create_image(0, 0, image=self.image, anchor="nw")
        self.canvases.append((canvas, item))
        canvas.bind("<Configure>", lambda event: self.request_refresh(), add="+")

    def request_refresh(self):
        if self.repaint_pending is None:
            self.repaint_pending = self.root.after_idle(self.refresh)

    def refresh(self):
        self.repaint_pending = None
        for canvas, item in self.canvases:
            self.position(canvas, item)

    def position(self, canvas, item):
        x = canvas.winfo_rootx() - self.root.winfo_rootx()
        y = canvas.winfo_rooty() - self.root.winfo_rooty()
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if x < 0 or y < 0 or x >= self.image.width() or y >= self.image.height():
            return
        # Give each native surface a bounded image rather than an oversized
        # negative-coordinate image, so Windows repaint clipping stays local.
        crop = tk.PhotoImage(width=width, height=height)
        crop.tk.call(crop, "copy", self.image, "-from", x, y,
                     min(x + width, self.image.width()), min(y + height, self.image.height()))
        canvas.poster_image = crop
        canvas.coords(item, 0, 0)
        canvas.itemconfigure(item, image=crop)

    def resize(self, event):
        if event.widget is not self.root or event.width < 400 or event.height < 660:
            return
        size = (event.width, event.height)
        if size == self.size:
            return
        width, height = size
        result = tk.PhotoImage(width=width, height=height)
        sw, sh = self.base.width(), self.base.height()
        # Preserve the whole left illustration, outer frame and corner leaves.
        # Only quiet center paper and upper charcoal texture are tiled/cropped.
        for sx, ex, dx, tx in ((0, 206, 0, 206), (206, sw-170, 206, width-170),
                              (sw-170, sw, width-170, width)):
            for sy, ey, dy, ty in ((0, 180, 0, 180), (180, sh-480, 180, height-480),
                                  (sh-480, sh, height-480, height)):
                for x in range(dx, tx, ex-sx):
                    for y in range(dy, ty, ey-sy):
                        result.tk.call(result, "copy", self.base, "-from", sx, sy,
                                       sx+min(ex-sx, tx-x), sy+min(ey-sy, ty-y), "-to", x, y)
        self.image, self.size = result, size
        self.request_refresh()


class _PosterLabel(tk.Canvas):
    """Static translated text over the shared poster; never an action control."""
    def __init__(self, poster, parent, text, font=("Segoe UI", 9, "bold"), fg=MUTED):
        super().__init__(parent, width=1, height=1, highlightthickness=0,
                         borderwidth=0, takefocus=False)
        self.text_key = text
        poster.attach(self)
        self.text_item = self.create_text(1, 1, text=text, font=font, fill=fg, anchor="nw")
        poster.labels.append(self)
        self.configure(text=text)

    def configure(self, cnf=None, **kwargs):
        if not hasattr(self, "text_item"):
            return super().configure(cnf, **kwargs)
        text_options = {}
        for name, target in (("text", "text"), ("font", "font"), ("fg", "fill"),
                             ("wraplength", "width"), ("justify", "justify")):
            if name in kwargs:
                text_options[target] = kwargs.pop(name)
        if text_options:
            self.itemconfigure(self.text_item, **text_options)
            box = self.bbox(self.text_item)
            kwargs["height"] = box[3] - box[1] + 2
            kwargs["width"] = box[2] - box[0] + 2
        return super().configure(cnf, **kwargs)


class Configuration(NamedTuple):
    naming: str
    perks: str
    food: str
    junk: str


class App:
    def __init__(self, package=None, game=None, language=None, naming=FULL, perks=ON,
                 food=FOOD_DEFAULT, junk=JUNK_DEFAULT):
        self.language = language or load_language()
        self.log_lines = []
        self.status_title_key = "Ready when you are."
        self.primary_key = "Install content"
        self.root = tk.Tk()
        self.root.title("KKS Installer · " + APP_VERSION)
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
        self.naming_available = False
        self.initial_naming = naming
        self.perks_available = False
        self.initial_perks = perks
        self.string_modes_available = False
        self.initial_food, self.initial_junk = food, junk
        self.installed_verified_configuration = None
        self.installed_manifest = None
        self.pending_selected_configuration = Configuration(naming, perks, food, junk)
        self.configuration_apply_available = False
        self.active_action = None
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "TCombobox", fieldbackground=PANEL, background=PANEL2,
            foreground=INK, arrowcolor=INK, bordercolor=LINE,
            lightcolor=LINE, darkcolor=LINE, selectbackground=PANEL2,
            selectforeground=INK,
        )
        style.map(
            "TCombobox", fieldbackground=[("readonly", PANEL), ("disabled", PANEL2)],
            foreground=[("disabled", MUTED)], arrowcolor=[("disabled", MUTED)],
        )
        style.configure(
            "KKS.Horizontal.TProgressbar",
            troughcolor=PANEL2,
            bordercolor=PANEL2,
            background=GREEN,
            lightcolor=GREEN,
            darkcolor=GREEN,
            thickness=5,
        )


        # The approved poster is presentation only. Native controls and actions
        # remain real widgets over the same in-memory background.
        self.poster = _Poster(self.root)
        background = tk.Canvas(self.root, highlightthickness=0, borderwidth=0, takefocus=False)
        background.place(x=0, y=0, relwidth=1, relheight=1)
        self.poster.attach(background)
        spine = tk.Canvas(self.root, width=190, highlightthickness=0, borderwidth=0, takefocus=False)
        spine.pack(side="left", fill="y")
        spine.pack_propagate(False)
        self.poster.attach(spine)
        self.seasonal_canvas = spine
        self.canvas_text = []

        def spine_text(y, text, font, color=BG):
            shadow = spine.create_text(26, y + 1, text=text, font=font, fill=DARK,
                                       anchor="nw", justify="left")
            item = spine.create_text(25, y, text=text, font=font, fill=color,
                                     anchor="nw", justify="left")
            self.canvas_text.append((spine, shadow, text))
            self.canvas_text.append((spine, item, text))
            return shadow, item

        spine_text(30, "KKS", ("Bahnschrift", 48, "bold"))
        spine_text(114, "KIT’S\nKILLER\nSYSTEM", ("Bahnschrift", 15))
        spine.create_line(25, 209, 164, 209, fill=ACCENT)
        spine_text(232, "CONTENT\nINSTALLER", ("Consolas", 10), PANEL2)
        spine_text(275, "v" + APP_VERSION, ("Consolas", 10), PANEL2)
        spine_text(313, "Language", ("Segoe UI", 9))
        footer = spine_text(640, "FALLOUT 76\nSTEAM\n13 CONTENT LANGUAGES",
                            ("Consolas", 9), PANEL2)
        def place_footer(event):
            spine.coords(footer[0], 26, event.height - 67)
            spine.coords(footer[1], 25, event.height - 68)
        spine.bind("<Configure>", place_footer, add="+")
        self.language_value = tk.StringVar(value=LANGUAGE_NAMES[self.language])
        self.language_box = ttk.Combobox(
            spine, textvariable=self.language_value, values=tuple(LANGUAGE_NAMES.values()),
            state="readonly", width=13,
        )
        self.language_box.place(x=23, y=335, width=144)
        self.language_box.bind("<<ComboboxSelected>>", self.change_language)

        outer = self.poster.canvas(self.root)
        outer.pack(side="left", fill="both", expand=True, padx=(23, 26), pady=(16, 24))
        _PosterLabel(self.poster, outer, "A BETTER-ORDERED WASTELAND.",
                     font=("Consolas", 10, "bold"), fg=RED).pack(fill="x")
        _PosterLabel(self.poster, outer, "Make yourself at home.",
                     font=("Bahnschrift", 16), fg=INK).pack(fill="x", pady=(0, 1))
        _PosterLabel(self.poster, outer, "Choose your game folder and a complete KKS content ZIP.",
                     font=("Segoe UI", 10), fg=MUTED).pack(fill="x")
        tk.Frame(outer, bg=INK, height=2).pack(fill="x", pady=(8, 6))

        self.label(outer, "01  /  GAME DIRECTORY", BG).pack(fill="x", pady=(0, 3))
        row = self.poster.canvas(outer)
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

        self.label(outer, "02  /  CONTENT PACKAGE", BG).pack(fill="x", pady=(8, 3))
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
        package_actions = tk.Frame(package_row, bg=PANEL)
        package_actions.pack(fill="x", padx=12, pady=(0, 4))
        self.package_button = self.button(package_actions, "Choose package…", self.choose_package)
        self.package_button.pack(side="left")
        self.naming_value = tk.StringVar(value=LABELS[FULL])
        self.naming_box = ttk.Combobox(package_actions, textvariable=self.naming_value,
                                       values=tuple(LABELS.values()), state="disabled", width=45)
        self.naming_box.pack(side="left", fill="x", expand=True, padx=(12, 0))
        self.naming_box.bind("<<ComboboxSelected>>", self.configuration_changed)
        perk_actions = tk.Frame(package_row, bg=PANEL)
        perk_actions.pack(fill="x", padx=12, pady=(0, 4))
        self.perks_value = tk.StringVar(value=PERK_LABELS[ON])
        self.perks_box = ttk.Combobox(perk_actions, textvariable=self.perks_value,
                                      values=tuple(PERK_LABELS.values()), state="disabled")
        self.perks_box.pack(fill="x")
        self.perks_box.bind("<<ComboboxSelected>>", self.configuration_changed)
        mode_actions = tk.Frame(package_row, bg=PANEL)
        mode_actions.pack(fill="x", padx=12, pady=(0, 4))
        self.label(mode_actions, "Food:").pack(side="left", padx=(0, 5))
        self.food_value = tk.StringVar(value=FOOD_LABELS[FOOD_DEFAULT])
        self.food_box = ttk.Combobox(mode_actions, textvariable=self.food_value,
                                    values=tuple(FOOD_LABELS.values()), state="disabled", width=13)
        self.food_box.pack(side="left", fill="x", expand=True)
        self.label(mode_actions, "Junk Components:").pack(side="left", padx=(12, 5))
        self.junk_value = tk.StringVar(value=JUNK_LABELS[JUNK_DEFAULT])
        self.junk_box = ttk.Combobox(mode_actions, textvariable=self.junk_value,
                                    values=tuple(JUNK_LABELS.values()), state="disabled", width=30)
        self.junk_box.pack(side="left", fill="x", expand=True)
        for box in (self.food_box, self.junk_box):
            box.bind("<<ComboboxSelected>>", self.configuration_changed)
        self.label(outer, "03  /  INSTALLATION STATUS", BG).pack(fill="x", pady=(5, 3))
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
            height=2,
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
        self.progress.pack(fill="x", pady=(0, 6))
        actions = self.poster.canvas(outer)
        actions.pack(fill="x")
        self.primary = self.button(actions, "Install content", self.primary_action, True)
        self.primary.pack(side="left")
        self.repair = self.button(actions, "Repair", lambda: self.start("repair"))
        self.repair.pack(side="left", padx=8)
        self.restore = self.button(actions, "Restore Baseline", lambda: self.start("restore"))
        self.restore.pack(side="left")
        launch_row = self.poster.canvas(outer)
        launch_row.pack(fill="x", pady=(6, 0))
        self.play = self.button(launch_row, "Play Fallout 76", lambda: self.start("play"))
        self.play.pack(side="right")
        self.apply = self.button(launch_row, "Apply Changes", lambda: self.start("apply"))
        self.apply.pack(side="right", padx=(0, 8))
        for button in (self.primary, self.repair, self.restore, self.play, self.apply):
            button.configure(state="disabled")
        baseline_help = self.label(launch_row, "Returns KKS-managed files to the state they were in before KKS was installed.", BG)
        baseline_help.configure(wraplength=420, font=("Segoe UI", 9), justify="left")
        baseline_help.pack(side="left", fill="x", expand=True)
        launch_row.bind(
            "<Configure>",
            lambda event: baseline_help.configure(
                wraplength=max(100, event.width - self.play.winfo_reqwidth()
                               - self.apply.winfo_reqwidth() - 12)
            ),
        )
        self.label(outer, "ACTIVITY", BG).pack(fill="x", pady=(3, 3))
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
        _PosterLabel(
            self.poster, outer, "Your installation baseline and backups stay with your game.",
            fg=MUTED, font=("Segoe UI", 9),
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
        for box, labels in ((self.naming_box, LABELS), (self.perks_box, PERK_LABELS),
                            (self.food_box, FOOD_LABELS), (self.junk_box, JUNK_LABELS)):
            selected = box.current()
            box.configure(values=tuple(self.t(label) for label in labels.values()))
            box.current(max(0, selected))
        for widget, text in self.static_text:
            widget.configure(text=self.t(text))
        for canvas, item, text in self.canvas_text:
            canvas.itemconfigure(item, text=self.t(text))
        for label in self.poster.labels:
            label.configure(text=self.t(label.text_key))
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
        if bg == BG:
            return _PosterLabel(self.poster, parent, text)
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
            activebackground="#344e2f" if primary else "#cabea3",
            activeforeground="#ffffff" if primary else INK,
            disabledforeground="#767b69",
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

    def read_configuration(self):
        return Configuration(*(
            next(key for key, label in labels.items() if self.t(label) == value.get())
            for value, labels in (
                (self.naming_value, LABELS), (self.perks_value, PERK_LABELS),
                (self.food_value, FOOD_LABELS), (self.junk_value, JUNK_LABELS),
            )
        ))

    def set_pending_configuration(self, configuration):
        self.pending_selected_configuration = configuration
        for value, labels, choice in zip(
            (self.naming_value, self.perks_value, self.food_value, self.junk_value),
            (LABELS, PERK_LABELS, FOOD_LABELS, JUNK_LABELS), configuration,
        ):
            value.set(self.t(labels[choice]))

    def can_apply(self):
        return (
            not self.busy and self.last_status == "installed"
            and self.configuration_apply_available
            and self.installed_verified_configuration is not None
            and self.selected == self.installed_manifest
            and self.pending_selected_configuration != self.installed_verified_configuration
        )

    def configuration_changed(self, event=None):
        """An in-memory edit only: no worker, package, verification or disk access."""
        if not self.busy:
            self.pending_selected_configuration = self.read_configuration()
            self.apply.configure(state="normal" if self.can_apply() else "disabled")

    def inspected_configuration(self, data, completed_action=None):
        """Only backend inspection may establish installed truth; never use a draft."""
        previous = self.installed_verified_configuration
        was_clean = previous is None or self.pending_selected_configuration == previous
        self.configuration_apply_available = False
        if data.get("installed_verified"):
            installed = Configuration(*(data["installed_" + field]
                                        for field in Configuration._fields))
            self.installed_verified_configuration = installed
            self.installed_manifest = data["installed_manifest"]
            if self.selected is None:
                self.selected = self.installed_manifest
                self.set_package(data["installed_content"])
            if self.selected == self.installed_manifest:
                self.naming_available = data["installed_equipment_naming_available"]
                self.perks_available = data["installed_perk_cards_available"]
                self.string_modes_available = data["installed_string_modes_available"]
                self.configuration_apply_available = data.get("repair_available", False)
                if was_clean or completed_action in ("select", "install", "apply", "recover"):
                    self.set_pending_configuration(installed)
        elif data["status"] in ("package_required", "ready") and not data.get("installed_content"):
            self.installed_verified_configuration = None
            self.installed_manifest = None

    def path_changed(self, *args):
        if not self.busy:
            self.last_status = None
            self.selected = None
            self.installed_verified_configuration = None
            self.installed_manifest = None
            self.configuration_apply_available = False
            self.naming_available = False
            self.naming_value.set(self.t(LABELS[FULL]))
            self.naming_box.configure(state="disabled")
            self.perks_available = False
            self.perks_value.set(self.t(PERK_LABELS[ON]))
            self.perks_box.configure(state="disabled")
            self.string_modes_available = False
            self.food_value.set(self.t(FOOD_LABELS[FOOD_DEFAULT]))
            self.junk_value.set(self.t(JUNK_LABELS[JUNK_DEFAULT]))
            self.food_box.configure(state="disabled")
            self.junk_box.configure(state="disabled")
            self.pending_selected_configuration = self.read_configuration()
            self.set_package("Drop a ZIP here or choose a package. Keep the ZIP unopened.")
            for b in (self.primary, self.repair, self.restore, self.play, self.apply):
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
        if self.last_status in ("ready", "update_available", "recovery_required"):
            self.start("recover" if self.last_status == "recovery_required" else "install")

    def confirm_modifications(self, resources):
        dialog = tk.Toplevel(self.root)
        dialog.title(self.t("Existing interface modifications detected"))
        dialog.transient(self.root)
        dialog.grab_set()
        accepted = [False]
        text = self.t("KKS found existing modifications in resources it needs to update. These may belong to another interface, sorting, or icon mod.\n\nKKS will preserve your current state as the installation baseline before replacing the resources it requires. Restore Baseline can later return KKS-managed resources to this state.\n\nContinue with KKS installation?")
        tk.Label(dialog, text=text, wraplength=510, justify="left", padx=20, pady=16).pack()
        details = tk.Text(dialog, height=5, width=65, wrap="word")
        details.insert("1.0", "\n".join(resources))
        details.configure(state="disabled")
        details.pack(padx=20)
        buttons = tk.Frame(dialog)
        buttons.pack(pady=16)
        def finish(value):
            accepted[0] = value
            dialog.destroy()
        tk.Button(buttons, text=self.t("Continue"), command=lambda: finish(True)).pack(side="left", padx=10)
        cancel = tk.Button(buttons, text=self.t("Cancel"), command=lambda: finish(False))
        cancel.pack(side="left", padx=10)
        cancel.focus_set()
        dialog.protocol("WM_DELETE_WINDOW", lambda: finish(False))
        dialog.bind("<Escape>", lambda event: finish(False))
        self.root.wait_window(dialog)
        return accepted[0]

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
        self.configuration_changed()
        if action == "apply" and not self.can_apply():
            if self.pending_selected_configuration == self.installed_verified_configuration:
                self.append("No changes to apply.")
            return
        game = self.path.get().strip()
        if not game:
            self.choose_game()
            return
        self.busy = True
        self.active_action = action
        naming, perks, food, junk = self.pending_selected_configuration
        self.naming_box.configure(state="disabled")
        self.perks_box.configure(state="disabled")
        self.food_box.configure(state="disabled")
        self.junk_box.configure(state="disabled")
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
            self.play,
            self.apply,
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
                "apply": "Installing the selected content package…",
                "repair": "Repairing installed content…",
                "restore": "Restoring the installation baseline…",
                "recover": "Recovering the interrupted operation…",
                "play": "Launching Fallout 76 through Steam…",
            }[action]
        )

        def work():
            try:
                manager = Manager(game, lambda text: self.events.put(("log", text)))
                release = (
                    manager.package(selected)
                    if selected and action not in ("select", "restore", "recover", "repair", "play")
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
                                "equipment_naming" in release.manifest,
                                "perk_cards" in release.manifest,
                                "string_modes" in release.manifest,
                            ),
                        )
                    )
                    result = manager.inspect(release,
                        naming=self.initial_naming if "equipment_naming" in release.manifest else FULL,
                        perks=self.initial_perks if "perk_cards" in release.manifest else ON,
                        food=self.initial_food if "string_modes" in release.manifest else FOOD_DEFAULT,
                        junk=self.initial_junk if "string_modes" in release.manifest else JUNK_DEFAULT)
                elif action == "check":
                    result = manager.inspect(release, naming=naming, perks=perks, food=food, junk=junk)
                elif action == "play":
                    result = manager.play()
                    self.events.put(("log", result["message"]))
                    result = manager.inspect()
                    result["play_available"] = False
                else:
                    consent = None
                    if action in ("install", "apply"):
                        inspection = manager.inspect(release, naming=naming, perks=perks, food=food, junk=junk)
                        if inspection.get("existing_modifications"):
                            ready, answer = threading.Event(), {}
                            self.events.put(("confirm", (inspection["existing_modifications"], ready, answer)))
                            ready.wait()
                            if not answer.get("accepted"):
                                self.events.put(("log", "Installation cancelled. Game files were not changed."))
                                self.events.put(("cancelled", inspection))
                                return
                            consent = inspection["confirmation_token"]
                    if action == "recover":
                        result = manager.recover()
                    elif action in ("install", "apply"):
                        result = manager.run(
                            "install", release, naming=naming, perks=perks,
                            food=food, junk=junk, accept_modifications=consent,
                        )
                    else:
                        # Repair and Restore use authenticated installed state, never the draft.
                        result = manager.run(action)
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
                if kind == "confirm":
                    resources, ready, answer = data
                    try:
                        answer["accepted"] = self.confirm_modifications(resources)
                    finally:
                        ready.set()
                    continue
                if kind == "log":
                    self.append(data)
                    continue
                if kind == "selected":
                    self.selected, name, file_count, language = data[:4]
                    self.naming_available = bool(len(data) > 4 and data[4])
                    self.naming_value.set(self.t(LABELS[self.initial_naming] if self.naming_available else LABELS[FULL]))
                    self.perks_available = bool(len(data) > 5 and data[5])
                    self.perks_value.set(self.t(PERK_LABELS[self.initial_perks] if self.perks_available else PERK_LABELS[ON]))
                    self.string_modes_available = bool(len(data) > 6 and data[6])
                    self.food_value.set(self.t(FOOD_LABELS[self.initial_food if self.string_modes_available else FOOD_DEFAULT]))
                    self.junk_value.set(self.t(JUNK_LABELS[self.initial_junk if self.string_modes_available else JUNK_DEFAULT]))
                    self.pending_selected_configuration = self.read_configuration()
                    self.configuration_apply_available = False
                    self.apply.configure(state="disabled")
                    self.set_package(
                        name
                        + f" · signature and all {file_count} files verified"
                        + "\n"
                        + (CONTENT_HINTS[language])
                    )
                    continue
                completed_action = self.active_action if kind == "success" else None
                self.active_action = None
                self.busy = False
                if kind != "error":
                    self.inspected_configuration(data, completed_action)
                self.language_box.configure(state="readonly")
                self.naming_box.configure(state="readonly" if self.naming_available else "disabled")
                self.perks_box.configure(state="readonly" if self.perks_available else "disabled")
                self.food_box.configure(state="readonly" if self.string_modes_available else "disabled")
                self.junk_box.configure(state="readonly" if self.string_modes_available else "disabled")
                self.progress.stop()
                self.progress.configure(value=0)
                for w in (self.entry, self.browse, self.check, self.package_button):
                    w.configure(state="normal")
                if kind == "error":
                    self.last_status = None
                    self.configuration_apply_available = False
                    for button in (self.primary, self.repair, self.restore, self.play, self.apply):
                        button.configure(state="disabled")
                    self.set_title("Needs attention before continuing", RED)
                    self.status_text(data)
                    self.append(data)
                else:
                    status = data["status"]
                    play_available = data.get("play_available", False)
                    if (data.get("installed_verified")
                            and data.get("selected_manifest") == self.installed_manifest):
                        # A different draft on the same package is not a package update.
                        status = "installed"
                        play_available = data.get("installed_play_available", play_available)
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
                    self.play.configure(state="normal" if play_available else "disabled")
                    self.apply.configure(state="normal" if self.can_apply() else "disabled")
        except queue.Empty:
            pass
        self.root.after(100, self.pump)

    def run(self):
        self.root.mainloop()


def launch(package=None, game=None, naming=FULL, perks=ON, food=FOOD_DEFAULT, junk=JUNK_DEFAULT):
    App(package, game, naming=naming, perks=perks, food=food, junk=junk).run()
