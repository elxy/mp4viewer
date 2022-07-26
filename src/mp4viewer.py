#!/usr/bin/python

import argparse
import importlib.resources
import xml.etree.ElementTree as ET

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from showboxes import get_tree_from_file


class View():
    def __init__(self):
        self.builder = Gtk.Builder()
        with importlib.resources.path("assets", "mp4viewer.ui") as ui_path:
            self.builder.add_from_file(str(ui_path))

        self.window = self.builder.get_object("main_window")
        self.window.connect("delete_event", self.on_delete)
        self.window.connect("destroy", self.on_destroy)

        self.setup_menu()

        self.treestore_box = self.builder.get_object("tree_store_box")
        self.treeview_box = self.builder.get_object("tree_view_box")
        col = Gtk.TreeViewColumn()
        cell = Gtk.CellRendererText()
        col.pack_start(cell, True)
        col.add_attribute(cell, 'markup', 0)
        self.treeview_box.append_column(col)
        select = self.treeview_box.get_selection()
        select.connect("changed", self.on_box_select)
        self.box_index = {}

        self.liststore_attr = self.builder.get_object("list_store_attr")
        self.treeview_attr = self.builder.get_object("tree_view_attr")
        col = Gtk.TreeViewColumn()
        cell = Gtk.CellRendererText()
        col.pack_start(cell, True)
        col.add_attribute(cell, 'markup', 0)
        self.treeview_attr.append_column(col)
        col = Gtk.TreeViewColumn()
        cell = Gtk.CellRendererText()
        col.pack_start(cell, True)
        col.add_attribute(cell, 'markup', 1)
        self.treeview_attr.append_column(col)

    def on_delete(self, widget, event, data=None):
        return False

    def on_destroy(self, widget, data=None):
        Gtk.main_quit()

    def on_box_select(self, selection):
        _, treeiter = selection.get_selected()
        if treeiter is not None:
            path = self.treestore_box.get_path(treeiter)
            node = self.box_index[str(path)]
            self.liststore_attr.clear()
            for attr in node.attrs:
                self.liststore_attr.append(
                    [attr.name, str(attr.display_value if attr.display_value else attr.value)])

    def on_menu_open(self, widget):
        print('open is clicked')
        file_chooser = self.builder.get_object('file_chooser')
        file_chooser.show_all()

    def on_file_activated(self, file_chooser):
        file_chooser_button = self.builder.get_object('file_chooser_button')
        file_chooser_button.set_sensitive(True)

    def on_file_choosed(self, widget):
        file_chooser = self.builder.get_object('file_chooser')
        file = file_chooser.get_filename()
        print(file)
        file_chooser.hide()

    def setup_menu(self):
        menu_open = self.builder.get_object('menu_open')
        menu_open.connect("activate", self.on_menu_open)

        file_chooser = self.builder.get_object('file_chooser')
        file_chooser.connect('file-activated', self.on_file_activated)
        file_chooser_button = self.builder.get_object('file_chooser_button')
        file_chooser_button.connect('clicked', self.on_file_choosed)

    def format_node(self, name, value, istitle=False):
        root = ET.Element('markup')
        color = 'red' if istitle else 'blue'
        child = ET.SubElement(root, 'span', {'foreground': color})
        child.text = name
        child = ET.SubElement(root, 'span', {'foreground': 'black'})
        child.text = ": %s" % (value)
        return ET.tostring(root, encoding="unicode")

    def populate(self, datanode, parent=None):
        treenode = self.treestore_box.append(parent, [self.format_node(datanode.name, datanode.desc, True)])
        index = str(self.treestore_box.get_path(treenode))
        self.box_index[index] = datanode
        for child in datanode.children:
            self.populate(child, treenode)

    def render(self, data):
        self.window.set_title(data.name)

        self.treestore_box.clear()
        for child in data.children:
            self.populate(child)

        self.treeview_box.expand_all()
        self.window.show_all()


class Application():

    def __init__(self, input_file, args):
        self.view = View()
        root = get_tree_from_file(args.input_file, args)
        self.view.render(root)

    def run(self):
        Gtk.main()

def main():
    parser = argparse.ArgumentParser(description='Process iso-bmff file and list the boxes and their contents')
    parser.add_argument('--debug', action='store_true', dest='debug', help='enable debug information')
    parser.add_argument('-e',
                        '--expand-arrays',
                        action='store_false',
                        help='do not truncate long arrays',
                        dest='truncate')
    parser.add_argument('input_file', metavar='iso-base-media-file', help='Path to iso media file')
    args = parser.parse_args()

    app = Application(args.input_file, args)
    app.run()


if __name__ == "__main__":
    main()
