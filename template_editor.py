import tkinter as tk
from tkinter import filedialog, messagebox, font
import fitz  # PyMuPDF
from PIL import Image, ImageTk


class PDFTemplateEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Template Editor: Auto-Fit & Accurate")
        # Maximize window or set large size
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.root.geometry(f"{int(screen_w * 0.9)}x{int(screen_h * 0.9)}")

        # --- Configuration ---
        self.display_scale = 1.0  # Will be calculated dynamically

        # --- State Variables ---
        self.doc = None
        self.page = None
        self.elements = []
        self.selected_element = None

        self.drag_data = {
            "mode": None, "item_index": None, "handle": None,
            "start_x": 0, "start_y": 0,
            "orig_x": 0, "orig_y": 0,
            "orig_w": 0, "orig_h": 0, "orig_fs": 0
        }

        self._setup_ui()

    def _setup_ui(self):
        # 1. LEFT SIDEBAR
        self.toolbar = tk.Frame(self.root, width=320, bg="#f0f0f0", padx=10, pady=10)
        self.toolbar.pack(side="left", fill="y")
        self.toolbar.pack_propagate(False)

        # File
        tk.Label(self.toolbar, text="1. File", font=("Arial", 11, "bold"), bg="#f0f0f0").pack(anchor="w")
        tk.Button(self.toolbar, text="Load PDF Template (Auto-Fit)", command=self.load_pdf, bg="#4CAF50",
                  fg="white").pack(fill="x", pady=2)
        tk.Frame(self.toolbar, height=2, bg="#ccc").pack(fill="x", pady=8)

        # Add
        tk.Label(self.toolbar, text="2. Add Elements", font=("Arial", 11, "bold"), bg="#f0f0f0").pack(anchor="w")
        tk.Button(self.toolbar, text="+ Simple Text (One Line)", command=self.add_simple_text).pack(fill="x", pady=2)
        tk.Button(self.toolbar, text="+ Multi-line Textbox", command=self.add_textbox_element).pack(fill="x", pady=2)
        tk.Button(self.toolbar, text="+ QR / Image Box", command=self.add_qr_box).pack(fill="x", pady=2)
        tk.Frame(self.toolbar, height=2, bg="#ccc").pack(fill="x", pady=8)

        # Properties
        self.prop_frame = tk.LabelFrame(self.toolbar, text="PDF Coordinates (Points)", bg="#f0f0f0", padx=5, pady=5)
        self.prop_frame.pack(fill="x")

        row1 = tk.Frame(self.prop_frame, bg="#f0f0f0");
        row1.pack(fill="x")
        tk.Label(row1, text="X:", bg="#f0f0f0").pack(side="left")
        self.entry_x = tk.Entry(row1, width=6);
        self.entry_x.pack(side="left", padx=2)
        tk.Label(row1, text="Y:", bg="#f0f0f0").pack(side="left")
        self.entry_y = tk.Entry(row1, width=6);
        self.entry_y.pack(side="left", padx=2)

        row2 = tk.Frame(self.prop_frame, bg="#f0f0f0");
        row2.pack(fill="x", pady=2)
        tk.Label(row2, text="W:", bg="#f0f0f0").pack(side="left")
        self.entry_w = tk.Entry(row2, width=6);
        self.entry_w.pack(side="left", padx=2)
        tk.Label(row2, text="H:", bg="#f0f0f0").pack(side="left")
        self.entry_h = tk.Entry(row2, width=6);
        self.entry_h.pack(side="left", padx=2)

        tk.Label(self.prop_frame, text="Text Content:", bg="#f0f0f0", anchor="w").pack(fill="x")
        self.entry_text = tk.Entry(self.prop_frame);
        self.entry_text.pack(fill="x")

        tk.Label(self.prop_frame, text="Font Size & Name:", bg="#f0f0f0", anchor="w").pack(fill="x")
        f_frame = tk.Frame(self.prop_frame, bg="#f0f0f0");
        f_frame.pack(fill="x")
        self.entry_fontsize = tk.Entry(f_frame, width=5);
        self.entry_fontsize.pack(side="left")
        self.entry_fontname = tk.Entry(f_frame, width=15);
        self.entry_fontname.insert(0, "helv");
        self.entry_fontname.pack(side="left", padx=5)

        tk.Label(self.prop_frame, text="Align (0=L, 1=C, 2=R):", bg="#f0f0f0", anchor="w").pack(fill="x")
        self.align_var = tk.IntVar(value=0)
        a_frame = tk.Frame(self.prop_frame, bg="#f0f0f0");
        a_frame.pack(fill="x")
        tk.Radiobutton(a_frame, text="L", variable=self.align_var, value=0, bg="#f0f0f0").pack(side="left")
        tk.Radiobutton(a_frame, text="C", variable=self.align_var, value=1, bg="#f0f0f0").pack(side="left")
        tk.Radiobutton(a_frame, text="R", variable=self.align_var, value=2, bg="#f0f0f0").pack(side="left")

        tk.Button(self.prop_frame, text="Apply Manual Changes", command=self.push_ui_updates, bg="#2196F3",
                  fg="white").pack(fill="x", pady=10)

        tk.Button(self.toolbar, text="GENERATE CODE", command=self.generate_code, bg="#FF5722", fg="white",
                  font=("Arial", 10, "bold")).pack(fill="x", pady=20)

        # 2. RIGHT CANVAS
        self.canvas_container = tk.Frame(self.root, bg="gray")
        self.canvas_container.pack(side="right", fill="both", expand=True)

        self.canvas = tk.Canvas(self.canvas_container, bg="#555555")
        sb_y = tk.Scrollbar(self.canvas_container, orient="vertical", command=self.canvas.yview)
        sb_x = tk.Scrollbar(self.canvas_container, orient="horizontal", command=self.canvas.xview)
        self.canvas.config(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
        sb_y.pack(side="right", fill="y")
        sb_x.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Bindings
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

    # ============================
    # LOGIC: LOADING PDF (AUTO-FIT)
    # ============================
    def load_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if not path: return
        try:
            self.doc = fitz.open(path)
            self.page = self.doc[0]

            # Get available canvas size
            self.canvas_container.update()
            view_w = self.canvas_container.winfo_width()
            view_h = self.canvas_container.winfo_height()

            # Get PDF page size in Points
            page_rect = self.page.rect

            if view_w < 100: view_w = 800  # Fallback
            if view_h < 100: view_h = 600

            # Calculate Scale to Fit (with some padding)
            scale_w = (view_w - 50) / page_rect.width
            scale_h = (view_h - 50) / page_rect.height
            self.display_scale = min(scale_w, scale_h)

            # Don't scale up indefinitely if page is tiny, but for A4 it will likely scale down or stay ~1.0
            if self.display_scale <= 0: self.display_scale = 1.0

            # Render
            mat = fitz.Matrix(self.display_scale, self.display_scale)
            pix = self.page.get_pixmap(matrix=mat)

            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            self.tk_img = ImageTk.PhotoImage(img)

            self.canvas.delete("all")
            self.elements = []
            self.selected_element = None

            self.canvas.config(scrollregion=(0, 0, pix.width, pix.height))
            self.canvas.create_image(0, 0, image=self.tk_img, anchor="nw", tags="background")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ============================
    # LOGIC: HELPERS
    # ============================
    def get_scaled_font(self, fontname, size):
        fn = fontname.lower()
        family = "Helvetica"
        if "times" in fn:
            family = "Times New Roman"
        elif "cour" in fn:
            family = "Courier New"

        # Scale fontsize for display
        scaled_size = int(size * self.display_scale)
        if scaled_size < 4: scaled_size = 4
        return font.Font(family=family, size=scaled_size)

    def _get_wrapped_text(self, text, tk_font, box_width):
        lines = []
        for paragraph in text.split('\n'):
            words = paragraph.split()
            if not words:
                lines.append("")
                continue
            current_line = words[0]
            for word in words[1:]:
                test_line = current_line + " " + word
                if tk_font.measure(test_line) <= box_width:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            lines.append(current_line)
        return "\n".join(lines)

    def redraw_all(self):
        self.canvas.delete("element_visual")
        self.canvas.delete("handle")

        for i, el in enumerate(self.elements):
            # Convert PDF Points -> Screen Pixels
            sx = el['x'] * self.display_scale
            sy = el['y'] * self.display_scale
            sw = el['w'] * self.display_scale
            sh = el['h'] * self.display_scale

            tk_font = self.get_scaled_font(el['fontname'], el['fontsize'])
            tag = f"idx_{i}"

            if el['type'] == 'textbox':
                self.canvas.create_rectangle(sx, sy, sx + sw, sy + sh, outline="purple", width=2, dash=(4, 2),
                                             tags=("element_visual", tag))
                wrapped = self._get_wrapped_text(el['text'], tk_font, sw)

                anchor = "nw"
                txt_x = sx + (2 * self.display_scale)
                justify = "left"
                if el['align'] == 1:
                    anchor = "n"
                    txt_x = sx + sw / 2
                    justify = "center"
                elif el['align'] == 2:
                    anchor = "ne"
                    txt_x = sx + sw - (2 * self.display_scale)
                    justify = "right"

                self.canvas.create_text(txt_x, sy + (2 * self.display_scale), text=wrapped, font=tk_font, fill="purple",
                                        anchor=anchor, justify=justify, tags=("element_visual", tag))

            elif el['type'] == 'simple_text':
                cid = self.canvas.create_text(sx, sy, text=el['text'], font=tk_font, fill="blue", anchor="nw",
                                              tags=("element_visual", tag))
                bbox = self.canvas.bbox(cid)
                if bbox:
                    el['w'] = (bbox[2] - bbox[0]) / self.display_scale
                    el['h'] = (bbox[3] - bbox[1]) / self.display_scale

            elif el['type'] == 'box':
                self.canvas.create_rectangle(sx, sy, sx + sw, sy + sh, outline="red", width=2,
                                             tags=("element_visual", tag))
                self.canvas.create_text(sx + sw / 2, sy + sh / 2, text="QR/IMG", fill="red",
                                        font=("Arial", int(10 * self.display_scale)), tags=("element_visual", tag))

        if self.selected_element is not None:
            self.draw_handles(self.elements[self.selected_element])

    def draw_handles(self, el):
        sx = el['x'] * self.display_scale
        sy = el['y'] * self.display_scale
        sw = el['w'] * self.display_scale
        sh = el['h'] * self.display_scale

        size = 8
        corners = [('nw', sx, sy), ('ne', sx + sw, sy), ('sw', sx, sy + sh), ('se', sx + sw, sy + sh)]
        for tag, cx, cy in corners:
            self.canvas.create_rectangle(cx - size, cy - size, cx + size, cy + size, fill="yellow", outline="black",
                                         tags=("handle", tag))

    # ============================
    # LOGIC: ADDING ITEMS
    # ============================
    def add_simple_text(self):
        if not self.page: return
        self.elements.append({"type": "simple_text", "text": "Name", "x": 50, "y": 50, "w": 50, "h": 12, "fontsize": 12,
                              "fontname": "helv", "align": 0, "is_square": False})
        self.select_idx(len(self.elements) - 1)

    def add_textbox_element(self):
        if not self.page: return
        self.elements.append(
            {"type": "textbox", "text": "Multi-line Text", "x": 50, "y": 80, "w": 150, "h": 50, "fontsize": 12,
             "fontname": "helv", "align": 1, "is_square": False})
        self.select_idx(len(self.elements) - 1)

    def add_qr_box(self):
        if not self.page: return
        self.elements.append(
            {"type": "box", "text": "QR", "x": 50, "y": 150, "w": 50, "h": 50, "fontsize": 0, "fontname": "",
             "align": 0, "is_square": True})
        self.select_idx(len(self.elements) - 1)

    def select_idx(self, idx):
        self.selected_element = idx
        self.update_ui_from_selection()
        self.redraw_all()

    # ============================
    # INTERACTION
    # ============================
    def on_mouse_down(self, event):
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        closest = self.canvas.find_closest(cx, cy, halo=5)
        tags = self.canvas.gettags(closest[0]) if closest else ()

        if "handle" in tags:
            handle = [t for t in tags if t in ['nw', 'ne', 'sw', 'se']][0]
            self.drag_data.update({
                'mode': 'RESIZE', 'handle': handle, 'item_index': self.selected_element,
                'start_x': cx, 'start_y': cy,
                'orig_w': self.elements[self.selected_element]['w'],
                'orig_h': self.elements[self.selected_element]['h'],
                'orig_fs': self.elements[self.selected_element]['fontsize']
            })
            return

        closest_el = self.canvas.find_closest(cx, cy, halo=2)
        el_tags = self.canvas.gettags(closest_el[0]) if closest_el else ()
        idx = next((int(t.split("_")[1]) for t in el_tags if t.startswith("idx_")), None)

        if idx is not None:
            self.select_idx(idx)
            self.drag_data.update({
                'mode': 'MOVE', 'item_index': idx,
                'start_x': cx, 'start_y': cy,
                'orig_x': self.elements[idx]['x'],
                'orig_y': self.elements[idx]['y']
            })
        else:
            self.selected_element = None
            self.redraw_all()

    def on_mouse_drag(self, event):
        if not self.drag_data['mode']: return
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

        # Math: Divide delta by scale to get real PDF point delta
        dx = (cx - self.drag_data['start_x']) / self.display_scale
        dy = (cy - self.drag_data['start_y']) / self.display_scale
        el = self.elements[self.drag_data['item_index']]

        if self.drag_data['mode'] == 'MOVE':
            el['x'] = self.drag_data['orig_x'] + dx
            el['y'] = self.drag_data['orig_y'] + dy
            self.update_ui_from_selection()
            self.redraw_all()

        elif self.drag_data['mode'] == 'RESIZE':
            new_w = max(5, self.drag_data['orig_w'] + dx)
            new_h = max(5, self.drag_data['orig_h'] + dy)
            if el['is_square']:
                dim = max(new_w, new_h);
                new_w = dim;
                new_h = dim
            el['w'] = new_w;
            el['h'] = new_h
            if el['type'] == 'simple_text':
                ratio = new_h / self.drag_data['orig_h']
                el['fontsize'] = max(4, int(self.drag_data['orig_fs'] * ratio))
            self.update_ui_from_selection()
            self.redraw_all()

    def on_mouse_up(self, event):
        self.drag_data['mode'] = None

    # ============================
    # UI Sync & Generate
    # ============================
    def update_ui_from_selection(self):
        if self.selected_element is None: return
        el = self.elements[self.selected_element]
        self.entry_x.delete(0, tk.END);
        self.entry_x.insert(0, f"{el['x']:.1f}")
        self.entry_y.delete(0, tk.END);
        self.entry_y.insert(0, f"{el['y']:.1f}")
        self.entry_w.delete(0, tk.END);
        self.entry_w.insert(0, f"{el['w']:.1f}")
        self.entry_h.delete(0, tk.END);
        self.entry_h.insert(0, f"{el['h']:.1f}")
        self.entry_text.delete(0, tk.END);
        self.entry_text.insert(0, el['text'])
        self.entry_fontsize.delete(0, tk.END);
        self.entry_fontsize.insert(0, el['fontsize'])
        self.entry_fontname.delete(0, tk.END);
        self.entry_fontname.insert(0, el['fontname'])
        self.align_var.set(el['align'])

    def push_ui_updates(self):
        if self.selected_element is None: return
        el = self.elements[self.selected_element]
        try:
            el['x'] = float(self.entry_x.get())
            el['y'] = float(self.entry_y.get())
            el['w'] = float(self.entry_w.get())
            el['h'] = float(self.entry_h.get())
            el['text'] = self.entry_text.get()
            el['fontsize'] = int(self.entry_fontsize.get())
            el['fontname'] = self.entry_fontname.get()
            el['align'] = self.align_var.get()
            self.redraw_all()
        except:
            pass

    def generate_code(self):
        print("\n" + "=" * 50 + "\n   ACCURATE PDF COORDINATES (Points)\n" + "=" * 50)
        for el in self.elements:
            name = el["text"].replace("\n", "").replace(" ", "_").upper()[:15]
            x, y = int(el['x']), int(el['y'])
            w, h = int(el['w']), int(el['h'])

            if el['type'] == 'simple_text':
                print(f"COORDS_{name} = ({x}, {y})")
                print(
                    f"page.insert_text(({x}, {y}), \"{el['text']}\", fontsize={el['fontsize']}, fontname=\"{el['fontname']}\", color=(0, 0, 0))")
            elif el['type'] == 'textbox':
                print(f"RECT_{name} = fitz.Rect({x}, {y}, {x + w}, {y + h})")
                print(
                    f"page.insert_textbox(RECT_{name}, \"{el['text'].replace(chr(10), ' ')}\", fontsize={el['fontsize']}, fontname=\"{el['fontname']}\", align={el['align']}, color=(0, 0, 0))")
            elif el['type'] == 'box':
                print(f"RECT_{name} = fitz.Rect({x}, {y}, {x + w}, {y + h})")
                print(f"page.insert_image(RECT_{name}, stream=img_bytes)")
            print("-" * 30)
        messagebox.showinfo("Success", "High-precision coordinates printed to console.")


if __name__ == "__main__":
    root = tk.Tk()
    app = PDFTemplateEditor(root)
    root.mainloop()