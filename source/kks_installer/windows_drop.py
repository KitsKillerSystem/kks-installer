"""Windows file-drop adapter. Dropping selects a ZIP; it never installs it."""

import os


def enable_file_drop(root, callback):
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes as w

    user = ctypes.WinDLL("user32", use_last_error=True)
    shell = ctypes.WinDLL("shell32", use_last_error=True)
    user.GetParent.argtypes = [w.HWND]
    user.GetParent.restype = w.HWND
    root.update_idletasks()
    hwnd = user.GetParent(root.winfo_id()) or root.winfo_id()
    proc_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
    user.SetWindowLongPtrW.argtypes = [w.HWND, ctypes.c_int, ctypes.c_void_p]
    user.SetWindowLongPtrW.restype = ctypes.c_void_p
    user.CallWindowProcW.argtypes = [ctypes.c_void_p, w.HWND, w.UINT, w.WPARAM, w.LPARAM]
    user.CallWindowProcW.restype = ctypes.c_ssize_t
    shell.DragAcceptFiles.argtypes = [w.HWND, w.BOOL]
    shell.DragQueryFileW.argtypes = [w.HANDLE, w.UINT, w.LPWSTR, w.UINT]
    shell.DragQueryFileW.restype = w.UINT
    shell.DragFinish.argtypes = [w.HANDLE]
    previous = None

    def window_proc(handle, message, wp, lp):
        if message == 0x0233:
            try:
                count = shell.DragQueryFileW(wp, 0xFFFFFFFF, None, 0)
                paths = []
                if count == 1:
                    size = shell.DragQueryFileW(wp, 0, None, 0)
                    if 0 < size < 32768:
                        buffer = ctypes.create_unicode_buffer(size + 1)
                        shell.DragQueryFileW(wp, 0, buffer, size + 1)
                        paths.append(buffer.value)
                root.after(0, lambda: callback(paths))
            finally:
                shell.DragFinish(wp)
            return 0
        return user.CallWindowProcW(previous, handle, message, wp, lp)

    handler = proc_type(window_proc)
    ctypes.set_last_error(0)
    previous = user.SetWindowLongPtrW(hwnd, -4, ctypes.cast(handler, ctypes.c_void_p))
    if not previous and ctypes.get_last_error():
        raise OSError("Windows file drop could not be enabled")
    shell.DragAcceptFiles(hwnd, True)
    return (handler, previous, hwnd)
