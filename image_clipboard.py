import subprocess
import os

import pyperclip

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")


def safe_paste_text() -> str | None:
    """
    pyperclip.paste() assumes clipboard content is valid UTF-8 text. Once
    anything binary is on the clipboard (an image copied via this app or any
    other), it raises UnicodeDecodeError instead of pyperclip.PyperclipException,
    so callers that might run right after an image copy need this guard.
    """
    try:
        return pyperclip.paste()
    except UnicodeDecodeError:
        return None


def get_clipboard_image_bytes() -> bytes | None:
    """
    Returns raw image bytes currently on the clipboard, checking direct
    image data first, then a file reference to an image. Does one cheap
    'list types' call first to avoid spawning multiple subprocesses when
    there's clearly nothing image-related on the clipboard.
    """
    available_types = _get_clipboard_types()
    if available_types is None:
        return None

    if "image/png" in available_types:
        return _fetch_clipboard_data("image/png")

    if "text/uri-list" in available_types:
        return _get_image_bytes_from_uri_list()

    return None



def set_clipboard_image(path: str) -> bool:
    """
    Puts the PNG at `path` onto the system clipboard as real image/png data
    (not a text path), via xclip -- consistent with the rest of this module,
    so it doesn't reintroduce the wl-paste dock-jitter bug.
    """
    try:
        result = subprocess.run(
            ["xclip", "-selection", "clipboard", "-t", "image/png", "-i", path],
            capture_output=True,
            timeout=3,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _get_clipboard_types() -> set | None:
    try:
        result = subprocess.run(
            ["xclip", "-selection", "clipboard", "-o", "-t", "TARGETS"],
            capture_output=True,
            timeout=3,
        )
        if result.returncode != 0:
            return None
        return set(result.stdout.decode("utf-8", errors="ignore").splitlines())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _fetch_clipboard_data(mime_type: str) -> bytes | None:
    try:
        result = subprocess.run(
            ["xclip", "-selection", "clipboard", "-o", "-t", mime_type],
            capture_output=True,
            timeout=3,
        )
        if result.returncode != 0 or not result.stdout:
            return None
        return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _get_image_bytes_from_uri_list() -> bytes | None:
    uri_bytes = _fetch_clipboard_data("text/uri-list")
    if uri_bytes is None:
        return None

    uri_list = uri_bytes.decode("utf-8", errors="ignore").strip()
    for line in uri_list.splitlines():
        line = line.strip()
        if not line.startswith("file://"):
            continue
        path = line[len("file://"):]
        if path.lower().endswith(IMAGE_EXTENSIONS) and os.path.isfile(path):
            with open(path, "rb") as f:
                return f.read()
    return None
