import time

import pyperclip

from storage import add_entry


def start_monitoring(poll_interval=1.0, on_change=None):
    last_seen = pyperclip.paste()
    while True:
        time.sleep(poll_interval)
        try:
            current_value = pyperclip.paste()
            if last_seen != current_value:
                inserted = add_entry(content=current_value)
                last_seen = current_value
                if inserted and on_change:
                    on_change()
        except pyperclip.PyperclipException as e:
            print(f"Clipboard read failed: {e}")
