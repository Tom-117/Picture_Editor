import customtkinter as ctk
from PIL import Image, ImageTk, ImageEnhance, ImageOps, ImageDraw, ImageFont
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser, simpledialog
import cv2
import numpy as np
import pytesseract
import os



pytesseract.pytesseract.tesseract_cmd #= tesseract.exe path if needed
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class PictureEditor(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Picture_Editor")
        self.geometry("1920x1080")
        self.minsize(1100, 650)
        self.has_transparency = False
        self.bg_color = "#808080" 
       
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
        self.permanent_drawings = None
        self.draw_color = "red"
        self.draw_size = 10
        self.tool_var = tk.StringVar(value="brush")
        self.fill_var = tk.BooleanVar(value=False)
        self.draw_enabled = tk.BooleanVar(value=False)  

        
        self.text_mode = tk.BooleanVar(value=False)
        self.text_color = "white"
        
        self.bg_removal_mode = False
        self.bg_removal_method = None  
        self.bg_selection_rect = None
        self.bg_start_x = self.bg_start_y = None

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

        ctk.CTkLabel(self.sidebar, text="Háttér eltávolítás & OCR", font=ctk.CTkFont(weight="bold")).pack(pady=(20,5), anchor="w", padx=20)
        ctk.CTkButton(self.sidebar, text="Háttér eltávolítás", command=self.remove_background_grabcut, fg_color="purple").pack(pady=8, padx=20, fill="x")
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
        self.canvas.bind("<ButtonPress-3>", self.on_right_click)
        self.canvas.bind("<B3-Motion>", self.on_right_drag)
        self.canvas.bind("<ButtonRelease-3>", self.on_right_release)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-4>", lambda e: self.zoom(1.1))
        self.canvas.bind("<Button-5>", lambda e: self.zoom(0.9))

        self.bind("<Control-z>", lambda e: self.undo())
        self.bind("<Control-y>", lambda e: self.redo())
        self.bind("<Control-o>", lambda e: self.open_image())
        self.bind("<Control-s>", lambda e: self.save_image())

    def on_right_click(self, event):
        
        self.is_panning = True
        self.last_x = event.x
        self.last_y = event.y
        self.canvas.config(cursor="fleur")

    def on_right_drag(self, event):
        
        if self.is_panning:
            dx = event.x - self.last_x
            dy = event.y - self.last_y
            self.pan_x += dx
            self.pan_y += dy
            self.last_x = event.x
            self.last_y = event.y
            self.update_image_display()

    def on_right_release(self, event):
       
        self.is_panning = False
        self.canvas.config(cursor="")

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
            # Initialize permanent drawings layer if it doesn't exist
            if self.permanent_drawings is None:
                self.permanent_drawings = Image.new("RGBA", self.current_image.size, (0,0,0,0))

            # Composite the new drawing onto the permanent layer
            self.permanent_drawings = Image.alpha_composite(self.permanent_drawings, self.draw_overlay)
            self.draw_overlay = None
            self.save_state()
            self.update_image_display()

    def on_click(self, event):
        if not self.current_image:
            return
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        img_x = (canvas_x - self.pan_x) / self.zoom_factor
        img_y = (canvas_y - self.pan_y) / self.zoom_factor

        
        if self.bg_removal_mode:
            self.bg_start_x = img_x
            self.bg_start_y = img_y
            return

        
        if self.text_mode.get():
            self.place_text_at(img_x, img_y)
            return

        
        if not self.drawing:
            return

        tool = self.tool_var.get()

        # For eraser, work directly on permanent layer
        if tool == "eraser":
            if self.permanent_drawings is None:
                self.permanent_drawings = Image.new("RGBA", self.current_image.size, (0,0,0,0))

            # Create temporary overlay for erasing
            self.draw_overlay = Image.new("RGBA", self.current_image.size, (0,0,0,0))
            self.draw = ImageDraw.Draw(self.permanent_drawings) 

           
            pixels = self.permanent_drawings.load()
            for i in range(int(img_x - self.draw_size/2), int(img_x + self.draw_size/2)):
                for j in range(int(img_y - self.draw_size/2), int(img_y + self.draw_size/2)):
                    if 0 <= i < self.current_image.width and 0 <= j < self.current_image.height:
                        # Check if within circle
                        if (i - img_x)**2 + (j - img_y)**2 <= (self.draw_size/2)**2:
                            pixels[i, j] = (0, 0, 0, 0)
        else:
           
            color = self.draw_color
            self.draw_overlay = Image.new("RGBA", self.current_image.size, (0,0,0,0))
            self.draw = ImageDraw.Draw(self.draw_overlay)

            if tool == "brush":
                self.draw.ellipse([img_x - self.draw_size/2, img_y - self.draw_size/2,
                                   img_x + self.draw_size/2, img_y + self.draw_size/2], fill=color)

        self.start_x = self.last_x = img_x
        self.start_y = self.last_y = img_y
        self.update_image_display()

    def on_drag(self, event):
        if not self.current_image:
            return

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        img_x = (canvas_x - self.pan_x) / self.zoom_factor
        img_y = (canvas_y - self.pan_y) / self.zoom_factor

        # Background removal selection visualization
        if self.bg_removal_mode and self.bg_start_x is not None:
            self.canvas.delete("bg_selection")
            x1 = self.bg_start_x * self.zoom_factor + self.pan_x
            y1 = self.bg_start_y * self.zoom_factor + self.pan_y
            x2 = img_x * self.zoom_factor + self.pan_x
            y2 = img_y * self.zoom_factor + self.pan_y
            self.canvas.create_rectangle(x1, y1, x2, y2, outline="cyan", width=2, tags="bg_selection", dash=(5, 5))
            return

        if not self.drawing:
            return

        tool = self.tool_var.get()

        if tool == "eraser":
            
            pixels = self.permanent_drawings.load()

            # Erase along the line from last position to current
            steps = int(max(abs(img_x - self.last_x), abs(img_y - self.last_y)))
            for step in range(steps + 1):
                t = step / max(steps, 1)
                x = self.last_x + t * (img_x - self.last_x)
                y = self.last_y + t * (img_y - self.last_y)

                for i in range(int(x - self.draw_size/2), int(x + self.draw_size/2)):
                    for j in range(int(y - self.draw_size/2), int(y + self.draw_size/2)):
                        if 0 <= i < self.current_image.width and 0 <= j < self.current_image.height:
                            if (i - x)**2 + (j - y)**2 <= (self.draw_size/2)**2:
                                pixels[i, j] = (0, 0, 0, 0)

        elif tool == "brush":
            color = self.draw_color
            self.draw.line([self.last_x, self.last_y, img_x, img_y], fill=color, width=self.draw_size)
            self.draw.ellipse([img_x - self.draw_size/2, img_y - self.draw_size/2,
                               img_x + self.draw_size/2, img_y + self.draw_size/2], fill=color)

        self.last_x, self.last_y = img_x, img_y
        self.update_image_display()

    def on_release(self, event):
        if not self.current_image:
            return

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        img_x = (canvas_x - self.pan_x) / self.zoom_factor
        img_y = (canvas_y - self.pan_y) / self.zoom_factor

        
        if self.bg_removal_mode and self.bg_start_x is not None:
            self.canvas.delete("bg_selection")
            x1, y1 = int(min(self.bg_start_x, img_x)), int(min(self.bg_start_y, img_y))
            x2, y2 = int(max(self.bg_start_x, img_x)), int(max(self.bg_start_y, img_y))

            # Ensure coordinates are within image bounds
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(self.current_image.width, x2)
            y2 = min(self.current_image.height, y2)

            if x2 > x1 and y2 > y1:
                if hasattr(self, 'bg_removal_method') and self.bg_removal_method == 'grabcut':
                    self.process_grabcut_removal((x1, y1, x2, y2))

            self.bg_removal_mode = False
            self.bg_start_x = self.bg_start_y = None
            self.canvas.config(cursor="")
            return

        # Don't process drawing if not in drawing mode or no start position
        if not self.drawing or not hasattr(self, 'start_x'):
            return

        tool = self.tool_var.get()

       
        if tool == "eraser":
            self.finalize_drawing()
            return

        color = self.draw_color
        fill_color = color if self.fill_var.get() else None

        if tool == "line":
            self.draw.line([self.start_x, self.start_y, img_x, img_y], fill=color, width=self.draw_size)
        elif tool == "rectangle":
            self.draw.rectangle([min(self.start_x, img_x), min(self.start_y, img_y),
                                 max(self.start_x, img_x), max(self.start_y, img_y)],
                                outline=color, width=self.draw_size, fill=fill_color)
        elif tool == "circle":
            bbox = [min(self.start_x, img_x), min(self.start_y, img_y),
                    max(self.start_x, img_x), max(self.start_y, img_y)]
            self.draw.ellipse(bbox, outline=color, width=self.draw_size, fill=fill_color)

        self.finalize_drawing()

    def place_text_at(self, x, y):
        text = self.text_input.get().strip()
        if not text:
            return
        size = simpledialog.askinteger("Betűméret", "Méret (10-200):", minvalue=10, maxvalue=200, initialvalue=50)
        if not size:
            return
        try:
            font = ImageFont.truetype("arial.ttf", size)
        except:
            font = ImageFont.load_default()
        overlay = Image.new("RGBA", self.current_image.size, (0,0,0,0))
        draw = ImageDraw.Draw(overlay)
        draw.text((x, y), text, font=font, fill=self.text_color + "FF",
                  stroke_width=4, stroke_fill="black", anchor="mm")
        self.current_image = Image.alpha_composite(self.current_image.convert("RGBA"), overlay).convert("RGB")
        self.save_state()
        self.update_image_display()

    
    def open_image(self):
       
     path = filedialog.askopenfilename(filetypes=[("Képek", "*.png *.jpg *.jpeg *.bmp *.tiff *.webp")])
     if path:
         try:
             self.original_image = Image.open(path).convert("RGB")
             self.current_image = self.original_image.copy()
             self.permanent_drawings = None
             self.has_transparency = False

             
             self.history = [{
                 'image': np.array(self.current_image),
                 'drawings': None,
                 'has_transparency': False
             }]
             self.history_index = 0
             self.zoom_factor = 1.0
             self.pan_x = self.pan_y = 0
             self.update_image_display()
             messagebox.showinfo("Siker!", "Kép betöltve!")
         except Exception as e:
             messagebox.showerror("Hiba", f"Nem sikerült betölteni: {e}")

    def save_state(self):
        if self.current_image:
            self.history = self.history[:self.history_index + 1]
        # Save both the image and the drawing layer
        state = {
            'image': np.array(self.current_image),
            'drawings': self.permanent_drawings.copy() if self.permanent_drawings else None,
            'has_transparency': self.has_transparency
        }
        self.history.append(state)
        self.history_index += 1
        if len(self.history) > 30:
            self.history.pop(0)
            self.history_index -= 1

    def sync_drawing_layer_size(self):
        
        if self.permanent_drawings and self.current_image:
            if self.permanent_drawings.size != self.current_image.size:
                old_drawings = self.permanent_drawings
                self.permanent_drawings = Image.new("RGBA", self.current_image.size, (0,0,0,0))
               
                self.permanent_drawings.paste(old_drawings, (0, 0), old_drawings)

    def undo(self):
       
        if  self.history_index > 0:
          self.history_index -= 1
          state = self.history[self.history_index]
          
          
          if isinstance(state, dict):
              self.current_image = Image.fromarray(state['image'])
              self.permanent_drawings = state['drawings'].copy() if state['drawings'] else None
              self.has_transparency = state.get('has_transparency', False)
          else:
             
              self.current_image = Image.fromarray(state)
              
          self.update_image_display()

    def redo(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            state = self.history[self.history_index]

            
            if isinstance(state, dict):
                self.current_image = Image.fromarray(state['image'])
                self.permanent_drawings = state['drawings'].copy() if state['drawings'] else None
                self.has_transparency = state.get('has_transparency', False)
            else:
                
                self.current_image = Image.fromarray(state)

            self.update_image_display()

    def reset_image(self):
     if self.original_image:
         self.current_image = self.original_image.copy()
         self.permanent_drawings = None
         self.has_transparency = False

         
         self.history = [{
             'image': np.array(self.current_image),
             'drawings': None,
             'has_transparency': False
         }]
         self.history_index = 0
         self.zoom_factor = 1.0
         self.pan_x = self.pan_y = 0
         self.update_image_display()
    
    def update_image_display(self):
        if not self.current_image:
            self.canvas.delete("all")
            self.canvas.create_text(500, 300, text="Nyiss meg egy képet a bal oldali gombbal!", fill="gray", font=("Arial", 24))
            return

        img = self.current_image.copy()

        # If image has transparency, show it with checkerboard pattern
        if self.has_transparency or (img.mode == 'RGBA' and img.getchannel('A').getextrema()[0] < 255):
            # Create checkerboard background
            checker_size = 20
            w, h = img.size
            checkerboard = Image.new('RGB', (w, h), 'white')
            draw = ImageDraw.Draw(checkerboard)
            for y in range(0, h, checker_size):
                for x in range(0, w, checker_size):
                    if (x // checker_size + y // checker_size) % 2 == 0:
                        draw.rectangle([x, y, x + checker_size, y + checker_size], fill='#CCCCCC')

          
            img = Image.alpha_composite(checkerboard.convert('RGBA'), img.convert('RGBA'))
        else:
            img = img.convert('RGBA')

       
        if self.permanent_drawings:
            if self.permanent_drawings.size == img.size:
                img = Image.alpha_composite(img, self.permanent_drawings)
            else:
                
                self.sync_drawing_layer_size()
                if self.permanent_drawings.size == img.size:
                    img = Image.alpha_composite(img, self.permanent_drawings)

        # Add current drawing overlay
        if self.draw_overlay:
            if self.draw_overlay.size == img.size:
                img = Image.alpha_composite(img, self.draw_overlay)

        img = img.convert('RGB')

        w = int(img.width * self.zoom_factor)
        h = int(img.height * self.zoom_factor)
        self.display_image = img.resize((w, h), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(self.display_image)

        self.canvas.delete("all")
        self.canvas.config(scrollregion=(0, 0, w, h))
        self.canvas.create_image(self.pan_x, self.pan_y, image=self.photo, anchor="nw")

    def on_mousewheel(self, event):
        if event.delta > 0:
            self.zoom(1.1)
        else:
            self.zoom(0.9)

    def zoom(self, factor):
        old = self.zoom_factor
        self.zoom_factor = max(0.1, min(self.zoom_factor * factor, 10))
        if self.zoom_factor != old:
            self.update_image_display()

    def save_image(self):
        if not self.current_image:
            return

      
        final_image = self.current_image.copy()

        # Merge permanent drawings if they exist
        if self.permanent_drawings:
            if final_image.mode != 'RGBA':
                final_image = final_image.convert('RGBA')
            final_image = Image.alpha_composite(final_image, self.permanent_drawings)

        # Determine file types based on transparency
        if self.has_transparency or final_image.mode == 'RGBA':
            path = filedialog.asksaveasfilename(
                defaultextension=".png", 
                filetypes=[("PNG (támogatja az átlátszóságot)", "*.png"), ("JPEG", "*.jpg")]
            )
        else:
            path = filedialog.asksaveasfilename(
                defaultextension=".png", 
                filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")]
            )

        if path:
            if path.lower().endswith('.jpg') or path.lower().endswith('.jpeg'):
                # Convert RGBA to RGB for JPEG
                if final_image.mode == 'RGBA':
                    rgb_image = Image.new('RGB', final_image.size, (255, 255, 255))
                    rgb_image.paste(final_image, mask=final_image.split()[3])
                    rgb_image.save(path, quality=95)
                else:
                    final_image.convert('RGB').save(path, quality=95)
            else:
                final_image.save(path)
            messagebox.showinfo("Mentve", f"Kép elmentve: {os.path.basename(path)}")

    def remove_background_grabcut(self):
     if not self.current_image:
         return

     # Handle drawings
     if self.permanent_drawings:
         merge = messagebox.askyesno(
             "Rajzolt elemek",
             "Van rajzolt tartalom a képen.\n\n"
             "Szeretnéd egyesíteni a rajzokat a képpel a háttér eltávolítása előtt?\n\n"
             "Igen = Rajzok megmaradnak\n"
             "Nem = Rajzok eltávolítása"
         )

         if merge:
             # Merge drawings into the image
             temp_img = self.current_image.convert('RGBA')
             temp_img = Image.alpha_composite(temp_img, self.permanent_drawings)
             self.current_image = temp_img.convert('RGB')

         # Clear drawings in both cases
         self.permanent_drawings = None
         self.update_image_display() 

     messagebox.showinfo(
         "Háttér eltávolítás - GrabCut", 
         "Húzz egy téglalapot a MEGTARTANI kívánt objektum körül!\n\n"
         "A téglalapon BELÜL lesz a főbb objektum.\n"
         "A téglalapon KÍVÜL minden eltávolításra kerül."
     )

     self.bg_removal_mode = True
     self.bg_removal_method = 'grabcut'
     self.canvas.config(cursor="crosshair")

    

    def process_grabcut_removal(self, bbox):
        """Use GrabCut algorithm for background removal"""
        self.save_state()
        try:
            
            work_image = self.current_image.copy()

            x1, y1, x2, y2 = bbox

            img = np.array(work_image)

            mask = np.zeros(img.shape[:2], np.uint8)

            bgd_model = np.zeros((1, 65), np.float64)
            fgd_model = np.zeros((1, 65), np.float64)

            rect = (x1, y1, x2 - x1, y2 - y1)

            cv2.grabCut(img, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)

            mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')

            choice = messagebox.askquestion(
                "Háttér színe",
                "Átlátszó hátteret szeretnél?\n"
                "Igen = Átlátszó\n"
                "Nem = Válassz színt"
            )

            if choice == 'yes':
                img_rgba = cv2.cvtColor(img, cv2.COLOR_RGB2RGBA)
                img_rgba[:, :, 3] = mask2 * 255
                self.current_image = Image.fromarray(img_rgba, 'RGBA')
                self.has_transparency = True
            else:
                bg_color = colorchooser.askcolor(title="Válassz háttérszínt", initialcolor="#FFFFFF")[1]
                if bg_color:
                    bg_rgb = tuple(int(bg_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

                    result = img * mask2[:, :, np.newaxis]
                    background = np.full_like(img, bg_rgb)
                    result = np.where(mask2[:, :, np.newaxis] == 1, result, background)

                    self.current_image = Image.fromarray(result.astype('uint8'))
                    self.has_transparency = False

            # Ensure drawings are cleared
            self.permanent_drawings = None

            self.update_image_display()
            messagebox.showinfo("Kész!", "Háttér sikeresen eltávolítva!")

        except Exception as e:
            messagebox.showerror("Hiba", f"GrabCut sikertelen: {e}")
    
    def extract_text(self):
        if not self.current_image:
            return
        try:
            text = pytesseract.image_to_string(self.current_image, lang='hun+eng')
            win = ctk.CTkToplevel(self)
            win.title("Kinyert szöveg (OCR)")
            win.geometry("800x600")
            txt = ctk.CTkTextbox(win, wrap="word")
            txt.pack(fill="both", expand=True, padx=10, pady=10)
            txt.insert("end", text if text.strip() else "(Nincs felismerhető szöveg)")
            win.mainloop()
        except Exception as e:
            messagebox.showerror("Hiba", f"OCR sikertelen: {e}")

    
    def apply_filter(self, func):
        if not self.current_image:
            return
        self.save_state()
        img = cv2.cvtColor(np.array(self.current_image), cv2.COLOR_RGB2BGR)
        result = func(img)
        if len(result.shape) == 2:
            result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
        self.current_image = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        self.sync_drawing_layer_size()  # Add this line
        self.update_image_display()

    def apply_grayscale(self): self.apply_filter(lambda x: cv2.cvtColor(x, cv2.COLOR_BGR2GRAY))
    def apply_blur(self): self.apply_filter(lambda x: cv2.GaussianBlur(x, (25,25), 0))
    def apply_sharpen(self): self.apply_filter(lambda x: cv2.filter2D(x, -1, np.array([[-1,-1,-1],[-1,9,-1],[-1,-1,-1]])))
    def apply_sepia(self): 
        self.apply_filter(lambda x: (cv2.transform(x, np.array([[0.272,0.534,0.131],[0.349,0.686,0.168],[0.393,0.769,0.189]], dtype=np.float32)) * 1.1).clip(0,255).astype(np.uint8))
    def apply_vintage(self): self.apply_filter(lambda x: cv2.add(x, np.random.randint(0,40,(x.shape[0],x.shape[1],3),dtype=np.uint8)))

    def rotate(self, angle):
        if self.current_image:
            self.save_state()
            self.current_image = self.current_image.rotate(-angle, expand=True)
           
            if self.permanent_drawings:
                self.permanent_drawings = self.permanent_drawings.rotate(-angle, expand=True)
            self.sync_drawing_layer_size()
            self.save_state()
            self.update_image_display()

    def flip_horizontal(self):
        if self.current_image:
            self.save_state()
            self.current_image = ImageOps.mirror(self.current_image)
            if self.permanent_drawings:
                self.permanent_drawings = ImageOps.mirror(self.permanent_drawings)
            self.update_image_display()
            
    def resize_image(self):
        if not self.current_image:
            return
        w = simpledialog.askinteger("Szélesség", f"Új szélesség (jelenleg: {self.current_image.width}):", minvalue=1)
        if not w:
            return
        h = simpledialog.askinteger("Magasság", f"Új magasság (jelenleg: {self.current_image.height}):", minvalue=1)
        if not h:
            return
        self.save_state()
        self.current_image = self.current_image.resize((w, h), Image.Resampling.LANCZOS)
        if self.permanent_drawings:
            self.permanent_drawings = self.permanent_drawings.resize((w, h), Image.Resampling.LANCZOS)
        self.update_image_display()

if __name__ == "__main__":
    app = PictureEditor()
    app.mainloop()