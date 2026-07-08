import threading

import pyperclip

WIPE_DELAY_SECONDS = 30


def schedule_wipe(expected_content: str, delay: float = WIPE_DELAY_SECONDS):
    """
    Schedules the system clipboard to be cleared after `delay` seconds,
    but only if it still contains exactly `expected_content` at that time --
    so we don't accidentally wipe something the user copied in the meantime.
    """

    def wipe():
        current = pyperclip.paste()
        if current == expected_content:
            pyperclip.copy("")

    timer = threading.Timer(delay, wipe)
    timer.daemon = True
    timer.start()
    return timer
