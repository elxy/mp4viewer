import enum

import xml.etree.ElementTree as ET
from io import StringIO
from typing import Dict, Callable, Optional, Union

from PySide6 import QtCore, QtGui, QtWidgets

from datasource import DataBuffer, FileSource, Position
from isobmff.box import Box, Field


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
    # User refreshes the view
    REFRESH = enum.auto()
    # User selects item from box tree
    BOX_SELECTED = enum.auto()
    # User selects attribute from attributes table
    ATTR_SELECTED = enum.auto()


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
        return QtCore.QSize(self.doc.idealWidth(), self.doc.size().height())


class AttrItem(QtWidgets.QTableWidgetItem):

    def __init__(self, field: Field, is_name: bool) -> None:
        self.field = field
        self.is_name = is_name

        string = field.name if is_name else field.get_display_value()
        super().__init__(string)
        self.setToolTip(string)
        self.setFlags(self.flags() ^ QtGui.Qt.ItemIsEditable)


class AttrView(QtWidgets.QTableWidget):

    def __init__(self, callbacks: Dict[Events, Callable[..., None]], **kargs) -> None:
        super().__init__(**kargs)

        self.callbacks = callbacks

        self.setColumnCount(2)
        self.setRowCount(0)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setHorizontalHeaderLabels(("Field", "Value"))
        self.verticalHeader().hide()
        header = self.horizontalHeader()
        header.setMinimumSectionSize(160)
        self.setMinimumWidth(self.columnCount() * header.minimumSectionSize())
        self.setHorizontalScrollBarPolicy(QtGui.Qt.ScrollBarAlwaysOff)

        self.itemSelectionChanged.connect(self.on_attr_selected)

        self.resized = False

    def on_attr_selected(self) -> None:
        selected = self.selectedItems()
        self.callbacks[Events.ATTR_SELECTED](selected)

    def refresh(self) -> None:
        header = self.horizontalHeader()
        header.resizeSections(QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)

    def show_attrs(self, box: Box, truncate=False) -> None:
        for field in box.generate_fields():
            if isinstance(field, Box):
                continue
            elif not isinstance(field, Field):
                raise Exception("Expected a Field, got a %s" % type(field))
            name_item = AttrItem(field, is_name=True)
            value_item = AttrItem(field, is_name=False)
            row = self.rowCount()
            self.insertRow(row)
            self.setItem(row, 0, name_item)
            self.setItem(row, 1, value_item)


class BoxItem(QtWidgets.QTreeWidgetItem, Position):

    def __init__(self, box: Box) -> None:
        QtWidgets.QTreeWidgetItem.__init__(self, [self.format_box_title(box)])
        Position.__init__(self)

        self.box = box
        self.pos = box.buffer_offset
        self.len = box.size

    def format_box_title(self, box: Box) -> str:
        root = ET.Element('span')
        child = ET.SubElement(root, 'span', {'style': 'color:red'})
        child.text = box.boxtype
        child = ET.SubElement(root, 'span', {'style': 'color:black'})
        child.text = ": %s" % (Box.getboxdesc(box.boxtype))
        return ET.tostring(root, encoding="unicode")


class TreeView(QtWidgets.QTreeWidget):

    def __init__(self, callbacks: Dict[Events, Callable[..., None]], **kargs) -> None:
        super().__init__(**kargs)

        self.callbacks = callbacks

        self.setColumnCount(1)
        self.setHeaderHidden(True)
        delegate = HTMLDelegate()
        self.setItemDelegate(delegate)
        self.setMinimumWidth(320)
        self.setMaximumWidth(480)

        self.itemSelectionChanged.connect(self.on_box_selected)

    def on_box_selected(self) -> None:
        selected = self.selectedItems()[0]
        self.callbacks[Events.BOX_SELECTED](selected)

    def populate(self, box: Box, parent: Optional[BoxItem] = None) -> BoxItem:
        item = BoxItem(box)
        for sub_box in box.children:
            self.populate(sub_box, item)
        if parent:
            parent.addChild(item)
        return item

    def show_boxes(self, boxes: list[Box]) -> None:
        items = []
        for box in boxes:
            item = self.populate(box)
            items.append(item)

        self.insertTopLevelItems(0, items)
        self.setCurrentItem(items[0])

        self.expandAll()
        self.resizeColumnToContents(0)


