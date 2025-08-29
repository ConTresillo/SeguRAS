import tkinter as tk
from tkinter import simpledialog, colorchooser, messagebox
import random


def random_color():
    return "#%06x" % random.randint(0, 0xFFFFFF)


class DraggableObject:
    id_counters = {}

    def __init__(self, canvas, obj_type, coords):
        self.canvas = canvas
        self.type = obj_type
        DraggableObject.id_counters.setdefault(obj_type, 0)
        DraggableObject.id_counters[obj_type] += 1
        self.id_str = f"{obj_type}{DraggableObject.id_counters[obj_type]}"
        self.fill_color = random_color()

        self.item_id = self.create_shape(coords)
        self.label_id = self.create_label(coords, self.id_str)

        # Bindings for both shape and label
        for cid in (self.item_id, self.label_id):
            canvas.tag_bind(cid, "<ButtonPress-1>", self.on_drag_start)
            canvas.tag_bind(cid, "<B1-Motion>", self.on_drag_motion)
            canvas.tag_bind(cid, "<Button-3>", self.show_context_menu)

        self.last_x = None
        self.last_y = None

        self.menu = tk.Menu(canvas, tearoff=0)
        self.menu.add_command(label="Change Color", command=self.change_color)
        self.menu.add_command(label="Rename", command=self.rename)
        self.menu.add_command(label="Delete", command=self.delete)
        self.menu.add_command(label="Duplicate", command=self.duplicate)

    def create_shape(self, coords):
        # Base creates rectangle by default - subclasses override this
        return self.canvas.create_rectangle(*coords, fill=self.fill_color, tags=self.id_str)

    def is_color_dark(self,hex_color):
        # Convert hex color to RGB
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        # Calculate perceived brightness
        brightness = (0.299 * r + 0.587 * g + 0.114 * b)
        # Threshold can be tweaked; below 128 is dark
        return brightness < 128

    def create_label(self, coords, text):
        label_x = (coords[0] + coords[2]) / 2
        label_y = (coords[1] + coords[3]) / 2
        width = abs(coords[2] - coords[0])
        height = abs(coords[3] - coords[1])

        # Initial guess
        font_size = int(min(width, height) * 0.7)
        if font_size < 6:
            font_size = 6

        text_color = 'white' if self.is_color_dark(self.fill_color) else 'black'

        # Try font, shrink if doesn't fit
        while font_size > 6:
            font = ("Arial", font_size, "bold")
            temp_id = self.canvas.create_text(label_x, label_y, text=text, font=font, fill=text_color, anchor="center")
            bbox = self.canvas.bbox(temp_id)
            if bbox:
                t_width = bbox[2] - bbox[0]
                t_height = bbox[3] - bbox[1]
                # Check if text fits within 85% of object width&height (little margin)
                if t_width <= width * 0.85 and t_height <= height * 0.8:
                    self.canvas.delete(temp_id)
                    break
            self.canvas.delete(temp_id)
            font_size -= 1

        # Now actually create and return the label
        return self.canvas.create_text(
            label_x, label_y,
            text=text,
            font=("Arial", font_size, "bold"),
            fill=text_color,
            anchor="center"
        )

    def on_drag_start(self, event):
        self.last_x = event.x
        self.last_y = event.y

    def on_drag_motion(self, event):
        dx = event.x - self.last_x
        dy = event.y - self.last_y
        self.canvas.move(self.item_id, dx, dy)
        self.canvas.move(self.label_id, dx, dy)
        self.last_x = event.x
        self.last_y = event.y

    def show_context_menu(self, event):
        self.menu.post(event.x_root, event.y_root)

    def change_color(self):
        color = colorchooser.askcolor(title=f"Change color of {self.id_str}")
        if color[1]:
            self.fill_color = color[1]
            self.canvas.itemconfig(self.item_id, fill=color[1])
            # Update label color dynamically based on new fill color brightness
            new_text_color = 'white' if self.is_color_dark(self.fill_color) else 'black'
            self.canvas.itemconfig(self.label_id, fill=new_text_color)

    def rename(self):
        new_name = simpledialog.askstring("Rename", f"Rename {self.id_str} to:")
        if new_name:
            self.id_str = new_name
            self.canvas.itemconfig(self.label_id, text=new_name)
            self.canvas.itemconfig(self.item_id, tags=new_name)
            self.canvas.itemconfig(self.label_id, tags=new_name)
            update_master_list()

    def delete(self):
        if messagebox.askyesno("Delete", f"Delete {self.id_str}?"):
            self.canvas.delete(self.item_id)
            self.canvas.delete(self.label_id)
            objects.remove(self)
            update_master_list()

    def duplicate(self):
        coords = self.canvas.coords(self.item_id)
        offset = 20
        new_coords = [coord + (offset if i % 2 == 0 else offset) for i, coord in enumerate(coords)]
        new_obj = type(self)(self.canvas, new_coords)  # Create same type object with offset coords
        objects.append(new_obj)
        update_master_list()


