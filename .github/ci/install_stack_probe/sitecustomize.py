"""Bounded installation diagnostics for the disposable CI install process."""

import os
import sys
import threading


if os.environ.get("CONSTRUCTION_CI_INSTALL_PROBE") == "1":

    def dump_install_stack():
        frame = sys._current_frames().get(threading.main_thread().ident)
        stack = []
        progress = None
        while frame is not None and len(stack) < 4000:
            if frame.f_code.co_name == "import_released_overrides":
                # Numeric progress from the disposable CI import only. Never
                # print translation content, document values, or other locals.
                progress = {
                    key: frame.f_locals[key]
                    for key in ("total", "created", "updated", "skipped", "drift")
                    if type(frame.f_locals.get(key)) is int
                }
            stack.append((frame.f_code.co_filename, frame.f_lineno, frame.f_code.co_name))
            frame = frame.f_back
        stack.reverse()
        if progress is not None:
            print(f"CI translation import progress: {progress}", flush=True)
        print("CI install main-thread stack (filenames/functions only; no locals):", flush=True)
        selected = stack if len(stack) <= 80 else stack[:40] + stack[-40:]
        print(f"Observed frames: {len(stack)} (traversal bounded at 4000)", flush=True)
        for filename, lineno, function in selected:
            print(f"  {filename}:{lineno} in {function}", flush=True)

    timers = []
    for seconds in (45, 180, 360, 720, 1440):
        timer = threading.Timer(seconds, dump_install_stack)
        timer.daemon = True
        timer.start()
        timers.append(timer)
