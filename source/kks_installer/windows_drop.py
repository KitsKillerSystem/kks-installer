"""Windows drops select a ZIP, never install it. Native callbacks never call Tcl."""

import os
import queue


class _DropBinding:
    def __init__(self, root, callback):
        import ctypes
        from ctypes import wintypes as w

        self.root = root
        self.callback = callback
        self.pending = queue.SimpleQueue()
        self.closed = False
        self.timer = None
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.shell = ctypes.WinDLL("shell32", use_last_error=True)
        self.common = ctypes.WinDLL("comctl32", use_last_error=True)
        self.user.GetParent.argtypes = [w.HWND]
        self.user.GetParent.restype = w.HWND
        root.update_idletasks()
        self.hwnd = self.user.GetParent(root.winfo_id()) or root.winfo_id()
        self.identifier = id(self)
        proc_type = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t,
            w.HWND,
            w.UINT,
            w.WPARAM,
            w.LPARAM,
            ctypes.c_size_t,
            ctypes.c_size_t,
        )
        self.common.SetWindowSubclass.argtypes = [
            w.HWND,
            proc_type,
            ctypes.c_size_t,
            ctypes.c_size_t,
        ]
        self.common.SetWindowSubclass.restype = w.BOOL
        self.common.RemoveWindowSubclass.argtypes = [w.HWND, proc_type, ctypes.c_size_t]
        self.common.RemoveWindowSubclass.restype = w.BOOL
        self.common.DefSubclassProc.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
        self.common.DefSubclassProc.restype = ctypes.c_ssize_t
        self.shell.DragAcceptFiles.argtypes = [w.HWND, w.BOOL]
        self.shell.DragAcceptFiles.restype = None
        self.shell.DragQueryFileW.argtypes = [w.HANDLE, w.UINT, w.LPWSTR, w.UINT]
        self.shell.DragQueryFileW.restype = w.UINT
        self.shell.DragFinish.argtypes = [w.HANDLE]
        self.shell.DragFinish.restype = None

        def window_proc(handle, message, wp, lp, identifier, reference):
            if message == 0x0233:  # WM_DROPFILES
                paths = []
                try:
                    count = self.shell.DragQueryFileW(wp, 0xFFFFFFFF, None, 0)
                    if count == 1:
                        size = self.shell.DragQueryFileW(wp, 0, None, 0)
                        if 0 < size < 32768:
                            buffer = ctypes.create_unicode_buffer(size + 1)
                            if self.shell.DragQueryFileW(wp, 0, buffer, size + 1) == size:
                                paths.append(buffer.value)
                except Exception:
                    paths = []
                finally:
                    self.shell.DragFinish(wp)
                if not self.closed:
                    self.pending.put(paths)
                return 0
            if message == 0x0082:  # WM_NCDESTROY: no Tcl calls during teardown.
                self.closed = True
                self.common.RemoveWindowSubclass(handle, self.handler, self.identifier)
            return self.common.DefSubclassProc(handle, message, wp, lp)

        self.handler = proc_type(window_proc)
        if not self.common.SetWindowSubclass(self.hwnd, self.handler, self.identifier, 0):
            raise OSError("Windows file drop could not be enabled")
        self.shell.DragAcceptFiles(self.hwnd, True)
        self.timer = root.after(50, self._pump)

    def _pump(self):
        self.timer = None
        if self.closed:
            return
        try:
            # Bounded work on the ordinary Tk loop, outside native message dispatch.
            for _ in range(8):
                self.callback(self.pending.get_nowait())
        except queue.Empty:
            pass
        finally:
            if not self.closed:
                self.timer = self.root.after(50, self._pump)

    def close(self):
        if not self.closed:
            self.shell.DragAcceptFiles(self.hwnd, False)
            self.common.RemoveWindowSubclass(self.hwnd, self.handler, self.identifier)
            self.closed = True
        if self.timer is not None:
            self.root.after_cancel(self.timer)
            self.timer = None


def enable_file_drop(root, callback):
    if os.name != "nt":
        return None
    previous = getattr(root, "_kks_drop_binding", None)
    if previous is not None:
        previous.close()
    binding = _DropBinding(root, callback)
    # Keep the callback alive through the native window lifetime even if the
    # caller discards the return value; collected callbacks crash native dispatch.
    root._kks_drop_binding = binding
    return binding
