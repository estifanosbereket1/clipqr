import os
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GdkPixbuf, Gtk


class ImagePreviewPopup(Gtk.Window):
    def __init__(self, entry):
        """
        entry: the sqlite3.Row for an image clipboard item (entry["content"] is
        the on-disk PNG path). Shows the full image at a larger, readable size.
        """
        super().__init__(title="Image Preview")
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)

        outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        outer_box.set_border_width(16)
        self.add(outer_box)

        path = entry["content"]
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            path, width=600, height=600, preserve_aspect_ratio=True
        )
        image = Gtk.Image.new_from_pixbuf(pixbuf)
        outer_box.pack_start(image, True, True, 0)

        name_label = Gtk.Label(label=os.path.basename(path))
        name_label.get_style_context().add_class("dim-label")
        outer_box.pack_start(name_label, False, False, 0)

        close_btn = Gtk.Button(label="Close")
        close_btn.connect("clicked", lambda _btn: self.destroy())
        outer_box.pack_end(close_btn, False, False, 0)

        self.show_all()
