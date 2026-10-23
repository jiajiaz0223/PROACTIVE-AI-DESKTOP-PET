"""Launch the local AI desktop reminder application."""
from pathlib import Path
import argparse
import os
import tkinter as tk
from tkinter import messagebox
from proactive_pet.runtime import ensure_runtime
from proactive_pet.ui.app import Application


def main():
    if os.name == 'nt':
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    parser = argparse.ArgumentParser()
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--data-dir')
    parser.add_argument('--smoke-seconds', type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    project = Path(__file__).resolve().parent
    data = Path(args.data_dir or project / 'data')
    data.mkdir(parents=True, exist_ok=True)
    lock = (data / ('demo.lock' if args.demo else 'events.lock')).open('a+b')
    lock.seek(0)
    lock.write(b'0')
    lock.flush()
    lock.seek(0)
    try:
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo('呱呱已啟動', '這個模式已在執行，請查看工作列。')
        root.destroy()
        return
    ensure_runtime(project)
    root = tk.Tk()
    app = Application(root, project, args.demo, data)
    if args.smoke_seconds:
        root.after(args.smoke_seconds * 1000, app.close)
    try:
        root.mainloop()
    finally:
        lock.close()


if __name__ == '__main__':
    main()
