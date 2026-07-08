import gi

gi.require_version("Gtk", "3.0")
from datetime import datetime

from gi.repository import Gtk


class TimelineWidget(Gtk.DrawingArea):
    def __init__(self, entries, on_select=None):
        """
        entries: list of sqlite3.Row, each with 'created_at' (oldest first)
        on_select: called with the index of the entry closest to a click
        """
        super().__init__()
        self.entries = entries
        self.on_select = on_select
        self.selected_index = 0

        self.set_size_request(-1, 80)
        self.connect("draw", self.on_draw)
        self.connect("button-press-event", self.on_click)
        self.add_events(self.get_events() | 0x100)  # GDK_BUTTON_PRESS_MASK

        self._parsed_times = [
            datetime.strptime(e["created_at"], "%Y-%m-%d %H:%M:%S") for e in entries
        ]
        if self._parsed_times:
            self._min_time = min(self._parsed_times)
            self._max_time = max(self._parsed_times)
        else:
            self._min_time = self._max_time = None

    def _time_fraction(self, index) -> float:
        """Returns 0.0-1.0 representing where this entry falls in the time range."""
        if self._min_time == self._max_time:
            return 0.5  # only one entry, or all same timestamp -- center it
        total_span = (self._max_time - self._min_time).total_seconds()
        offset = (self._parsed_times[index] - self._min_time).total_seconds()
        return offset / total_span

    def on_draw(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        mid_y = height / 2

        # baseline
        cr.set_source_rgb(0.4, 0.4, 0.4)
        cr.set_line_width(2)
        cr.move_to(10, mid_y)
        cr.line_to(width - 10, mid_y)
        cr.stroke()

        usable_width = width - 20  # 10px margin each side

        for index in range(len(self.entries)):
            fraction = self._time_fraction(index)
            x = 10 + fraction * usable_width

            if index == self.selected_index:
                cr.set_source_rgb(0.35, 0.55, 1.0)
                radius = 7
            else:
                cr.set_source_rgb(0.6, 0.6, 0.6)
                radius = 4

            cr.arc(x, mid_y, radius, 0, 2 * 3.14159)
            cr.fill()

    def on_click(self, widget, event):
        width = widget.get_allocated_width()
        usable_width = width - 20
        click_fraction = (event.x - 10) / usable_width

        # find whichever entry's fraction is closest to where the user clicked
        closest_index = 0
        closest_distance = None
        for index in range(len(self.entries)):
            fraction = self._time_fraction(index)
            distance = abs(fraction - click_fraction)
            if closest_distance is None or distance < closest_distance:
                closest_distance = distance
                closest_index = index

        self.selected_index = closest_index
        self.queue_draw()  # triggers a re-render with the new selection highlighted

        if self.on_select:
            self.on_select(closest_index)


def _standalone_test():
    from storage import get_recent_unpinned

    entries = list(get_recent_unpinned(limit=50))
    entries.reverse()

    win = Gtk.Window(title="Timeline Test")
    win.set_default_size(500, 150)

    def on_select(index):
        print(f"Selected index {index}: {entries[index]['content'][:40]!r}")

    timeline = TimelineWidget(entries, on_select=on_select)
    win.add(timeline)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    _standalone_test()
