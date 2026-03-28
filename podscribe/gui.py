from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog, ttk
    TK_IMPORT_ERROR = None
except ModuleNotFoundError as error:
    tk = None
    filedialog = None
    messagebox = None
    simpledialog = None
    ttk = None
    TK_IMPORT_ERROR = error

from podscribe.app_service import (
    DEFAULT_OUTPUT_DIR,
    PodscribeError,
    build_request,
    normalize_config,
    process_episode,
)
from podscribe.config import load_config, save_config
from podscribe.setup_helper import resolve_api_key, save_api_key


def split_episode_urls(raw: str) -> list[str]:
    return [url.strip() for url in raw.split(',') if url.strip()]


def reveal_directory(path: Path):
    resolved = path.expanduser().resolve()
    if sys.platform == 'darwin':
        subprocess.run(['open', str(resolved)], check=False)
        return
    if sys.platform.startswith('win'):
        os.startfile(str(resolved))  # type: ignore[attr-defined]
        return
    subprocess.run(['xdg-open', str(resolved)], check=False)


class PodScribeApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title('PodScribe')
        self.root.geometry('760x560')
        self.root.minsize(720, 500)

        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.worker: threading.Thread | None = None

        config = normalize_config(load_config())
        self.url_var = tk.StringVar()
        self.output_dir_var = tk.StringVar(value=config['output_dir'])
        self.audio_dir_var = tk.StringVar(value=config['audio_dir'] or str(DEFAULT_OUTPUT_DIR / 'audio'))
        self.use_ai_var = tk.BooleanVar(value=config['use_ai'])
        self.save_audio_var = tk.BooleanVar(value=config['save_audio'])
        self.txt_var = tk.BooleanVar(value='txt' in config['output_formats'])
        self.srt_var = tk.BooleanVar(value='srt' in config['output_formats'])
        self.status_var = tk.StringVar(value='Ready')

        self._build_ui()
        self.root.after(150, self._poll_events)

    def _build_ui(self):
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)

        title = ttk.Label(frame, text='PodScribe Desktop', font=('', 18, 'bold'))
        title.grid(row=0, column=0, columnspan=4, sticky='w')

        subtitle = ttk.Label(
            frame,
            text='Paste Xiaoyuzhou episode URLs, then run the existing PodScribe pipeline without the terminal UI.',
        )
        subtitle.grid(row=1, column=0, columnspan=4, sticky='w', pady=(4, 16))

        ttk.Label(frame, text='Episode URL(s)').grid(row=2, column=0, sticky='nw', pady=(0, 8))
        url_entry = ttk.Entry(frame, textvariable=self.url_var)
        url_entry.grid(row=2, column=1, columnspan=3, sticky='ew', pady=(0, 8))
        url_entry.focus_set()

        ttk.Label(frame, text='Output directory').grid(row=3, column=0, sticky='w', pady=(0, 8))
        ttk.Entry(frame, textvariable=self.output_dir_var).grid(row=3, column=1, columnspan=2, sticky='ew', pady=(0, 8))
        ttk.Button(frame, text='Browse...', command=self._choose_output_dir).grid(row=3, column=3, sticky='e', pady=(0, 8))

        ttk.Label(frame, text='Audio directory').grid(row=4, column=0, sticky='w', pady=(0, 8))
        self.audio_dir_entry = ttk.Entry(frame, textvariable=self.audio_dir_var)
        self.audio_dir_entry.grid(row=4, column=1, columnspan=2, sticky='ew', pady=(0, 8))
        self.audio_dir_button = ttk.Button(frame, text='Browse...', command=self._choose_audio_dir)
        self.audio_dir_button.grid(row=4, column=3, sticky='e', pady=(0, 8))

        options = ttk.LabelFrame(frame, text='Options', padding=12)
        options.grid(row=5, column=0, columnspan=4, sticky='ew', pady=(8, 12))
        ttk.Checkbutton(options, text='TXT output', variable=self.txt_var).grid(row=0, column=0, sticky='w')
        ttk.Checkbutton(options, text='SRT output', variable=self.srt_var).grid(row=0, column=1, sticky='w')
        ttk.Checkbutton(options, text='AI post-process', variable=self.use_ai_var).grid(row=1, column=0, sticky='w', pady=(8, 0))
        ttk.Checkbutton(options, text='Save audio locally', variable=self.save_audio_var).grid(row=1, column=1, sticky='w', pady=(8, 0))

        actions = ttk.Frame(frame)
        actions.grid(row=6, column=0, columnspan=4, sticky='ew', pady=(0, 12))
        actions.columnconfigure(2, weight=1)
        ttk.Button(actions, text='API Key...', command=self._configure_api_key).grid(row=0, column=0, sticky='w')
        ttk.Button(actions, text='Open Output Folder', command=self._open_output_dir).grid(row=0, column=1, sticky='w', padx=(8, 0))
        self.start_button = ttk.Button(actions, text='Start Transcription', command=self._start)
        self.start_button.grid(row=0, column=3, sticky='e')

        ttk.Label(frame, textvariable=self.status_var).grid(row=7, column=0, columnspan=4, sticky='w', pady=(0, 8))

        self.log = tk.Text(frame, height=18, wrap='word', state='disabled')
        self.log.grid(row=8, column=0, columnspan=4, sticky='nsew')
        frame.rowconfigure(8, weight=1)
        self.save_audio_var.trace_add('write', lambda *_: self._sync_audio_controls())
        self._sync_audio_controls()

    def _sync_audio_controls(self):
        state = 'normal' if self.save_audio_var.get() else 'disabled'
        self.audio_dir_entry.configure(state=state)
        self.audio_dir_button.configure(state=state)

    def _choose_output_dir(self):
        selected = filedialog.askdirectory(initialdir=self.output_dir_var.get() or str(DEFAULT_OUTPUT_DIR))
        if selected:
            self.output_dir_var.set(selected)

    def _choose_audio_dir(self):
        selected = filedialog.askdirectory(initialdir=self.audio_dir_var.get() or str(DEFAULT_OUTPUT_DIR / 'audio'))
        if selected:
            self.audio_dir_var.set(selected)

    def _configure_api_key(self):
        current = resolve_api_key() or ''
        api_key = simpledialog.askstring(
            'DashScope API Key',
            'Paste your DashScope API Key:',
            initialvalue=current,
            show='*',
            parent=self.root,
        )
        if api_key and api_key.strip():
            save_api_key(api_key.strip())
            messagebox.showinfo('PodScribe', 'API Key saved.')

    def _open_output_dir(self):
        output_dir = Path(self.output_dir_var.get() or str(DEFAULT_OUTPUT_DIR)).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        reveal_directory(output_dir)

    def _start(self):
        if self.worker and self.worker.is_alive():
            return

        urls = split_episode_urls(self.url_var.get())
        if not urls:
            messagebox.showerror('PodScribe', 'Please enter at least one episode URL.')
            return

        formats = []
        if self.txt_var.get():
            formats.append('txt')
        if self.srt_var.get():
            formats.append('srt')
        if not formats:
            messagebox.showerror('PodScribe', 'Select at least one output format.')
            return

        api_key = resolve_api_key()
        if not api_key:
            self._configure_api_key()
            api_key = resolve_api_key()
        if not api_key:
            messagebox.showerror('PodScribe', 'DashScope API Key is required.')
            return

        config = normalize_config({
            'output_formats': formats,
            'output_dir': self.output_dir_var.get().strip() or str(DEFAULT_OUTPUT_DIR),
            'save_audio': self.save_audio_var.get(),
            'audio_dir': self.audio_dir_var.get().strip() or None,
            'use_ai': self.use_ai_var.get(),
        })
        save_config(config)

        self._append_log('Starting batch...')
        self.status_var.set('Running...')
        self.start_button.configure(state='disabled')
        self.worker = threading.Thread(
            target=self._run_batch,
            args=(urls, config),
            daemon=True,
        )
        self.worker.start()

    def _run_batch(self, urls: list[str], config: dict):
        results: list[str] = []
        try:
            for index, url in enumerate(urls, start=1):
                request = build_request(url, config, index=index, total=len(urls))
                result = process_episode(
                    request,
                    progress_callback=lambda event: self.events.put(('progress', event.message)),
                )
                results.extend(result.output_files)
            self.events.put(('done', results))
        except KeyboardInterrupt:
            self.events.put(('error', 'Interrupted by user.'))
        except PodscribeError as error:
            self.events.put(('error', str(error)))
        except Exception as error:
            self.events.put(('error', f'Unexpected error: {error}'))

    def _poll_events(self):
        while True:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break

            if kind == 'progress':
                self.status_var.set(str(payload))
                self._append_log(str(payload))
            elif kind == 'done':
                self.status_var.set('Done')
                self.start_button.configure(state='normal')
                files = payload if isinstance(payload, list) else []
                if files:
                    self._append_log('Output files:')
                    for path in files:
                        self._append_log(f'  {path}')
                messagebox.showinfo('PodScribe', 'Transcription complete.')
            elif kind == 'error':
                self.status_var.set('Failed')
                self.start_button.configure(state='normal')
                self._append_log(str(payload))
                messagebox.showerror('PodScribe', str(payload))

        if not (self.worker and self.worker.is_alive()) and self.start_button['state'] == 'disabled':
            self.start_button.configure(state='normal')
        self.root.after(150, self._poll_events)

    def _append_log(self, message: str):
        self.log.configure(state='normal')
        self.log.insert('end', f'{message}\n')
        self.log.see('end')
        self.log.configure(state='disabled')


def main():
    if TK_IMPORT_ERROR is not None:
        raise RuntimeError(
            'Tkinter is not available in this Python environment. '
            'Install a Tk-enabled Python build before launching the desktop app.'
        ) from TK_IMPORT_ERROR
    root = tk.Tk()
    style = ttk.Style(root)
    if 'aqua' in style.theme_names():
        style.theme_use('aqua')
    app = PodScribeApp(root)
    app.root.mainloop()


if __name__ == '__main__':
    main()
