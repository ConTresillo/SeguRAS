import tkinter as tk
from tkinter import simpledialog, colorchooser
from abc import ABC, abstractmethod
import random, re

# ---------- Name allocation ----------
class NameAllocator:
    pools = {}

    @classmethod
    def next_name(cls, type_name: str) -> str:
        pool = cls.pools.setdefault(type_name, {"next": 1, "free": set()})
        if pool["free"]:
            n = min(pool["free"])
            pool["free"].remove(n)
        else:
            n = pool["next"]
            pool["next"] += 1
        return f"{type_name}{n}"

    @classmethod
    def release_name(cls, type_name: str, name: str):
        m = re.fullmatch(rf"{re.escape(type_name)}(\d+)", name)
        if not m:
            return
        n = int(m.group(1))
        pool = cls.pools.setdefault(type_name, {"next": 1, "free": set()})
        if n < pool["next"] or n not in pool["free"]:
            pool["free"].add(n)


# ---------- Abstract base ----------
class ClickableObject(ABC):
    instances = []

    def __init__(self, app, x, y, name=None, color=None):
        if type(self) is ClickableObject:
            raise TypeError("ClickableObject is abstract and cannot be instantiated directly")

        self.app = app
        self.canvas = app.canvas
        self.layer_listbox = app.layer_listbox

        cls_name = self.__class__.__name__
        self.name = name or NameAllocator.next_name(cls_name)
        self.color = color or "#%06x" % random.randint(0, 0xFFFFFF)

        self.shape_id = None
        self.label_id = None

        self.create_shape(x, y)
        self._create_or_update_label()

        ClickableObject.instances.append(self)
        self.layer_listbox.insert(tk.END, self.name)

        for obj_id in (self.shape_id, self.label_id):
            self.canvas.tag_bind(obj_id, "<Button-3>", self.show_menu)
            self.canvas.tag_bind(obj_id, "<Button-1>", self.on_select)
            self.canvas.tag_bind(obj_id, "<B1-Motion>", self.do_drag)

        self._drag_data = {"x": 0, "y": 0}

    @abstractmethod
    def create_shape(self, x, y):
        pass

    # ------- helpers -------
    def _center_of_shape(self):
        x1, y1, x2, y2 = self.canvas.bbox(self.shape_id)
        return (x1 + x2) / 2, (y1 + y2) / 2

    def _create_or_update_label(self):
        cx, cy = self._center_of_shape()
        if self.label_id is None:
            self.label_id = self.canvas.create_text(cx, cy, text=self.name)
        else:
            self.canvas.coords(self.label_id, cx, cy)
            self.canvas.itemconfig(self.label_id, text=self.name)

    def _current_index(self):
        return ClickableObject.instances.index(self)

    # ------- context menu -------
    def show_menu(self, event):
        menu = tk.Menu(self.canvas, tearoff=0)
        actions = {
            "Recolor": self.recolor,
            "Rename": self.rename,
            "Duplicate": lambda: self.duplicate(event.x + 20, event.y + 20),
            "Delete": self.delete
        }
        for label, action in actions.items():
            menu.add_command(label=label, command=action)
        menu.post(event.x_root, event.y_root)

    def recolor(self):
        color = colorchooser.askcolor(title="Choose new color", initialcolor=self.color)
        if color and color[1]:
            self.color = color[1]
            self.canvas.itemconfig(self.shape_id, fill=self.color)

    def rename(self):
        old_name = self.name
        new_name = simpledialog.askstring("Rename", f"Enter new name for {self.name}:", initialvalue=self.name)
        if not new_name or new_name == old_name:
            return
        NameAllocator.release_name(self.__class__.__name__, old_name)
        self.name = new_name
        self._create_or_update_label()
        idx = self._current_index()
        self.layer_listbox.delete(idx)
        self.layer_listbox.insert(idx, self.name)

    def duplicate(self, x, y):
        new_obj = self.__class__(self.app, x, y, color=self.color)
        new_obj._create_or_update_label()

    def delete(self):
        self.canvas.delete(self.shape_id)
        self.canvas.delete(self.label_id)
        NameAllocator.release_name(self.__class__.__name__, self.name)
        if self in ClickableObject.instances:
            idx = self._current_index()
            ClickableObject.instances.remove(self)
            self.layer_listbox.delete(idx)

    # --- Selection + Dragging ---
    def on_select(self, event):
        for obj in ClickableObject.instances:
            self.canvas.itemconfig(obj.shape_id, width=1)
        self.canvas.itemconfig(self.shape_id, width=3)
        idx = self._current_index()
        self.layer_listbox.selection_clear(0, tk.END)
        self.layer_listbox.selection_set(idx)
        self.layer_listbox.activate(idx)
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def do_drag(self, event):
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        self.canvas.move(self.shape_id, dx, dy)
        self.canvas.move(self.label_id, dx, dy)
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y


# ---------- Concrete shapes ----------
class Bag(ClickableObject):
    def create_shape(self, x, y):
        self.shape_id = self.canvas.create_rectangle(x, y, x + 80, y + 80, fill=self.color)

class Item(ClickableObject):
    def create_shape(self, x, y):
        self.shape_id = self.canvas.create_rectangle(x, y, x + 40, y + 40, fill=self.color)

class Tag(ClickableObject):
    def create_shape(self, x, y):
        r = 20
        self.shape_id = self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=self.color)

class Scanner(ClickableObject):
    def create_shape(self, x, y):
        self.shape_id = self.canvas.create_rectangle(x, y, x + 100, y + 40, fill=self.color)


# ---------- Menu ----------
class MenuManager:
    def __init__(self, app):
        self.app = app
        self.object_classes = {
            "Bag": Bag,
            "Item": Item,
            "Tag": Tag,
            "Scanner": Scanner
        }
        self._build()

    def _build(self):
        menubar = tk.Menu(self.app.root)
        add_menu = tk.Menu(menubar, tearoff=0)
        for obj_name, cls in self.object_classes.items():
            add_menu.add_command(
                label=obj_name,
                command=lambda c=cls: c(self.app, 50, 50)
            )
        menubar.add_cascade(label="Add", menu=add_menu)
        self.app.root.config(menu=menubar)


# ---------- App ----------
class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Scalable Objects GUI with Layer Manager")

        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(main_frame, width=700, height=500, bg="white")
        self.canvas.pack(side="left", fill="both", expand=True)

        layer_frame = tk.Frame(main_frame, width=180)
        layer_frame.pack(side="right", fill="y")

        tk.Label(layer_frame, text="Layers", font=("Arial", 12, "bold")).pack()
        self.layer_listbox = tk.Listbox(layer_frame)
        self.layer_listbox.pack(fill="both", expand=True, padx=5, pady=5)

        MenuManager(self)

        self.layer_listbox.bind("<<ListboxSelect>>", self.on_layer_select)
        self.canvas.bind("<Button-1>", self.unfocus, add="+")

    def on_layer_select(self, event):
        selection = self.layer_listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        if 0 <= idx < len(ClickableObject.instances):
            obj = ClickableObject.instances[idx]
            for o in ClickableObject.instances:
                self.canvas.itemconfig(o.shape_id, width=1)
            self.canvas.itemconfig(obj.shape_id, width=3)
            obj._create_or_update_label()

    def unfocus(self, event):
        clicked = self.canvas.find_withtag("current")
        if not clicked:
            self.layer_listbox.selection_clear(0, tk.END)
            for obj in ClickableObject.instances:
                self.canvas.itemconfig(obj.shape_id, width=1)

    def run(self):
        self.root.mainloop()


# ---------- Run ----------
if __name__ == "__main__":
    App().run()
