import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
import pyperclip

from storage import add_snippet, update_snippet, delete_snippet, get_all_snippets

class SnippetsWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Named Snippets")
        self.set_default_size(420, 480)
        self.set_position(Gtk.WindowPosition.CENTER)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        outer.set_border_width(16)
        self.add(outer)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title_label = Gtk.Label(label="Snippets")
        title_label.set_xalign(0)
        title_label.set_hexpand(True)

        new_btn = Gtk.Button(label="+ New Snippet")
        new_btn.connect("clicked", self.on_new_clicked)

        header.pack_start(title_label, True, True, 0)
        header.pack_end(new_btn, False, False, 0)
        outer.pack_start(header, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        outer.pack_start(scrolled, True, True, 0)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled.add(self.list_box)

        self.refresh()
        self.show_all()

    def refresh(self):
        for child in self.list_box.get_children():
            self.list_box.remove(child)

        snippets = get_all_snippets()
        if not snippets:
            empty = Gtk.Label(label="No snippets yet. Click + New Snippet to add one.")
            empty.set_margin_top(20)
            empty.get_style_context().add_class("dim-label")
            self.list_box.add(empty)
        else:
            for snippet in snippets:
                row = self._build_row(snippet)
                self.list_box.add(row)

        self.list_box.show_all()

    def _build_row(self, snippet) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(6)
        box.set_margin_end(6)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        name_label = Gtk.Label()
        name_label.set_xalign(0)

        # CRITICAL FIX: Escape the text before using markup
        # Prevents characters like & and < from crashing the GTK renderer
        escaped_name = GLib.markup_escape_text(snippet["name"])
        name_label.set_markup(f"<b>{escaped_name}</b>")

        preview_text = snippet["content"].replace("\n", " ")
        if len(preview_text) > 60:
            preview_text = preview_text[:60].rstrip() + "..."

        preview_label = Gtk.Label(label=preview_text)
        preview_label.set_xalign(0)
        preview_label.get_style_context().add_class("dim-label")

        text_box.pack_start(name_label, False, False, 0)
        text_box.pack_start(preview_label, False, False, 0)
        text_box.set_hexpand(True)
        box.pack_start(text_box, True, True, 0)

        copy_btn = Gtk.Button(label="Copy")
        copy_btn.connect("clicked", self._make_copy_handler(snippet))
        box.pack_end(copy_btn, False, False, 0)

        edit_btn = Gtk.Button(label="Edit")
        edit_btn.connect("clicked", self._make_edit_handler(snippet))
        box.pack_end(edit_btn, False, False, 0)

        delete_btn = Gtk.Button(label="Delete")
        delete_btn.connect("clicked", self._make_delete_handler(snippet))
        box.pack_end(delete_btn, False, False, 0)

        row.add(box)
        return row

    def _make_copy_handler(self, snippet):
        def handler(_button):
            pyperclip.copy(snippet["content"])
        return handler

    def _make_edit_handler(self, snippet):
        def handler(_button):
            self._open_editor(snippet=snippet)
        return handler

    def _make_delete_handler(self, snippet):
        def handler(_button):
            confirm = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.YES_NO,
                text=f"Delete snippet '{snippet['name']}'?",
            )
            response = confirm.run()
            confirm.destroy()
            if response == Gtk.ResponseType.YES:
                delete_snippet(snippet["id"])
                self.refresh()
        return handler

    def on_new_clicked(self, _button):
        self._open_editor(snippet=None)

    def _open_editor(self, snippet):
        is_edit = snippet is not None
        dialog = Gtk.Dialog(
            title="Edit Snippet" if is_edit else "New Snippet",
            transient_for=self,
            flags=0,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK,
        )
        dialog.set_default_size(360, 300)

        content_area = dialog.get_content_area()
        content_area.set_border_width(12)
        content_area.set_spacing(8)

        # --- Name Input Section ---
        name_label = Gtk.Label(label="Name:")
        name_label.set_xalign(0)  # Align to the left
        content_area.add(name_label)

        name_entry = Gtk.Entry()
        name_entry.set_placeholder_text("e.g., Docker cleanup")
        if is_edit:
            name_entry.set_text(snippet["name"])
        content_area.add(name_entry)

        # --- Content Input Section ---
        content_label = Gtk.Label(label="Content:")
        content_label.set_xalign(0)  # Align to the left
        content_label.set_margin_top(4) # A tiny bit of breathing room
        content_area.add(content_label)

        text_scrolled = Gtk.ScrolledWindow()
        text_scrolled.set_vexpand(True)
        text_view = Gtk.TextView()
        text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        if is_edit:
            text_view.get_buffer().set_text(snippet["content"])
        text_scrolled.add(text_view)
        content_area.add(text_scrolled)

        dialog.show_all()

        # Wrap the response in a loop so we can intercept empty saves
        while True:
            response = dialog.run()

            if response == Gtk.ResponseType.OK:
                name = name_entry.get_text().strip()
                buffer = text_view.get_buffer()
                content = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False).strip()

                if not name or not content:
                    # Don't let them silently fail out of the dialog
                    error = Gtk.MessageDialog(
                        transient_for=dialog,
                        flags=0,
                        message_type=Gtk.MessageType.ERROR,
                        buttons=Gtk.ButtonsType.OK,
                        text="Name and content are required.",
                    )
                    error.run()
                    error.destroy()
                    continue

                if is_edit:
                    update_snippet(snippet["id"], name, content)
                else:
                    add_snippet(name, content)

                self.refresh()
                break
            else:
                break

        dialog.destroy()


def _standalone_test():
    win = SnippetsWindow()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()

if __name__ == "__main__":
    _standalone_test()