# Subclasses

class Bag(DraggableObject):
    def __init__(self, canvas, coords):
        super().__init__(canvas, 'Bag', coords)

    def create_shape(self, coords):
        # Big square
        x1, y1, x2, y2 = coords
        side = min(x2 - x1, y2 - y1)
        return self.canvas.create_rectangle(x1, y1, x1 + side, y1 + side, fill=self.fill_color, tags=self.id_str)


class Item(DraggableObject):
    def __init__(self, canvas, coords):
        x1, y1, x2, y2 = coords
        side = min(x2 - x1, y2 - y1) // 2
        actual_coords = (x1, y1, x1 + side, y1 + side)
        super().__init__(canvas, 'Item', actual_coords)

    def create_shape(self, coords):
        return self.canvas.create_rectangle(*coords, fill=self.fill_color, tags=self.id_str)




class RFID_Tag(DraggableObject):
    def __init__(self, canvas, coords):
        super().__init__(canvas, 'RFID_Tag', coords)

    def create_shape(self, coords):
        return self.canvas.create_oval(*coords, fill=self.fill_color, tags=self.id_str)


class RFID_Scanner(DraggableObject):
    def __init__(self, canvas, coords):
        super().__init__(canvas, 'RFID_Scanner', coords)

    def create_shape(self, coords):
        return self.canvas.create_rectangle(*coords, fill=self.fill_color, tags=self.id_str)


# Master list update
def update_master_list():
    master_list.delete(0, tk.END)
    for obj in objects:
        master_list.insert(tk.END, f"{obj.id_str} ({obj.type})")


# Setup window
root = tk.Tk()
root.geometry("1000x700")

control_frame = tk.Frame(root)
control_frame.pack(side='top', fill='x', padx=10, pady=5)

canvas = tk.Canvas(root, width=800, height=600, bg='white')
canvas.pack(side='left')

objects = []

current_type = tk.StringVar(value='Item')

type_menu = tk.OptionMenu(control_frame, current_type, 'Bag', 'Item', 'RFID_Tag', 'RFID_Scanner')
type_menu.pack(side='left', padx=5)


def create_new_object():
    sizes = {
        'Bag': (50, 50, 150, 150),
        'Item': (200, 50, 300, 150),
        'RFID_Tag': (350, 50, 390, 90),
        'RFID_Scanner': (400, 50, 460, 90),
    }

    obj_type = current_type.get()

    cls_map = {
        'Bag': Bag,
        'Item': Item,
        'RFID_Tag': RFID_Tag,
        'RFID_Scanner': RFID_Scanner,
    }

    obj = cls_map[obj_type](canvas, sizes[obj_type])
    objects.append(obj)
    update_master_list()


create_button = tk.Button(control_frame, text="Create New Object", command=create_new_object)
create_button.pack(side='left', padx=5)

master_frame = tk.Frame(root)
master_frame.pack(side='right', fill='y', padx=10, pady=5)

tk.Label(master_frame, text="All Created Objects").pack()
master_list = tk.Listbox(master_frame, width=25)
master_list.pack(fill='y')

root.mainloop()
