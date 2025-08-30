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
    def build_base_menu(self, event):
        menu = tk.Menu(self.canvas, tearoff=0)
        actions = {
            "Recolor": self.recolor,
            "Rename": self.rename,
            "Duplicate": lambda: self.duplicate(event.x + 20, event.y + 20),
            "Delete": self.delete
        }
        for label, action in actions.items():
            menu.add_command(label=label, command=action)
        return menu

    def show_menu(self, event):
        menu = self.build_base_menu(event)
        # Call per-class menu extender if present
        if hasattr(self, "extend_menu"):
            self.extend_menu(menu)
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
from tkinter import messagebox


class Bag(ClickableObject):
    def __init__(self, app, x, y, name=None, color=None, max_items=5):
        self.is_open = False
        self.attached_scanner = None
        self.max_items = max_items
        self.items = []  # hold attached items
        super().__init__(app, x, y, name, color)

    def create_shape(self, x, y):
        self.shape_id = self.canvas.create_rectangle(
            x, y, x + 80, y + 80,
            fill=self.color,
            outline="red",  # closed by default
            width=3
        )

    # ---------- open/close ----------
    def open_bag(self):
        if not self.is_open:
            self.is_open = True
            self.canvas.itemconfig(self.shape_id, outline="green")

    def close_bag(self):
        if self.is_open:
            self.is_open = False
            self.canvas.itemconfig(self.shape_id, outline="red")

    # ---------- items ----------
    def add_item(self, item):
        if len(self.items) >= self.max_items:
            messagebox.showwarning("Bag", f"Bag limit reached! (max {self.max_items})")
            return
        if item in self.items:
            messagebox.showinfo("Bag", f"{item.name} is already inside {self.name}")
            return
        self.items.append(item)
        item.hide()  # hide item after adding
        messagebox.showinfo("Bag", f"{item.name} added to {self.name}")

    def remove_item(self, item):
        if item in self.items:
            self.items.remove(item)
            # show item again beside bag
            x1, y1, x2, y2 = self.canvas.bbox(self.shape_id)
            cx = x2 + 30
            cy = (y1 + y2) / 2
            item.show(cx, cy)

    def remove_all_items(self):
        for item in self.items[:]:
            self.remove_item(item)

    # ---------- scanner attach/remove ----------
    def add_scanner(self, scanner):
        if self.attached_scanner is None:
            self.attached_scanner = scanner
            print(f"✅ Scanner added to {self.name}")
            return True
        else:
            print(f"⚠️ {self.name} already has a scanner")
            return False

    def remove_scanner(self):
        if self.attached_scanner:
            self.attached_scanner.attached_bag = None
            # show scanner again beside the bag
            x1, y1, x2, y2 = self.canvas.bbox(self.shape_id)
            cx = x2 + 40
            cy = (y1 + y2) / 2
            self.attached_scanner.show(cx, cy)

            self.attached_scanner = None
            self.canvas.itemconfig(self.shape_id, outline="green" if self.is_open else "red")

    # ---------- menu ----------
    def extend_menu(self, menu):
        if self.items:
            menu.add_command(label="Remove Item", command=self.open_remove_item_window)
            menu.add_command(label="Remove All Items", command=self.remove_all_items)

        # Bag info is always available
        menu.add_command(label="Bag Info", command=self.show_info)

    def open_remove_item_window(self):
        if not self.items:
            messagebox.showinfo("Remove Item", "No items to remove!")
            return

        win = tk.Toplevel(self.app.root)
        win.title(f"Remove Item from {self.name}")
        tk.Label(win, text="Select an item to remove:").pack(padx=10, pady=5)

        listbox = tk.Listbox(win)
        for item in self.items:
            listbox.insert(tk.END, item.name)
        listbox.pack(padx=10, pady=5)

        def remove_selected():
            selection = listbox.curselection()
            if selection:
                index = selection[0]
                item = self.items[index]
                self.remove_item(item)
                win.destroy()

        tk.Button(win, text="Remove", command=remove_selected).pack(pady=5)

    def show_menu(self, event):
        menu = self.build_base_menu(event)

        if self.is_open:
            menu.insert_command(0, label="Close", command=self.close_bag)
        else:
            menu.insert_command(0, label="Open", command=self.open_bag)

        if self.attached_scanner:
            menu.add_command(label="Remove Scanner", command=self.remove_scanner)

        self.extend_menu(menu)
        menu.post(event.x_root, event.y_root)

    def show_info(self):
        left = self.max_items - len(self.items)
        scanner_info = self.attached_scanner.name if self.attached_scanner else "None"
        item_names = [it.name for it in self.items] or ["None"]
        messagebox.showinfo(
            "Bag Info",
            f"Bag: {self.name}\n"
            f"Space left: {left}/{self.max_items}\n"
            f"Scanner: {scanner_info}\n"
            f"Items: {', '.join(item_names)}"
        )


