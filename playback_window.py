import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from settings_store import load_settings
from storage import get_recent_unpinned
from timeline_widget import TimelineWidget


class PlaybackWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Clipboard Playback")
        self.set_default_size(500, 320)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.entries = list(get_recent_unpinned(limit=200))
        self.entries.reverse()  # oldest first

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        outer.set_border_width(16)
        self.add(outer)

        self.timestamp_label = Gtk.Label(label="")
        outer.pack_start(self.timestamp_label, False, False, 0)

        self.content_label = Gtk.Label(label="")
        self.content_label.set_line_wrap(True)
        self.content_label.set_selectable(True)
        self.content_label.set_xalign(0)
        self.content_label.set_yalign(0)

        content_scroll = Gtk.ScrolledWindow()
        content_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        content_scroll.set_min_content_height(150)
        content_scroll.set_max_content_height(150)
        content_scroll.add(self.content_label)
        outer.pack_start(content_scroll, True, True, 0)

        if not self.entries:
            self.content_label.set_text("No history to play back yet.")
            self.show_all()
            return

        playback_mode = load_settings().get("playback_mode", "time")

        if playback_mode == "time":
            self.timeline = TimelineWidget(self.entries, on_select=self._show_entry)
            outer.pack_start(self.timeline, False, False, 0)
        else:
            adjustment = Gtk.Adjustment(
                value=0, lower=0, upper=len(self.entries) - 1, step_increment=1
            )
            scale = Gtk.Scale(
                orientation=Gtk.Orientation.HORIZONTAL, adjustment=adjustment
            )
            scale.set_digits(0)
            scale.connect(
                "value-changed", lambda s: self._show_entry(int(s.get_value()))
            )
            outer.pack_start(scale, False, False, 0)

        self._show_entry(0)
        self.show_all()

    def _show_entry(self, index):
        entry = self.entries[index]
        self.timestamp_label.set_text(
            f"{entry['created_at']}  ({index + 1}/{len(self.entries)})"
        )
        self.content_label.set_text(entry["content"])


def _standalone_test():
    win = PlaybackWindow()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()


if __name__ == "__main__":
    _standalone_test()
