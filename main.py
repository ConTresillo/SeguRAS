from PyQt6.QtWidgets import QApplication, QMainWindow, QGraphicsScene, QGraphicsView, QGraphicsItem, \
    QMenuBar, QInputDialog, QColorDialog, QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtGui import QBrush, QColor, QPainter
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QCursor
import sys

# ------------------- Base Class -------------------
class ClickableObject(QGraphicsItem):
    """Base class for all clickable objects with scalable naming and number tracking."""

    def __init__(self, w=50, h=50, color=QColor("gray"), name=None):
        super().__init__()
        self.rect = QRectF(0, 0, w, h)
        self.color = color

        cls = type(self)
        # initialize used_numbers set for the subclass if missing
        if not hasattr(cls, "used_numbers"):
            cls.used_numbers = set()

        # assign smallest available number
        num = 1
        while num in cls.used_numbers:
            num += 1
        cls.used_numbers.add(num)
        self.number = num

        # default name
        self.name = name or f"{cls.__name__}{self.number}"

        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
                      QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)

    def boundingRect(self):
        return self.rect

    def paint(self, painter, option, widget):
        """Subclasses must override paint()"""
        raise NotImplementedError("Subclasses must override paint()")

    # ---------------- Context menu ----------------
    def contextMenuEvent(self, event):
        # Correct
        menu = QMenu()  # ✅ a QMenu, not a QMenuBar
        rename_action = menu.addAction("Rename")
        recolor_action = menu.addAction("Recolor")
        duplicate_action = menu.addAction("Duplicate")
        delete_action = menu.addAction("Delete")

        action = menu.exec(event.screenPos())
        if action == rename_action:
            self.rename()
        elif action == recolor_action:
            self.recolor()
        elif action == duplicate_action:
            self.duplicate()
        elif action == delete_action:
            self.delete()

    # ---------------- Helper Methods ----------------
    def rename(self):
        view = self.scene().views()[0]
        text, ok = QInputDialog.getText(view, "Rename Object", "Enter new name:")
        if ok:
            self.name = text
            self.update()

    def recolor(self):
        view = self.scene().views()[0]
        color = QColorDialog.getColor(initial=self.color, parent=view)
        if color.isValid():
            self.color = color
            self.update()

    def duplicate(self):
        cls = type(self)
        copy = cls()
        copy.setPos(self.pos() + QPointF(20, 20))
        self.scene().addItem(copy)

    def delete(self):
        cls = type(self)
        # recycle the number
        if hasattr(self, "number") and self.number in cls.used_numbers:
            cls.used_numbers.remove(self.number)
        self.scene().removeItem(self)

# ------------------- Subclasses -------------------
class Bag(ClickableObject):
    def __init__(self):
        super().__init__(80, 80, QColor("blue"))

    def paint(self, painter, option, widget):
        painter.setBrush(QBrush(self.color))
        painter.drawRect(self.rect)
        painter.setPen(Qt.GlobalColor.black)
        painter.drawText(self.rect, Qt.AlignmentFlag.AlignCenter, self.name)

class Item(ClickableObject):
    def __init__(self):
        super().__init__(60, 60, QColor("red"))

    def paint(self, painter, option, widget):
        painter.setBrush(QBrush(self.color))
        painter.drawRect(self.rect)
        painter.setPen(Qt.GlobalColor.black)
        painter.drawText(self.rect, Qt.AlignmentFlag.AlignCenter, self.name)

class RFIDTag(ClickableObject):
    def __init__(self):
        super().__init__(40, 40, QColor("green"))

    def paint(self, painter, option, widget):
        painter.setBrush(QBrush(self.color))
        painter.drawEllipse(self.rect)
        painter.setPen(Qt.GlobalColor.black)
        painter.drawText(self.rect, Qt.AlignmentFlag.AlignCenter, self.name)

class RFIDScanner(ClickableObject):
    def __init__(self):
        super().__init__(100, 50, QColor("orange"))

    def paint(self, painter, option, widget):
        painter.setBrush(QBrush(self.color))
        painter.drawRect(self.rect)
        painter.setPen(Qt.GlobalColor.black)
        painter.drawText(self.rect, Qt.AlignmentFlag.AlignCenter, self.name)

# ------------------- Main Window -------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RFID System GUI")

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.setCentralWidget(self.view)

        self.current_type = None
        self.ghost_item = None

        # Menu
        menu_bar = self.menuBar()
        obj_menu = menu_bar.addMenu("Add Object")
        for name, cls in [("Bag", Bag), ("Item", Item), ("RFID Tag", RFIDTag), ("RFID Scanner", RFIDScanner)]:
            action = QAction(name, self)
            action.triggered.connect(lambda checked, c=cls: self.select_type(c))
            obj_menu.addAction(action)

        # Mouse tracking
        self.view.setMouseTracking(True)
        self.view.viewport().installEventFilter(self)

    # ---------------- Object selection ----------------
    def select_type(self, cls):
        self.current_type = cls
        if self.ghost_item:
            self.scene.removeItem(self.ghost_item)
        pos = self.view.mapToScene(self.view.mapFromGlobal(QCursor.pos()))
        self.ghost_item = cls()
        self.ghost_item.setPos(pos - QPointF(self.ghost_item.rect.width()/2,
                                             self.ghost_item.rect.height()/2))
        self.ghost_item.setOpacity(0.5)
        self.scene.addItem(self.ghost_item)

    # ---------------- Event Filter ----------------
    def eventFilter(self, source, event):
        if self.ghost_item and event.type() == event.Type.MouseMove:
            pos = self.view.mapToScene(event.position().toPoint())
            self.ghost_item.setPos(pos - QPointF(self.ghost_item.rect.width()/2,
                                                 self.ghost_item.rect.height()/2))
        elif self.ghost_item and event.type() == event.Type.MouseButtonPress:
            # Confirm placement
            self.ghost_item.setOpacity(1.0)
            self.ghost_item = None
            self.current_type = None
        return super().eventFilter(source, event)

# ------------------- Run -------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())