class Item(ClickableObject):
    def __init__(self, app, x, y, name=None, color=None, tag=None):
        super().__init__(app, x, y, name, color)
        self.attached_tag = tag
        self.rfid = tag.rfid if tag else "No RFID"
        self.hidden = False  # to support hide/show

    def create_shape(self, x, y):
        self.shape_id = self.canvas.create_rectangle(
            x, y, x + 40, y + 40,
            fill=self.color, outline="black"
        )

    # ---------- hide/show ----------
    def hide(self):
        if not self.hidden:
            self.hidden = True
            self.canvas.itemconfigure(self.shape_id, state="hidden")
            self.canvas.itemconfigure(self.label_id, state="hidden")
            if self.attached_tag:
                self.attached_tag.hide()

    def show(self, cx=None, cy=None):
        if self.hidden:
            self.hidden = False
            if cx is not None and cy is not None:
                self.canvas.coords(self.shape_id, cx, cy, cx + 40, cy + 40)
                self.canvas.coords(self.label_id, cx + 20, cy + 20)
            self.canvas.itemconfigure(self.shape_id, state="normal")
            self.canvas.itemconfigure(self.label_id, state="normal")
            if self.attached_tag:
                self.attached_tag.show(cx + 50, cy + 20)

    # ---------- tag attach/remove ----------
    def attach_tag(self, tag):
        if self.attached_tag:
            messagebox.showinfo("Item", f"{self.name} already has a tag")
            return
        self.attached_tag = tag
        tag.attached_item = self
        self.rfid = tag.rfid
        self.canvas.itemconfig(self.shape_id, outline="blue")

    def remove_tag(self):
        if self.attached_tag:
            tag = self.attached_tag
            self.attached_tag = None
            tag.attached_item = None
            self.rfid = "No RFID"
            self.canvas.itemconfig(self.shape_id, outline="black")
            # show tag again beside the item
            bbox = self.canvas.bbox(self.shape_id)
            if bbox:
                x1, y1, x2, y2 = bbox
                cx = x2 + 30
                cy = (y1 + y2) / 2
                tag.show(cx, cy)

    # ---------- menu ----------
    def extend_menu(self, menu):
        if self.attached_tag:
            menu.add_command(label="Remove Tag", command=self.remove_tag)

        nearest_bag = self.find_nearest_bag()
        if nearest_bag:
            menu.add_command(label=f"Add to Bag: {nearest_bag.name}",
                             command=lambda b=nearest_bag: b.add_item(self))

        menu.add_command(label="Item Info", command=self.show_info)

    def show_info(self):
        tag_info = self.attached_tag.name if self.attached_tag else "None"
        messagebox.showinfo(
            "Item Info",
            f"Item: {self.name}\n"
            f"Tag: {tag_info}\n"
            f"RFID: {self.rfid}"
        )

    # ---------- find nearest bag ----------
    def find_nearest_bag(self, max_distance=80):
        center = self._center_of_shape()
        if center is None:
            return None
        ix, iy = center
        nearest = None
        nearest_dist = max_distance
        for obj in ClickableObject.instances:
            if isinstance(obj, Bag) and obj.is_open:
                bbox = obj._center_of_shape()
                if bbox is None:
                    continue
                bx, by = bbox
                dist = ((ix - bx) ** 2 + (iy - by) ** 2) ** 0.5
                if dist < nearest_dist:
                    nearest = obj
                    nearest_dist = dist
        return nearest

    # ---------- dragging ----------
    def do_drag(self, event):
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        self.canvas.move(self.shape_id, dx, dy)
        self.canvas.move(self.label_id, dx, dy)

        if self.attached_tag:
            self.canvas.move(self.attached_tag.shape_id, dx, dy)
            self.canvas.move(self.attached_tag.label_id, dx, dy)

        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    # ---------- helper ----------
    def _center_of_shape(self):
        bbox = self.canvas.bbox(self.shape_id)
        if bbox is None:
            return None
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)




