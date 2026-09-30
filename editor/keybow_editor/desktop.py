"""Desktop window around the local editor HTTP server."""

import sys
import threading

from . import server


def require_webview2():
    if sys.platform != "win32":
        return
    import ctypes
    import winreg

    key = r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
    installed = False
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in (0, winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY):
            try:
                with winreg.OpenKey(hive, key, 0, winreg.KEY_READ | view) as entry:
                    version = winreg.QueryValueEx(entry, "pv")[0]
                    installed = installed or bool(version and version != "0.0.0.0")
            except OSError:
                pass
    if not installed:
        message = ("Keybow Editor needs Microsoft Edge WebView2 Runtime.\n"
                   "Install it from https://developer.microsoft.com/microsoft-edge/webview2/ "+
                   "and reopen the app.")
        ctypes.windll.user32.MessageBoxW(None, message, "Keybow Editor", 0x10)
        raise SystemExit(message)


def main():
    require_webview2()
    import webview

    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    worker = threading.Thread(target=httpd.serve_forever, daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{httpd.server_port}/"
    try:
        webview.create_window("Keybow Editor", url, width=1280, height=850, min_size=(850, 600))
        # Force WebView2 on Windows: the legacy MSHTML engine cannot run this UI.
        webview.start(gui="edgechromium" if sys.platform == "win32" else None)
    except Exception as exc:
        if sys.platform == "win32":
            raise SystemExit("Keybow Editor needs Microsoft Edge WebView2 Runtime. Install it from https://developer.microsoft.com/microsoft-edge/webview2/ and reopen the app.\n" + str(exc)) from exc
        raise
    finally:
        httpd.shutdown()
        httpd.server_close()
        server.DEVICE.close()
        worker.join(timeout=3)


if __name__ == "__main__":
    main()
