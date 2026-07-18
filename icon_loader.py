import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf

import os

ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons")



def load_icon(name: str, size: int = 18) -> Gtk.Image:

    path = f"{ICON_DIR}/{name}.svg"
    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, size, True)
        return Gtk.Image.new_from_pixbuf(pixbuf)
    except Exception as e:
        print(f"Failed to load icon '{name}': {e}")
        return Gtk.Image.new_from_icon_name("image-missing", Gtk.IconSize.BUTTON)


def load_thumbnail(path: str, size: int = 32) -> Gtk.Image:
    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, size, True)
        return Gtk.Image.new_from_pixbuf(pixbuf)
    except Exception as e:
        print(f"Failed to load thumbnail '{path}': {e}")
        return Gtk.Image.new_from_icon_name("image-missing", Gtk.IconSize.DND)