class Tag(ClickableObject):
    def __init__(self, app, x, y, name=None, color=None, rfid=None):
        super().__init__(app, x, y, name, color)
        self.attached_item = None
        self.hidden = False
        self.rfid = rfid or f"RFID-{random.randint(1000, 9999)}"  # unique identifier

    def create_shape(self, x, y):
        r = 20
        self.shape_id = self.canvas.create_oval(
            x - r, y - r, x + r, y + r,
            fill=self.color, outline="black"
        )

    def hide(self):
        if not self.hidden:
            self.hidden = True
            self.canvas.itemconfigure(self.shape_id, state="hidden")
            self.canvas.itemconfigure(self.label_id, state="hidden")

    def show(self, cx=None, cy=None):
        if self.hidden:
            self.hidden = False
            if cx is not None and cy is not None:
                r = 20
                self.canvas.coords(self.shape_id, cx - r, cy - r, cx + r, cy + r)
                self.canvas.coords(self.label_id, cx, cy)
            self.canvas.itemconfigure(self.shape_id, state="normal")
            self.canvas.itemconfigure(self.label_id, state="normal")

    def attach_to_item(self, item):
        if self.attached_item is None and item.attached_tag is None:
            self.attached_item = item
            item.attached_tag = self
            self.canvas.itemconfig(item.shape_id, outline="blue")
            self.hide()

    def detach_from_item(self):
        if self.attached_item:
            item = self.attached_item
            self.attached_item = None
            item.attached_tag = None
            self.canvas.itemconfig(item.shape_id, outline="black")
            # reappear next to item
            bbox = self.canvas.bbox(item.shape_id)
            if bbox:
                x1, y1, x2, y2 = bbox
                cx = x2 + 30
                cy = (y1 + y2) / 2
                self.show(cx, cy)

    def extend_menu(self, menu):
        if self.attached_item is None:
            nearest_item = self.find_nearest_item()
            if nearest_item:
                menu.add_command(label=f"Attach to {nearest_item.name}",
                                 command=lambda: self.attach_to_item(nearest_item))
        else:
            menu.add_command(label="Detach", command=self.detach_from_item)
        menu.add_command(label=f"Tag Info (RFID: {self.rfid})", command=self.show_info)

    def show_info(self):
        attached_name = self.attached_item.name if self.attached_item else "None"
        messagebox.showinfo("Tag Info",
                            f"Tag: {self.name}\n"
                            f"Attached to: {attached_name}\n"
                            f"RFID: {self.rfid}")

    def find_nearest_item(self, max_distance=60):
        center = self._center_of_shape()
        if center is None:
            return None
        tx, ty = center
        nearest = None
        nearest_dist = max_distance
        for obj in ClickableObject.instances:
            if isinstance(obj, Item) and obj.attached_tag is None:
                item_center = obj._center_of_shape()
                if item_center is None:
                    continue
                cx, cy = item_center
                dist = ((tx - cx) ** 2 + (ty - cy) ** 2) ** 0.5
                if dist < nearest_dist:
                    nearest = obj
                    nearest_dist = dist
        return nearest

    def _center_of_shape(self):
        bbox = self.canvas.bbox(self.shape_id)
        if bbox is None:
            return None
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)




class Scanner(ClickableObject):
    def __init__(self, app, x, y, name=None, color=None):
        super().__init__(app, x, y, name, color)
        self.attached_bag = None
        self.hidden = False

    def create_shape(self, x, y):
        self.shape_id = self.canvas.create_rectangle(
            x, y, x + 100, y + 40, fill=self.color
        )

    # ---------- hide/show ----------
    def hide(self):
        if not self.hidden:
            self.hidden = True
            self.canvas.itemconfig(self.shape_id, state="hidden")
            self.canvas.itemconfig(self.label_id, state="hidden")

    def show(self, cx=None, cy=None):
        if self.hidden:
            self.hidden = False
            if cx is not None and cy is not None:
                self.canvas.coords(self.shape_id, cx, cy, cx + 100, cy + 40)
                self.canvas.coords(self.label_id, cx + 50, cy + 20)
            self.canvas.itemconfig(self.shape_id, state="normal")
            self.canvas.itemconfig(self.label_id, state="normal")

    # ---------- attach/detach ----------
    def attach_to_bag(self, bag):
        if bag.attached_scanner is None:
            bag.attached_scanner = self
            self.attached_bag = bag
            bag.canvas.itemconfig(bag.shape_id, outline="blue")
            self.hide()  # hide scanner when attached

    def detach_from_bag(self):
        if self.attached_bag:
            bag = self.attached_bag
            self.attached_bag = None
            bag.attached_scanner = None
            bag.canvas.itemconfig(bag.shape_id, outline="green" if bag.is_open else "red")
            # show scanner again beside bag
            x1, y1, x2, y2 = self.canvas.bbox(bag.shape_id)
            cx = x2 + 40
            cy = (y1 + y2) / 2
            self.show(cx, cy)

    # ---------- menu ----------
    def show_menu(self, event):
        menu = self.build_base_menu(event)
        nearest_bag = self._find_nearest_bag()
        if nearest_bag and nearest_bag.attached_scanner is None:
            menu.insert_command(0, label="Attach to Bag",
                                command=lambda b=nearest_bag: self.attach_to_bag(b))
        if self.attached_bag:
            menu.add_command(label="Detach from Bag", command=self.detach_from_bag)
        menu.post(event.x_root, event.y_root)

    # ---------- find nearest bag ----------
    def _find_nearest_bag(self, max_dist=60):
        sx, sy = self._center_of_shape()
        for obj in ClickableObject.instances:
            if isinstance(obj, Bag):
                bx, by = obj._center_of_shape()
                dist = ((sx - bx) ** 2 + (sy - by) ** 2) ** 0.5
                if dist < max_dist:
                    return obj
        return None



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
