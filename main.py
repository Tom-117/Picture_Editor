from pathlib import Path
import customtkinter as ctk
from PIL import Image, ImageTk, ImageEnhance, ImageOps, ImageDraw, ImageFont, ImageFilter
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser, simpledialog
import cv2
import numpy as np
import pytesseract
import os
import time
import threading
import time

pytesseract.pytesseract.tesseract_cmd = 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
ctk.set_appearance_mode('dark')
ctk.set_default_color_theme('blue')

SUPPORTED_BATCH_FORMATS = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')

class PictureEditor(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title('Picture_Editor')
        self.geometry('1920x1080')
        self.minsize(1100, 650)
        self.has_transparency = False
        self.bg_color = '#808080'

        self.original_image = None
        self.current_image = None
        self.display_image = None

        self.layers = []
        self.active_layer_index = 0

        self.history = []
        self.history_index = -1

        self.zoom_factor = 1.0
        self.pan_x = self.pan_y = 0
        self.is_panning = False
        self.last_x = self.last_y = 0

        self.drawing = False
        self.draw_overlay = None
        self.draw_color = 'red'
        self.draw_size = 10
        self.tool_var = tk.StringVar(value='brush')
        self.fill_var = tk.BooleanVar(value=False)
        self.draw_enabled = tk.BooleanVar(value=False)

        self.text_mode = tk.BooleanVar(value=False)
        self.text_color = 'white'

        self.bg_removal_mode = False
        self.bg_removal_method = None
        self.bg_selection_rect = None
        self.bg_start_x = self.bg_start_y = None

        self.crop_mode = False
        self.crop_start = None
        self.crop_rect_id = None

        self.preview_adjustments = False
        self.adj_brightness = 1.0
        self.adj_contrast = 1.0
        self.adj_saturation = 1.0
        self.adj_sharpness = 1.0

        self.batch_cancel_event = None

        # Performance optimizations
        self.base_cache = None
        self.layers_dirty = True
        self.layer_panel_dirty = False
        self.adjustment_timer = None
        self.drawing_timer = None
        self.adjustment_throttle_ms = 100

        self.setup_ui()
        self.setup_bindings()
        self.update_image_display()

    def setup_ui(self):
        self.sidebar = ctk.CTkScrollableFrame(self, width=320, corner_radius=0)
        self.sidebar.pack(side='left', fill='y')

        ctk.CTkLabel(self.sidebar, text='Picture_Editor', font=ctk.CTkFont(size=22, weight='bold')).pack(pady=20)
        ctk.CTkButton(self.sidebar, text='Kép megnyitása (Ctrl+O)', command=self.open_image, height=40).pack(pady=8, padx=20, fill='x')
        ctk.CTkButton(self.sidebar, text='Mentés (Ctrl+S)', command=self.save_image, height=40).pack(pady=5, padx=20, fill='x')

        ctk.CTkLabel(self.sidebar, text='Rajzolás & Eszközök', font=ctk.CTkFont(weight='bold')).pack(pady=(25,5), anchor='w', padx=20)
        tools_scroll = ctk.CTkScrollableFrame(self.sidebar, height=90, orientation='horizontal')
        tools_scroll.pack(pady=8, padx=20, fill='x')

        row1 = ctk.CTkFrame(tools_scroll); row1.pack(pady=4)
        row2 = ctk.CTkFrame(tools_scroll); row2.pack(pady=4)

        for text, val in [('Ecset', 'brush'), ('Vonal', 'line'), ('Téglalap', 'rectangle')]:
            ctk.CTkRadioButton(row1, text=text, variable=self.tool_var, value=val).pack(side='left', padx=10)
        for text, val in [('Kör', 'circle'), ('Radír', 'eraser')]:
            ctk.CTkRadioButton(row2, text=text, variable=self.tool_var, value=val).pack(side='left', padx=10)

        opts = ctk.CTkFrame(self.sidebar)
        opts.pack(pady=8, padx=20, fill='x')
        ctk.CTkCheckBox(opts, text='Rajzolás be', variable=self.draw_enabled,
                        command=self.toggle_drawing_mode, fg_color='crimson').pack(side='left', padx=5)
        ctk.CTkButton(opts, text='Szín', width=60, command=self.choose_draw_color).pack(side='left', padx=5)
        ctk.CTkCheckBox(opts, text='Kitöltés', variable=self.fill_var).pack(side='left', padx=5)

        ctk.CTkLabel(self.sidebar, text='Eszköz méret:').pack(anchor='w', padx=30)
        self.brush_scale = ctk.CTkSlider(self.sidebar, from_=1, to=100, command=self.update_brush_size)
        self.brush_scale.pack(pady=5, padx=30, fill='x')
        self.brush_scale.set(10)
        self.brush_size_label = ctk.CTkLabel(self.sidebar, text='10 px')
        self.brush_size_label.pack(anchor='w', padx=30)

        ctk.CTkLabel(self.sidebar, text='Szöveg hozzáadása', font=ctk.CTkFont(weight='bold')).pack(pady=(25,5), anchor='w', padx=20)
        text_opts = ctk.CTkFrame(self.sidebar)
        text_opts.pack(pady=8, padx=20, fill='x')
        ctk.CTkCheckBox(text_opts, text='Szöveg mód', variable=self.text_mode,
                        command=lambda: messagebox.showinfo('Szöveg', 'Kattints a képre a szöveg elhelyezéséhez!')).pack(side='left', padx=5)
        ctk.CTkButton(text_opts, text='Szín', width=60, command=self.choose_text_color).pack(side='right', padx=5)

        self.text_input = ctk.CTkEntry(self.sidebar, placeholder_text='Ide írd a szöveget...')
        self.text_input.pack(pady=5, padx=20, fill='x')
        self.text_input.insert(0, 'Szöveg')

        ctk.CTkLabel(self.sidebar, text='Rétegek', font=ctk.CTkFont(weight='bold')).pack(pady=(25,5), anchor='w', padx=20)
        self.layers_frame = ctk.CTkScrollableFrame(self.sidebar, height=220)
        self.layers_frame.pack(pady=8, padx=20, fill='x')
        layer_controls = ctk.CTkFrame(self.sidebar)
        layer_controls.pack(pady=5, padx=20, fill='x')
        ctk.CTkButton(layer_controls, text='Réteg hozzáadása', command=self.add_layer).pack(side='left', expand=True, padx=2)
        ctk.CTkButton(layer_controls, text='Törlés', command=self.delete_layer).pack(side='left', expand=True, padx=2)
        ctk.CTkButton(layer_controls, text='Fel', command=self.move_layer_up).pack(side='left', expand=True, padx=2)
        ctk.CTkButton(layer_controls, text='Le', command=self.move_layer_down).pack(side='left', expand=True, padx=2)

        layer_controls2 = ctk.CTkFrame(self.sidebar)
        layer_controls2.pack(pady=5, padx=20, fill='x')
        ctk.CTkButton(layer_controls2, text='Merge Down', command=self.merge_down).pack(side='left', expand=True, padx=2)
        ctk.CTkButton(layer_controls2, text='Flatten All', command=self.flatten_all).pack(side='left', expand=True, padx=2)

        ctk.CTkLabel(self.sidebar, text='Ayarok / Adjustments', font=ctk.CTkFont(weight='bold')).pack(pady=(25,5), anchor='w', padx=20)
        self.adjustments_visible = True
        self.adjustments_frame = ctk.CTkFrame(self.sidebar)
        self.adjustments_frame.pack(pady=5, padx=20, fill='x')

        ctk.CTkLabel(self.adjustments_frame, text='Brightness').pack(anchor='w')
        self.adj_brightness_slider = ctk.CTkSlider(self.adjustments_frame, from_=0.1, to=3.0, number_of_steps=58,
                                                    command=lambda v: self.on_adjustment_change('brightness', v))
        self.adj_brightness_slider.pack(fill='x')

        ctk.CTkLabel(self.adjustments_frame, text='Contrast').pack(anchor='w')
        self.adj_contrast_slider = ctk.CTkSlider(self.adjustments_frame, from_=0.1, to=3.0, number_of_steps=58,
                                                  command=lambda v: self.on_adjustment_change('contrast', v))
        self.adj_contrast_slider.pack(fill='x')

        ctk.CTkLabel(self.adjustments_frame, text='Saturation').pack(anchor='w')
        self.adj_saturation_slider = ctk.CTkSlider(self.adjustments_frame, from_=0.0, to=3.0, number_of_steps=60,
                                                    command=lambda v: self.on_adjustment_change('saturation', v))
        self.adj_saturation_slider.pack(fill='x')

        ctk.CTkLabel(self.adjustments_frame, text='Sharpness').pack(anchor='w')
        self.adj_sharpness_slider = ctk.CTkSlider(self.adjustments_frame, from_=0.0, to=3.0, number_of_steps=60,
                                                   command=lambda v: self.on_adjustment_change('sharpness', v))
        self.adj_sharpness_slider.pack(fill='x')

        self.adj_brightness_slider.set(1.0)
        self.adj_contrast_slider.set(1.0)
        self.adj_saturation_slider.set(1.0)
        self.adj_sharpness_slider.set(1.0)

        adj_buttons = ctk.CTkFrame(self.sidebar)
        adj_buttons.pack(pady=5, padx=20, fill='x')
        ctk.CTkButton(adj_buttons, text='Apply Adjustments', command=self.apply_adjustments).pack(side='left', expand=True, padx=2)
        ctk.CTkButton(adj_buttons, text='Reset Sliders', command=self.reset_adjustments).pack(side='left', expand=True, padx=2)

        ctk.CTkButton(self.sidebar, text='Batch feldolgozás', command=self.open_batch_processing).pack(pady=(10,8), padx=20, fill='x')

        ctk.CTkLabel(self.sidebar, text='Átalakítás', font=ctk.CTkFont(weight='bold')).pack(pady=(20,5), anchor='w', padx=20)
        for text, cmd in [('Átméretezés', self.resize_image), ('Forgatás 90°', lambda: self.rotate(90)),
                          ('Tükrözés', self.flip_horizontal), ('Crop', self.toggle_crop_mode)]:
            ctk.CTkButton(self.sidebar, text=text, command=cmd).pack(pady=3, padx=20, fill='x')

        ctk.CTkLabel(self.sidebar, text='Szűrők', font=ctk.CTkFont(weight='bold')).pack(pady=(20,5), anchor='w', padx=20)
        for name, cmd in [('Szürke', self.apply_grayscale), ('Elmosás', self.apply_blur), ('Élesítés', self.apply_sharpen),
                          ('Szépia', self.apply_sepia), ('Vintage', self.apply_vintage)]:
            ctk.CTkButton(self.sidebar, text=name, command=cmd).pack(pady=3, padx=20, fill='x')

        ctk.CTkLabel(self.sidebar, text='Háttér eltávolítás & OCR', font=ctk.CTkFont(weight='bold')).pack(pady=(20,5), anchor='w', padx=20)
        ctk.CTkButton(self.sidebar, text='Háttér eltávolítás', command=self.remove_background_grabcut, fg_color='purple').pack(pady=8, padx=20, fill='x')
        ctk.CTkButton(self.sidebar, text='Szöveg kinyerése (OCR)', command=self.extract_text).pack(pady=5, padx=20, fill='x')

        ctk.CTkLabel(self.sidebar, text='Visszaállítás', font=ctk.CTkFont(weight='bold')).pack(pady=(20,5), anchor='w', padx=20)
        for text, cmd in [('Vissza (Ctrl+Z)', self.undo), ('Előre (Ctrl+Y)', self.redo), ('Teljes visszaállítás', self.reset_image)]:
            ctk.CTkButton(self.sidebar, text=text, command=cmd,
                          fg_color='darkred' if 'Teljes' in text else None).pack(pady=5, padx=20, fill='x')

        self.canvas = tk.Canvas(self, bg='#1e1e1e', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True, padx=10, pady=10)

        self.v_scroll = ctk.CTkScrollbar(self, command=self.canvas.yview)
        self.h_scroll = ctk.CTkScrollbar(self, orientation='horizontal', command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        self.v_scroll.pack(side='right', fill='y')
        self.h_scroll.pack(side='bottom', fill='x')

        self.refresh_layers_panel()

    

if __name__ == '__main__':
    app = PictureEditor()
    app.mainloop()