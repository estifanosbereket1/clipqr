import subprocess


def get_clipboard_image_bytes() -> bytes | None:
    """
    Returns the raw PNG bytes currently on the clipboard, or None if
    there's no image data. Uses wl-paste directly since GTK's own
    clipboard API has been unreliable for image data on some GNOME/Wayland
    setups.
    """
    try:
        result = subprocess.run(
            ["wl-paste", "--type", "image/png"],
            capture_output=True,
            timeout=3,
        )
        if result.returncode != 0 or not result.stdout:
            return None
        return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def save_image_bytes_to_file(image_bytes: bytes, path: str):
    with open(path, "wb") as f:
        f.write(image_bytes)


def _standalone_test():
    import time
    print("Copy an image (Super+Shift+S to screenshot an area), you have 5 seconds...")
    time.sleep(5)

    image_bytes = get_clipboard_image_bytes()
    if image_bytes is None:
        print("No image found on clipboard.")
        return

    print(f"Found image: {len(image_bytes)} bytes")
    save_image_bytes_to_file(image_bytes, "/tmp/clipvault_image_test.png")
    print("Saved to /tmp/clipvault_image_test.png")


if __name__ == "__main__":
    _standalone_test()
