import os
import sys

try:
    import winreg
    _WINREG_AVAILABLE = True
except ImportError:
    _WINREG_AVAILABLE = False

APP_NAME = "AITranscription"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _build_command() -> str:
    # Use pythonw.exe to hide console on startup
    exe = sys.executable
    if exe.endswith("python.exe"):
        exe = exe[:-10] + "pythonw.exe"
    script = os.path.abspath("main.py")
    return f'"{exe}" "{script}"'


def enable() -> None:
    if not _WINREG_AVAILABLE:
        return
    value = _build_command()
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, value)
    winreg.CloseKey(key)


def disable() -> None:
    if not _WINREG_AVAILABLE:
        return
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
    try:
        winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass
    winreg.CloseKey(key)


def is_enabled() -> bool:
    if not _WINREG_AVAILABLE:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