class HexArea(QtWidgets.QWidget):

    def __init__(self, callbacks: Dict[Events, Callable[..., None]], **kargs) -> None:
        super().__init__(**kargs)
        # self._layout = QtWidgets.QHBoxLayout(parent=parent)

        # self._offset_area = QtWidgets.QTextEdit(parent=parent)
        self._hex_area = QtWidgets.QTextEdit(self)
        self._hex_area.setReadOnly(True)
        self._hex_area.setHorizontalScrollBarPolicy(QtGui.Qt.ScrollBarAlwaysOff)
        self._hex_area.setVerticalScrollBarPolicy(QtGui.Qt.ScrollBarAlwaysOn)
        # self._ascii_area = QtWidgets.QTextEdit(parent=parent)
        # self._scroll_bar = QtWidgets.QScrollBar(parent=parent)

        # self.text_areas = [self._offset_area, self._hex_area, self._ascii_area]
        # for text_area in self.text_areas:
            # text_area.setReadOnly(True)

        # self._scroll_bar.sliderMoved.connect(self.on_scroll_bar)

    # def on_scroll_bar(self, value: int) -> None:
    def open_file(self, file_name: str) -> None:
        self.file = open(file_name, 'rb')
        data = self.file.read()




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
            Events.REFRESH: self.cb_refresh,
            Events.BOX_SELECTED: self.cb_box_selected,
            Events.ATTR_SELECTED: self.cb_attr_selected,
        }

        self._tree_view = TreeView(callbacks=callbacks)
        self._attr_view = AttrView(callbacks=callbacks)
        self._hex_area = HexArea(callbacks=callbacks)

        self._tree_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal, self)
        self._tree_splitter.setChildrenCollapsible(False)
        self._tree_splitter.addWidget(self._tree_view)

        self._attr_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical, self._tree_splitter)
        self._attr_splitter.setChildrenCollapsible(False)
        self._attr_splitter.addWidget(self._attr_view)
        self._attr_splitter.addWidget(self._hex_area)

        self._tree_splitter.addWidget(self._attr_splitter)
        self.setCentralWidget(self._tree_splitter)

        self.create_actions()

        self.read_settings()

        self.setStyleSheet(View.STYLE_SHEET)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        QtWidgets.QMainWindow.showEvent(self, event)
        self.cb_refresh()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.write_settings()
        event.accept()

    def open(self) -> None:
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(self)
        if file_name:
            self.open_file(file_name)

    def create_actions(self) -> None:
        self._open_act = QtGui.QAction('&Open', self, shortcut=QtGui.QKeySequence.Open, triggered=self.open)
        self._exit_act = QtGui.QAction('&Quit', self, shortcut=QtGui.QKeySequence.Quit, triggered=self.close)
        self._exit_act.setVisible(False)

        menu_bar = self.menuBar()

        menu_bar.addAction(self._open_act)
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
        self._tree_view.show_boxes(boxes)
        self._cur_file = file_name
        self.setWindowTitle(self._cur_file)

    def cb_refresh(self) -> None:
        self._attr_view.refresh()

    def cb_box_selected(self, item: BoxItem) -> None:
        self._attr_view.setRowCount(0)
        self._attr_view.show_attrs(item.box)

        pos, len = item.get_position()
        message = f'Position: {pos:d} (0x{pos:x}) | Length: {len:d} (0x{len:x}) bytes'
        self.statusBar().showMessage(message)

    def cb_attr_selected(self, items: list[AttrItem]) -> None:
        if not items:
            return

        item = items[0]
        pos, len = item.field.get_position()
        message = f'Position: {pos:d} (0x{pos:x}) | Length: {len:d} (0x{len:x}) bytes'
        self.statusBar().showMessage(message)
