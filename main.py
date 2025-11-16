import customtkinter as ctk
from PIL import Image, ImageTk, ImageEnhance, ImageOps, ImageDraw, ImageFont
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser, simpledialog
import cv2
import numpy as np
import pytesseract
import os
import io
from rembg import remove, new_session


pytesseract.pytesseract.tesseract_cmd #= Put your tesseract executable path here if you want OCR to work

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class PictureEditor(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Picture_Editor")
        self.geometry("1400x900")
        self.minsize(1100, 650)

       
        self.original_image = None
        self.current_image = None
        self.display_image = None
        self.history = []
        self.history_index = -1
        self.zoom_factor = 1.0
        self.pan_x = self.pan_y = 0
        self.is_panning = False
        self.last_x = self.last_y = 0

        
        self.drawing = False
        self.draw_overlay = None
        self.draw_color = "red"
        self.draw_size = 10
        self.tool_var = tk.StringVar(value="brush")
        self.fill_var = tk.BooleanVar(value=False)
        self.draw_enabled = tk.BooleanVar(value=False)  

        
        self.text_mode = tk.BooleanVar(value=False)
        self.text_color = "white"

        self.setup_ui()
        self.setup_bindings()
        self.update_image_display()

    def setup_ui(self):
        
        self.sidebar = ctk.CTkScrollableFrame(self, width=320, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        

        ctk.CTkLabel(self.sidebar, text="Picture_Editor", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=20)

        ctk.CTkButton(self.sidebar, text="Kép megnyitása (Ctrl+O)", command=self.open_image, height=40).pack(pady=8, padx=20, fill="x")
        ctk.CTkButton(self.sidebar, text="Mentés (Ctrl+S)", command=self.save_image, height=40).pack(pady=5, padx=20, fill="x")

        
        ctk.CTkLabel(self.sidebar, text="Rajzolás & Eszközök", font=ctk.CTkFont(weight="bold")).pack(pady=(25,5), anchor="w", padx=20)

        tools_scroll = ctk.CTkScrollableFrame(self.sidebar, height=90, orientation="horizontal")
        tools_scroll.pack(pady=8, padx=20, fill="x")

        row1 = ctk.CTkFrame(tools_scroll); row1.pack(pady=4)
        row2 = ctk.CTkFrame(tools_scroll); row2.pack(pady=4)

        for text, val in [("Ecset", "brush"), ("Vonal", "line"), ("Téglalap", "rectangle")]:
            ctk.CTkRadioButton(row1, text=text, variable=self.tool_var, value=val).pack(side="left", padx=10)
        for text, val in [("Kör", "circle"), ("Radír", "eraser")]:
            ctk.CTkRadioButton(row2, text=text, variable=self.tool_var, value=val).pack(side="left", padx=10)

        
        opts = ctk.CTkFrame(self.sidebar)
        opts.pack(pady=8, padx=20, fill="x")
        ctk.CTkCheckBox(opts, text="Rajzolás be", variable=self.draw_enabled,
                        command=self.toggle_drawing_mode, fg_color="crimson").pack(side="left", padx=5)
        ctk.CTkButton(opts, text="Szín", width=60, command=self.choose_draw_color).pack(side="left", padx=5)
        ctk.CTkCheckBox(opts, text="Kitöltés", variable=self.fill_var).pack(side="left", padx=5)

        ctk.CTkLabel(self.sidebar, text="Eszköz méret:").pack(anchor="w", padx=30)
        self.brush_scale = ctk.CTkSlider(self.sidebar, from_=1, to=100, command=self.update_brush_size)
        self.brush_scale.pack(pady=5, padx=30, fill="x")
        self.brush_scale.set(10)
        self.brush_size_label = ctk.CTkLabel(self.sidebar, text="10 px")
        self.brush_size_label.pack(anchor="w", padx=30)

        
        ctk.CTkLabel(self.sidebar, text="Szöveg hozzáadása", font=ctk.CTkFont(weight="bold")).pack(pady=(25,5), anchor="w", padx=20)
        text_opts = ctk.CTkFrame(self.sidebar)
        text_opts.pack(pady=8, padx=20, fill="x")
        ctk.CTkCheckBox(text_opts, text="Szöveg mód", variable=self.text_mode,
                        command=lambda: messagebox.showinfo("Szöveg", "Kattints a képre a szöveg elhelyezéséhez!")).pack(side="left", padx=5)
        ctk.CTkButton(text_opts, text="Szín", width=60, command=self.choose_text_color).pack(side="right", padx=5)

        self.text_input = ctk.CTkEntry(self.sidebar, placeholder_text="Ide írd a szöveget...")
        self.text_input.pack(pady=5, padx=20, fill="x")
        self.text_input.insert(0, "Szöveg")

        
        ctk.CTkLabel(self.sidebar, text="Átalakítás", font=ctk.CTkFont(weight="bold")).pack(pady=(25,5), anchor="w", padx=20)
        for text, cmd in [("Átméretezés", self.resize_image), ("Forgatás 90°", lambda: self.rotate(90)), ("Tükrözés", self.flip_horizontal)]:
            ctk.CTkButton(self.sidebar, text=text, command=cmd).pack(pady=3, padx=20, fill="x")

        ctk.CTkLabel(self.sidebar, text="Szűrők", font=ctk.CTkFont(weight="bold")).pack(pady=(20,5), anchor="w", padx=20)
        for name, cmd in [("Szürke", self.apply_grayscale), ("Elmosás", self.apply_blur), ("Élesítés", self.apply_sharpen),
                          ("Szépia", self.apply_sepia), ("Vintage", self.apply_vintage)]:
            ctk.CTkButton(self.sidebar, text=name, command=cmd).pack(pady=3, padx=20, fill="x")

        ctk.CTkLabel(self.sidebar, text="AI & OCR", font=ctk.CTkFont(weight="bold")).pack(pady=(20,5), anchor="w", padx=20)
        ctk.CTkButton(self.sidebar, text="Háttér eltávolítás (AI)", command=self.remove_background, fg_color="purple").pack(pady=8, padx=20, fill="x")
        ctk.CTkButton(self.sidebar, text="Szöveg kinyerése (OCR)", command=self.extract_text).pack(pady=5, padx=20, fill="x")

        ctk.CTkLabel(self.sidebar, text="Visszaállítás", font=ctk.CTkFont(weight="bold")).pack(pady=(20,5), anchor="w", padx=20)
        for text, cmd in [("Vissza (Ctrl+Z)", self.undo), ("Előre (Ctrl+Y)", self.redo), ("Teljes visszaállítás", self.reset_image)]:
            ctk.CTkButton(self.sidebar, text=text, command=cmd, fg_color="darkred" if "Teljes" in text else None).pack(pady=5, padx=20, fill="x")

        
        self.canvas = tk.Canvas(self, bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=10, pady=10)

        
        self.v_scroll = ctk.CTkScrollbar(self, command=self.canvas.yview)
        self.h_scroll = ctk.CTkScrollbar(self, orientation="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        self.v_scroll.pack(side="right", fill="y")
        self.h_scroll.pack(side="bottom", fill="x")

    def setup_bindings(self):
        self.canvas.bind("<ButtonPress-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-4>", lambda e: self.zoom(1.1))
        self.canvas.bind("<Button-5>", lambda e: self.zoom(0.9))

        self.bind("<Control-z>", lambda e: self.undo())
        self.bind("<Control-y>", lambda e: self.redo())
        self.bind("<Control-o>", lambda e: self.open_image())
        self.bind("<Control-s>", lambda e: self.save_image())


    def toggle_drawing_mode(self):
        self.drawing = self.draw_enabled.get()
        if self.drawing:
            tool_names = {"brush": "Ecset", "line": "Vonal", "rectangle": "Téglalap", "circle": "Kör", "eraser": "Radír"}
            tool = tool_names.get(self.tool_var.get(), "Eszköz")
            messagebox.showinfo("Rajzolás aktív!", f"{tool} mód bekapcsolva!\nBal kattintás + húzás: rajzolás\nJobb kattintás: mozgatás (pan)")

    def update_brush_size(self, val):
        self.draw_size = int(float(val))
        self.brush_size_label.configure(text=f"{self.draw_size} px")

    def choose_draw_color(self):
        color = colorchooser.askcolor(title="Válassz ecset/szöveg színt")[1]
        if color:
            self.draw_color = color

    def choose_text_color(self):
        color = colorchooser.askcolor(title="Szöveg színe")[1]
        if color:
            self.text_color = color

    def finalize_drawing(self):
        if self.draw_overlay:
            self.current_image = Image.alpha_composite(self.current_image.convert("RGBA"), self.draw_overlay).convert("RGB")
            self.draw_overlay = None
            self.save_state()
            self.update_image_display()

    def on_click(self, event):
        if not self.current_image:
            return
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        img_x = canvas_x / self.zoom_factor + self.pan_x / self.zoom_factor  
        img_y = canvas_y / self.zoom_factor + self.pan_y / self.zoom_factor

        if event.num == 3:  # Jobb klikk = panning
            self.is_panning = True
            self.last_x, self.last_y = event.x, event.y
            return

        if self.text_mode.get():
            self.place_text_at(img_x, img_y)
            return

        if not self.drawing:
            return

        color = "white" if self.tool_var.get() == "eraser" else self.draw_color
        self.draw_overlay = Image.new("RGBA", self.current_image.size, (0,0,0,0))
        self.draw = ImageDraw.Draw(self.draw_overlay)
        self.start_x = self.last_x = img_x
        self.start_y = self.last_y = img_y

        tool = self.tool_var.get()
        if tool in ["brush", "eraser"]:
            self.draw.ellipse([img_x - self.draw_size/2, img_y - self.draw_size/2,
                               img_x + self.draw_size/2, img_y + self.draw_size/2], fill=color)
            self.update_image_display()