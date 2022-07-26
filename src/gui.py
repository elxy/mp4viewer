import enum

import xml.etree.ElementTree as ET
from typing import Dict, Callable, Optional, Union

from PySide6 import QtCore, QtGui, QtWidgets

from datasource import DataBuffer, FileSource
from isobmff.box import Box


def get_boxes_from_file(path: str, debug: bool = False) -> list[Box]:
    with open(path, 'rb') as fd:
        buf = DataBuffer(FileSource(fd))
        from isobmff.box import Box
        boxes = []
        while buf.hasmore():
            box = Box.getnextbox(buf, None, debug)
            boxes.append(box)
        return boxes


class Events(enum.Enum):
    # User selects item from box tree
    BOX_SELECTED = enum.auto()


class HTMLDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        # probably better not to create new QTextDocuments every ms
        self.doc = QtGui.QTextDocument()

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
    ) -> None:
        options = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        painter.save()
        self.doc.setTextWidth(options.rect.width())
        self.doc.setHtml(options.text)
        self.doc.setDefaultFont(options.font)
        options.text = ''
        options.widget.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem, options, painter)
        painter.translate(options.rect.left(), options.rect.top())
        clip = QtCore.QRectF(0, 0, options.rect.width(), options.rect.height())
        painter.setClipRect(clip)
        ctx = QtGui.QAbstractTextDocumentLayout.PaintContext()
        ctx.clip = clip
        self.doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def sizeHint(
        self,
        option: QtWidgets.QStyleOptionViewItem,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
    ) -> QtCore.QSize:
        self.initStyleOption(option, index)
        self.doc.setHtml(option.text)
        self.doc.setTextWidth(option.rect.width())
        return QtCore.QSize(self.doc.idealWidth(), self.doc.size().height())


class BoxItem(QtWidgets.QTreeWidgetItem):

    def set_box(self, box: Box) -> None:
        self.box = box

    def get_box(self) -> Box:
        return self.box


class TreeView(QtWidgets.QTreeWidget):

    def __init__(self, callbacks: Dict[Events, Callable[..., None]]) -> None:
        super().__init__()

        self.callbacks = callbacks

        self.setColumnCount(1)
        self.setHeaderHidden(True)

        self.itemSelectionChanged.connect(self.on_box_selected)

    def on_box_selected(self) -> None:
        selected = self.selectedItems()[0]
        self.callbacks[Events.BOX_SELECTED](selected.get_box())

    def format_box_title(self, box: Box) -> str:
        root = ET.Element('span')
        child = ET.SubElement(root, 'span', {'style': 'color:red'})
        child.text = box.boxtype
        child = ET.SubElement(root, 'span', {'style': 'color:black'})
        child.text = ": %s" % (Box.getboxdesc(box.boxtype))
        return ET.tostring(root, encoding="unicode")

    def populate(self, box: Box, parent: Optional[BoxItem] = None) -> BoxItem:
        box_title = self.format_box_title(box)
        item = BoxItem([box_title])
        item.set_box(box)
        for sub_box in box.children:
            self.populate(sub_box, item)
        if parent:
            parent.addChild(item)
        return item

    def render(self, boxes: list[Box]) -> None:
        items = []
        for box in boxes:
            item = self.populate(box)
            items.append(item)

        self.insertTopLevelItems(0, items)
        delegate = HTMLDelegate()
        self.setItemDelegate(delegate)


class View(QtWidgets.QMainWindow):
    STYLE_SHEET = \
'''
QWidget {
    font: normal 16px;
    font-family: "Monospace"
}
'''

    def __init__(self, debug: bool = False) -> None:
        super().__init__()

        self._cur_file = ''
        self._debug = debug

        callbacks = {
            Events.BOX_SELECTED: self.cb_box_selected,
        }

        self._tree_view = TreeView(callbacks=callbacks)
        self.setCentralWidget(self._tree_view)

        self.create_actions()

        self.read_settings()

        self.setStyleSheet(View.STYLE_SHEET)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.write_settings()
        event.accept()

    def open(self) -> None:
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(self)
        if file_name:
            self.open_file(file_name)

    def set_font(self) -> None:
        ok, font = QtWidgets.QFontDialog.getFont(self._tree_view)
        if ok:
            self._tree_view.setFont(font)

    def create_actions(self) -> None:
        self._open_act = QtGui.QAction('&Open', self, shortcut=QtGui.QKeySequence.Open, triggered=self.open)
        self._font_act = QtGui.QAction('&Font', self, triggered=self.set_font)
        self._exit_act = QtGui.QAction('&Quit', self, shortcut=QtGui.QKeySequence.Quit, triggered=self.close)
        self._exit_act.setVisible(False)

        menu_bar = self.menuBar()

        menu_bar.addAction(self._open_act)
        menu_bar.addAction(self._font_act)
        menu_bar.addAction(self._exit_act)

    def read_settings(self) -> None:
        settings = QtCore.QSettings('mp4viewer', 'Application Example')
        geometry = settings.value('geometry', QtCore.QByteArray())
        if geometry.size():
            self.restoreGeometry(geometry)

    def write_settings(self) -> None:
        settings = QtCore.QSettings('mp4viewer', 'Application Example')
        settings.setValue('geometry', self.saveGeometry())

    def open_file(self, file_name: str) -> None:
        boxes = get_boxes_from_file(file_name, debug=self._debug)
        self._tree_view.clear()
        self._tree_view.render(boxes)
        self._cur_file = file_name
        self.setWindowTitle(self._cur_file)

    def cb_box_selected(self, box: Box) -> None:
        message = 'Position: {pos:d} (0x{pos:x}) | Length: {len:d} (0x{len:x}) bytes'.format(pos=box.buffer_offset,
                                                                                             len=box.size)
        self.statusBar().showMessage(message)
