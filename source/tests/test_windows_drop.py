"""Real WM_DROPFILES regression checks on Windows, using hidden Tk windows."""

import ctypes, gc, os, struct, unittest
from ctypes import wintypes as w
from kks_installer.windows_drop import enable_file_drop


@unittest.skipUnless(os.name == "nt", "Windows native drop integration")
class WindowsDropTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk

        self.root = tk.Tk()
        self.root.withdraw()
        self.received = []
        self.binding = enable_file_drop(self.root, self.received.append)
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.GlobalAlloc.argtypes = [w.UINT, ctypes.c_size_t]
        self.kernel.GlobalAlloc.restype = w.HGLOBAL
        self.kernel.GlobalLock.argtypes = [w.HGLOBAL]
        self.kernel.GlobalLock.restype = ctypes.c_void_p
        self.kernel.GlobalUnlock.argtypes = [w.HGLOBAL]
        self.kernel.GlobalUnlock.restype = w.BOOL
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.user.SendMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
        self.user.SendMessageW.restype = ctypes.c_ssize_t

    def tearDown(self):
        self.binding.close()
        self.root.destroy()

    def send(self, paths):
        payload = struct.pack("<IiiII", 20, 0, 0, 0, 1) + ("\0".join(paths) + "\0\0").encode(
            "utf-16le"
        )
        handle = self.kernel.GlobalAlloc(0x42, len(payload))
        self.assertTrue(handle)
        address = self.kernel.GlobalLock(handle)
        self.assertTrue(address)
        ctypes.memmove(address, payload, len(payload))
        self.kernel.GlobalUnlock(handle)
        # Any Tcl scheduling from native dispatch is a regression. The normal
        # event loop will drain the queue after SendMessage has returned.
        previous = self.root.after
        self.root.after = lambda *args: (_ for _ in ()).throw(
            AssertionError("Tcl entered inside native drop dispatch")
        )
        try:
            self.assertEqual(self.user.SendMessageW(self.binding.hwnd, 0x233, handle, 0), 0)
        finally:
            self.root.after = previous

    def drain(self):
        if self.binding.timer is not None:
            self.root.after_cancel(self.binding.timer)
            self.binding.timer = None
        self.binding._pump()

    def test_unicode_spaces_and_deferred_delivery(self):
        paths = [r"C:\KKS test\café ✓.zip"]
        self.send(paths)
        self.assertEqual(self.received, [])
        self.drain()
        self.assertEqual(self.received, [paths])

    def test_multiple_files_are_rejected_as_one_empty_selection(self):
        self.send([r"C:\one.zip", r"C:\two.zip"])
        self.drain()
        self.assertEqual(self.received, [[]])

    def test_repeated_drop_and_callback_lifetime(self):
        for i in range(24):
            gc.collect()
            self.send([rf"C:\package {i}.zip"])
            self.drain()
        self.assertEqual(len(self.received), 24)
        self.assertIs(self.root._kks_drop_binding, self.binding)

    def test_rebinding_removes_old_hook_and_shutdown_is_idempotent(self):
        old = self.binding
        self.binding = enable_file_drop(self.root, self.received.append)
        self.assertTrue(old.closed)
        self.send([r"C:\next.zip"])
        self.drain()
        self.assertEqual(self.received, [[r"C:\next.zip"]])
        self.binding.close()
        self.binding.close()
        self.assertTrue(self.binding.closed)


if __name__ == "__main__":
    unittest.main()
