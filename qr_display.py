import gi

from qr_popup import generate_qr_for_entry

gi.require_version("Gtk", "3.0")
from gi.repository import GdkPixbuf, Gtk


class QrPopup(Gtk.Window):
    def __init__(self, entry):
        """
        entry: the sqlite3.Row for the clipboard item (has entry["id"], entry["content"]).
        Generates the QR image and displays it immediately on construction.
        """
        super().__init__(title="Scan to copy on phone")
        self.set_default_size(320, 380)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)

        image_path = generate_qr_for_entry(entry["id"])

        outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        outer_box.set_border_width(16)
        self.add(outer_box)

        # A short label reminding the user what this QR is for
        preview = entry["content"]
        if len(preview) > 40:
            preview = preview[:40] + "..."
        info_label = Gtk.Label(label=f"Scan to copy:\n{preview}")
        info_label.set_justify(Gtk.Justification.CENTER)
        info_label.set_line_wrap(True)
        outer_box.pack_start(info_label, False, False, 0)

        # Load the saved PNG into a GTK image widget
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            image_path, width=280, height=280, preserve_aspect_ratio=True
        )
        qr_image = Gtk.Image.new_from_pixbuf(pixbuf)
        outer_box.pack_start(qr_image, True, True, 0)

        close_btn = Gtk.Button(label="Close")
        close_btn.connect("clicked", lambda _btn: self.destroy())
        outer_box.pack_end(close_btn, False, False, 0)

        self.show_all()


def _standalone_test():
    """
    Quick manual test: opens a popup for a fake/real entry without needing
    history_window.py wired up yet. Replace entry_id with one that exists in your DB.
    """
    from storage import get_entry_by_id

    entry = get_entry_by_id(4)  # change to an id you know exists
    if entry is None:
        print("No such entry, pick a valid id from your history.db")
        return

    win = QrPopup(entry)
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()


if __name__ == "__main__":
    _standalone_test()
