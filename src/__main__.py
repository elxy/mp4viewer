#!/usr/bin/env python3

import argparse
import os
import sys

from datasource import DataBuffer
from datasource import FileSource
from tree import Tree


def getboxlist(buf, parent=None, debug=False):
    from isobmff.box import Box
    boxes = []
    try:
        while buf.hasmore():
            box = Box.getnextbox(buf, parent, debug)
            boxes.append(box)
    except:
        import traceback
        print(traceback.format_exc())
    return boxes


def get_box_node(box, args):
    from isobmff.box import Box, Field
    node = Tree(box.boxtype, Box.getboxdesc(box.boxtype))
    for field in box.generate_fields():
        if isinstance(field, Box):
            add_box(node, field, args)
            continue
        elif not isinstance(field, Field):
            raise Exception("Expected a Field, got a %s" % type(field))
        node.add_attr(field.name, field.get_display_value())
    return node


def add_box(parent, box, args):
    box_node = parent.add_child(get_box_node(box, args))
    for child in box.children:
        add_box(box_node, child, args)
    return box_node


def get_tree_from_file(path, args):
    with open(path, 'rb') as fd:
        boxes = getboxlist(DataBuffer(FileSource(fd)), debug=args.debug)
    root = Tree(os.path.basename(path), "File")
    for box in boxes:
        add_box(root, box, args)
    return root


def main() -> None:
    parser = argparse.ArgumentParser(description='Process iso-bmff file and list the boxes and their contents')
    parser.add_argument('--debug', action='store_true', dest='debug', help='enable debug information')
    parser.add_argument('-o', choices=['stdout', 'gui'], default='gui', help='output format', dest='output_format')
    parser.add_argument('-e',
                        '--expand-arrays',
                        action='store_false',
                        help='do not truncate long arrays',
                        dest='truncate')
    parser.add_argument('-c',
                        '--color',
                        choices=['on', 'off'],
                        default='on',
                        dest='color',
                        help='turn on/off colors in console based output; on by default')
    parser.add_argument('file', metavar='iso-base-media-file', help='Path to iso media file')
    args, _ = parser.parse_known_args()

    if args.output_format == 'gui':
        from PySide6 import QtWidgets
        from gui import View

        app = QtWidgets.QApplication(sys.argv)
        main_win = View(args.debug)
        if args.file:
            main_win.open_file(args.file)
        main_win.show()
        sys.exit(app.exec())
    else:
        from console import ConsoleRenderer

        root = get_tree_from_file(args.file, args)
        renderer = ConsoleRenderer('  ')
        if args.color == 'off':
            renderer.disable_colors()
        renderer.render(root)


if __name__ == "__main__":
    main()
