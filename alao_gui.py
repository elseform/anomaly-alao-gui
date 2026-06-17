"""
Tkinter GUI for ALAO.
"""

import queue
import shlex
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from tkinter import (
    BooleanVar,
    Button,
    Checkbutton,
    Entry,
    Frame,
    Label,
    LabelFrame,
    OptionMenu,
    StringVar,
    Tk,
    filedialog,
    messagebox,
)
from tkinter.scrolledtext import ScrolledText


APP_DIR = Path(__file__).resolve().parent
CLI_SCRIPT = APP_DIR / "stalker_lua_lint.py"


class ALAOGui:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title("ALAO - Anomaly Lua Auto Optimizer")
        self.root.geometry("980x720")
        self.root.minsize(780, 560)

        self.output_queue = queue.Queue()
        self.active_process = None
        self.active_thread = None
        self.last_report_path = None

        self.path_var = StringVar()
        self.modlist_var = StringVar()
        self.update_status_var = StringVar(value="Updating repository...")

        self.fix_safe_var = BooleanVar(value=True)
        self.fix_yellow_var = BooleanVar(value=False)
        self.fix_debug_var = BooleanVar(value=False)
        self.fix_nil_var = BooleanVar(value=False)
        self.remove_dead_code_var = BooleanVar(value=False)
        self.experimental_var = BooleanVar(value=False)

        self.direct_var = BooleanVar(value=False)
        self.backup_var = BooleanVar(value=True)
        self.first_time_backup_var = BooleanVar(value=True)
        self.backup_all_var = BooleanVar(value=False)
        self.verbose_var = BooleanVar(value=False)
        self.quiet_var = BooleanVar(value=False)

        self.cache_threshold_var = StringVar(value="4")
        self.timeout_var = StringVar(value="10")
        self.workers_var = StringVar(value="")
        self.report_format_var = StringVar(value="html")

        self._build_ui()
        self._poll_output()
        self._check_repo_status()

    def _build_ui(self):
        top = Frame(self.root, padx=12, pady=10)
        top.pack(fill="x")

        Label(top, text="Repository").grid(row=0, column=0, sticky="w")
        Label(top, textvariable=self.update_status_var, anchor="w").grid(
            row=0, column=1, columnspan=2, sticky="ew", padx=(8, 0)
        )
        Button(top, text="Update", command=self.update_repository).grid(
            row=0, column=3, sticky="ew", padx=(8, 0)
        )

        Label(top, text="Folder").grid(row=1, column=0, sticky="w", pady=(8, 0))
        Entry(top, textvariable=self.path_var).grid(
            row=1, column=1, columnspan=2, sticky="ew", padx=(8, 8), pady=(8, 0)
        )
        Button(top, text="Browse...", command=self._choose_folder).grid(
            row=1, column=3, sticky="ew", pady=(8, 0)
        )
        Label(top, text="Modlist").grid(row=2, column=0, sticky="w", pady=(8, 0))
        Entry(top, textvariable=self.modlist_var).grid(
            row=2, column=1, columnspan=2, sticky="ew", padx=(8, 8), pady=(8, 0)
        )
        Button(top, text="Browse...", command=self._choose_modlist).grid(
            row=2, column=3, sticky="ew", pady=(8, 0)
        )
        top.columnconfigure(1, weight=1)

        middle = Frame(self.root, padx=12)
        middle.pack(fill="x")

        fixes = LabelFrame(middle, text="Fix Types", padx=10, pady=8)
        fixes.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        Checkbutton(fixes, text="Safe GREEN fixes", variable=self.fix_safe_var).grid(
            row=0, column=0, sticky="w"
        )
        Checkbutton(fixes, text="Unsafe YELLOW fixes", variable=self.fix_yellow_var).grid(
            row=1, column=0, sticky="w"
        )
        Checkbutton(fixes, text="Comment debug logging", variable=self.fix_debug_var).grid(
            row=2, column=0, sticky="w"
        )
        Checkbutton(fixes, text="Add safe nil guards", variable=self.fix_nil_var).grid(
            row=3, column=0, sticky="w"
        )
        Checkbutton(fixes, text="Remove safe dead code", variable=self.remove_dead_code_var).grid(
            row=4, column=0, sticky="w"
        )
        Checkbutton(fixes, text="Experimental string concat fix", variable=self.experimental_var).grid(
            row=5, column=0, sticky="w"
        )

        options = LabelFrame(middle, text="Options", padx=10, pady=8)
        options.grid(row=0, column=1, sticky="nsew")

        Checkbutton(options, text="Direct mode", variable=self.direct_var).grid(
            row=0, column=0, sticky="w"
        )
        Checkbutton(options, text="Create .alao-bak files", variable=self.backup_var).grid(
            row=1, column=0, sticky="w"
        )
        Checkbutton(options, text="First-run zip backup", variable=self.first_time_backup_var).grid(
            row=2, column=0, sticky="w"
        )
        Checkbutton(options, text="Backup all scripts before run", variable=self.backup_all_var).grid(
            row=3, column=0, sticky="w"
        )
        Checkbutton(options, text="Verbose output", variable=self.verbose_var).grid(
            row=4, column=0, sticky="w"
        )
        Checkbutton(options, text="Quiet output", variable=self.quiet_var).grid(
            row=5, column=0, sticky="w"
        )

        settings = LabelFrame(middle, text="Processing", padx=10, pady=8)
        settings.grid(row=0, column=2, sticky="nsew", padx=(8, 0))

        Label(settings, text="Cache threshold").grid(row=0, column=0, sticky="w")
        Entry(settings, textvariable=self.cache_threshold_var, width=8).grid(
            row=0, column=1, sticky="w", padx=(8, 0)
        )
        Label(settings, text="Timeout seconds").grid(row=1, column=0, sticky="w")
        Entry(settings, textvariable=self.timeout_var, width=8).grid(
            row=1, column=1, sticky="w", padx=(8, 0)
        )
        Label(settings, text="Workers").grid(row=2, column=0, sticky="w")
        Entry(settings, textvariable=self.workers_var, width=8).grid(
            row=2, column=1, sticky="w", padx=(8, 0)
        )
        Label(settings, text="Blank workers = automatic").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )
        Label(settings, text="Report format").grid(row=4, column=0, sticky="w", pady=(8, 0))
        OptionMenu(settings, self.report_format_var, "html", "txt", "json").grid(
            row=4, column=1, sticky="ew", padx=(8, 0), pady=(8, 0)
        )

        middle.columnconfigure(0, weight=1)
        middle.columnconfigure(1, weight=1)
        middle.columnconfigure(2, weight=1)

        actions = Frame(self.root, padx=12, pady=10)
        actions.pack(fill="x")

        self.analyze_button = Button(actions, text="Analyze", command=self.analyze)
        self.analyze_button.pack(side="left")
        self.fix_button = Button(actions, text="Apply Selected Fixes", command=self.apply_fixes)
        self.fix_button.pack(side="left", padx=(8, 0))
        self.report_button = Button(actions, text="Generate Report", command=self.generate_report)
        self.report_button.pack(side="left", padx=(8, 0))
        self.backup_button = Button(actions, text="Backup All Scripts", command=self.backup_all_scripts)
        self.backup_button.pack(side="left", padx=(8, 0))
        self.list_button = Button(actions, text="List Backups", command=self.list_backups)
        self.list_button.pack(side="left", padx=(8, 0))
        self.revert_button = Button(actions, text="Revert", command=self.revert)
        self.revert_button.pack(side="left", padx=(8, 0))
        self.clean_button = Button(actions, text="Clean Backups", command=self.clean_backups)
        self.clean_button.pack(side="left", padx=(8, 0))
        self.open_report_button = Button(actions, text="Open Report", command=self.open_report)
        self.open_report_button.pack(side="left", padx=(8, 0))
        self.stop_button = Button(actions, text="Stop", command=self.stop_process, state="disabled")
        self.stop_button.pack(side="right")

        log_frame = LabelFrame(self.root, text="Output", padx=8, pady=8)
        log_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.output = ScrolledText(log_frame, wrap="word", height=18)
        self.output.pack(fill="both", expand=True)

    def _choose_folder(self):
        folder = filedialog.askdirectory(title="Select folder to analyze")
        if folder:
            self.path_var.set(folder)
            if not self.modlist_var.get().strip():
                guessed_modlist = self._guess_modlist(Path(folder))
                if guessed_modlist is not None:
                    self.modlist_var.set(str(guessed_modlist))

    def _choose_modlist(self):
        file_path = filedialog.askopenfilename(
            title="Select MO2 modlist.txt",
            filetypes=(("MO2 modlist", "modlist.txt"), ("Text files", "*.txt"), ("All files", "*.*")),
        )
        if file_path:
            self.modlist_var.set(file_path)

    def _guess_modlist(self, folder: Path):
        if folder.name != "mods":
            return None

        profiles_dir = folder.parent / "profiles"
        if not profiles_dir.exists():
            return None

        candidates = sorted(profiles_dir.glob("*/modlist.txt"))
        if len(candidates) == 1:
            return candidates[0]
        return None

    def _check_repo_status(self):
        def check_repo():
            try:
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=APP_DIR,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=30,
                )
            except subprocess.TimeoutExpired:
                self.output_queue.put(("status", "Repository status check timed out."))
                return

            if result.returncode != 0:
                self.output_queue.put(("status", "Repository status unavailable."))
            elif result.stdout.strip():
                self.output_queue.put(("status", "Local changes present. Manual update disabled until clean."))
            else:
                self.output_queue.put(("status", "Repository clean. Use Update to pull upstream."))

        threading.Thread(target=check_repo, daemon=True).start()

    def update_repository(self):
        if self.active_process is not None:
            messagebox.showwarning("Busy", "A command is already running.")
            return

        def update_repo():
            self._write_output("Checking repository before update...\n")
            try:
                status = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=APP_DIR,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=30,
                )
            except subprocess.TimeoutExpired:
                self._write_output("git status timed out after 30 seconds.\n")
                self.output_queue.put(("status", "Repository status check timed out."))
                return

            if status.returncode != 0:
                self._write_output(status.stdout)
                self.output_queue.put(("status", "Repository status check failed."))
                return

            if status.stdout.strip():
                self._write_output("Update skipped: local changes are present.\n")
                self.output_queue.put(("status", "Local changes present. Commit/stash before updating."))
                return

            self._write_output("Updating repository...\n")
            try:
                result = subprocess.run(
                    ["git", "pull", "--ff-only"],
                    cwd=APP_DIR,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=120,
                )
            except subprocess.TimeoutExpired:
                self._write_output("git pull timed out after 120 seconds.\n")
                self.output_queue.put(("status", "Repository update timed out."))
                return

            text = result.stdout.strip()
            if text:
                self._write_output(text + "\n")
            if result.returncode == 0:
                self.output_queue.put(("status", "Repository is up to date."))
            else:
                self.output_queue.put(("status", "Repository update failed. See output."))

        threading.Thread(target=update_repo, daemon=True).start()

    def _base_command(self):
        raw_target = self.path_var.get().strip()
        if not raw_target:
            messagebox.showerror("Missing folder", "Choose a folder to analyze first.")
            return None
        target = Path(raw_target)
        if not target.exists():
            messagebox.showerror("Invalid folder", f"Path does not exist:\n{target}")
            return None

        command = [sys.executable, str(CLI_SCRIPT), str(target)]

        modlist = self.modlist_var.get().strip()
        if modlist:
            modlist_path = Path(modlist)
            if not modlist_path.exists():
                messagebox.showerror("Invalid modlist", f"Modlist does not exist:\n{modlist_path}")
                return None
            command.extend(["--modlist", str(modlist_path)])

        if self.direct_var.get():
            command.append("--direct")
        if not self.backup_var.get():
            command.append("--no-backup")
        if not self.first_time_backup_var.get():
            command.append("--no-first-time-auto-backup")
        if self.verbose_var.get() and not self.quiet_var.get():
            command.append("--verbose")
        if self.quiet_var.get():
            command.append("--quiet")

        try:
            cache_threshold = max(2, int(self.cache_threshold_var.get()))
        except ValueError:
            messagebox.showerror("Invalid setting", "Cache threshold must be a number.")
            return None
        command.extend(["--cache-threshold", str(cache_threshold)])

        timeout = self.timeout_var.get().strip()
        if timeout:
            try:
                float(timeout)
            except ValueError:
                messagebox.showerror("Invalid setting", "Timeout must be a number.")
                return None
            command.extend(["--timeout", timeout])

        workers = self.workers_var.get().strip()
        if workers:
            try:
                workers_int = int(workers)
            except ValueError:
                messagebox.showerror("Invalid setting", "Workers must be a whole number.")
                return None
            if workers_int < 1:
                messagebox.showerror("Invalid setting", "Workers must be at least 1.")
                return None
            command.extend(["--workers", workers])

        return command

    def _add_report_option(self, command):
        target = Path(self.path_var.get().strip())
        report_format = self.report_format_var.get()
        if report_format not in ("html", "txt", "json"):
            report_format = "html"
        report_path = (
            target / f"alao_report.{report_format}"
            if target.is_dir()
            else target.with_suffix(f".alao_report.{report_format}")
        )
        self.last_report_path = report_path
        command.extend(["--report", str(report_path)])

    def _run_command(self, command, title, stdin_text=None):
        if self.active_process is not None:
            messagebox.showwarning("Busy", "A command is already running.")
            return

        self._set_running(True)
        self._write_output(f"\n=== {title} ===\n")
        self._write_output(shlex.join(command) + "\n\n")

        def run_process(process_command, process_stdin=None):
            self.active_process = subprocess.Popen(
                process_command,
                cwd=APP_DIR,
                text=True,
                stdin=subprocess.PIPE if process_stdin is not None else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
            )

            if process_stdin is not None and self.active_process.stdin is not None:
                self.active_process.stdin.write(process_stdin)
                self.active_process.stdin.close()

            for line in self.active_process.stdout or []:
                self._write_output(line)

            return self.active_process.wait()

        def worker():
            try:
                return_code = run_process(command, stdin_text)
                self._write_output(f"\nCommand finished with exit code {return_code}.\n")
            except Exception as exc:
                self._write_output(f"\nCommand failed: {exc}\n")
            finally:
                self.active_process = None
                self.output_queue.put(("running", False))

        self.active_thread = threading.Thread(target=worker, daemon=True)
        self.active_thread.start()

    def _selected_fix_args(self):
        args = []
        if self.fix_safe_var.get():
            args.append("--fix")
        if self.fix_yellow_var.get():
            args.append("--fix-yellow")
        if self.fix_debug_var.get():
            args.append("--fix-debug")
        if self.fix_nil_var.get():
            args.append("--fix-nil")
        if self.remove_dead_code_var.get():
            args.append("--remove-dead-code")
        if self.experimental_var.get():
            args.append("--experimental")
        return args

    def analyze(self):
        command = self._base_command()
        if command is None:
            return
        self._run_command(command, "Analyze")

    def apply_fixes(self):
        fix_args = self._selected_fix_args()
        if not fix_args:
            messagebox.showerror("No fixes selected", "Select at least one fix type first.")
            return
        command = self._base_command()
        if command is None:
            return
        command.extend(fix_args)
        if self.backup_all_var.get():
            command.append("--backup-all-scripts")

        self._run_command(command, "Apply Selected Fixes")

    def generate_report(self):
        command = self._base_command()
        if command is None:
            return
        self._add_report_option(command)
        self._run_command(command, "Generate Report")

    def backup_all_scripts(self):
        command = self._base_command()
        if command is None:
            return
        command.append("--backup-all-scripts")
        self._run_command(command, "Backup All Scripts")

    def list_backups(self):
        command = self._base_command()
        if command is None:
            return
        command.append("--list-backups")
        self._run_command(command, "List Backups")

    def revert(self):
        if not messagebox.askyesno("Confirm revert", "Restore files from .alao-bak backups?"):
            return
        command = self._base_command()
        if command is None:
            return
        command.append("--revert")
        self._run_command(command, "Revert", stdin_text="y\n")

    def clean_backups(self):
        if not messagebox.askyesno("Confirm cleanup", "Delete all .alao-bak backup files?"):
            return
        command = self._base_command()
        if command is None:
            return
        command.append("--clean-backups")
        self._run_command(command, "Clean Backups", stdin_text="y\n")

    def open_report(self):
        if self.last_report_path and self.last_report_path.exists():
            webbrowser.open(self.last_report_path.as_uri())
            return
        messagebox.showinfo("No report", "No generated report was found yet.")

    def stop_process(self):
        if self.active_process is not None:
            self.active_process.terminate()
            self._write_output("\nStop requested.\n")

    def _set_running(self, running):
        state = "disabled" if running else "normal"
        for button in (
            self.analyze_button,
            self.fix_button,
            self.report_button,
            self.backup_button,
            self.list_button,
            self.revert_button,
            self.clean_button,
        ):
            button.configure(state=state)
        self.stop_button.configure(state="normal" if running else "disabled")

    def _write_output(self, text):
        self.output_queue.put(("text", text))

    def _poll_output(self):
        try:
            while True:
                kind, payload = self.output_queue.get_nowait()
                if kind == "text":
                    self.output.insert("end", payload)
                    self.output.see("end")
                elif kind == "running":
                    self._set_running(payload)
                elif kind == "status":
                    self.update_status_var.set(payload)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_output)


def main():
    root = Tk()
    ALAOGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
