import threading

import pyperclip

from image_clipboard import get_clipboard_image_bytes, safe_paste_text

WIPE_DELAY_SECONDS = 30


def schedule_wipe(expected_content: str, delay: float = WIPE_DELAY_SECONDS):
    """
    Schedules the system clipboard to be cleared after `delay` seconds,
    but only if it still contains exactly `expected_content` at that time --
    so we don't accidentally wipe something the user copied in the meantime.
    """

    def wipe():
        current = safe_paste_text()
        if current == expected_content:
            pyperclip.copy("")

    timer = threading.Timer(delay, wipe)
    timer.daemon = True
    timer.start()
    return timer


def schedule_image_wipe(expected_bytes: bytes, delay: float = WIPE_DELAY_SECONDS):
    """
    Same as schedule_wipe, but for image entries: the clipboard holds real
    image/png bytes (via image_clipboard.set_clipboard_image), not text, so
    the "still unchanged" check has to compare against clipboard image bytes
    instead of pyperclip.paste().
    """

    def wipe():
        current = get_clipboard_image_bytes()
        if current == expected_bytes:
            pyperclip.copy("")

    timer = threading.Timer(delay, wipe)
    timer.daemon = True
    timer.start()
    return timer
