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

    def setup_bindings(self):
        self.canvas.bind('<ButtonPress-1>', self.on_click)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.canvas.bind('<ButtonPress-3>', self.on_right_click)
        self.canvas.bind('<B3-Motion>', self.on_right_drag)
        self.canvas.bind('<ButtonRelease-3>', self.on_right_release)
        self.canvas.bind('<MouseWheel>', self.on_mousewheel)
        self.canvas.bind('<Button-4>', lambda e: self.zoom(1.1))
        self.canvas.bind('<Button-5>', lambda e: self.zoom(0.9))

        self.bind('<Control-z>', lambda e: self.undo())
        self.bind('<Control-y>', lambda e: self.redo())
        self.bind('<Control-o>', lambda e: self.open_image())
        self.bind('<Control-s>', lambda e: self.save_image())
        self.bind('<Control-Shift-x>', lambda e: self.toggle_crop_mode())

    def get_drawings_layer(self):
        for idx in range(len(self.layers) - 1, 0, -1):
            if self.layers[idx].get('is_drawing_layer'):
                return self.layers[idx], idx
        for idx in range(len(self.layers) - 1, 0, -1):
            if self.layers[idx]['name'].lower().startswith('draw'):
                return self.layers[idx], idx
        return None, None

    def compose_layers(self):
        if not self.layers:
            return None
        if self.base_cache is not None and not self.layers_dirty:
            if self.draw_overlay:
                overlay = self.draw_overlay
                if overlay.size != self.base_cache.size:
                    overlay = overlay.resize(self.base_cache.size, Image.Resampling.BILINEAR)
                return Image.alpha_composite(self.base_cache, overlay)
            else:
                return self.base_cache
        # recompose base
        base = self.layers[0]['image'].copy()
        if self.preview_adjustments:
            base = self.apply_adjustments_to_image(base)
        composited = base.convert('RGBA')
        for layer in self.layers[1:]:
            if not layer['visible']:
                continue
            top = layer['image']
            if top.size != composited.size:
                top = top.resize(composited.size, Image.Resampling.BILINEAR)
            composited = self.blend_images(composited, top, layer['blend_mode'], layer['opacity'])
        self.base_cache = composited
        self.layers_dirty = False
        if self.draw_overlay:
            overlay = self.draw_overlay
            if overlay.size != composited.size:
                overlay = overlay.resize(composited.size, Image.Resampling.BILINEAR)
            return Image.alpha_composite(composited, overlay)
        else:
            return composited

    def blend_images(self, base_img, top_img, mode='normal', opacity=1.0):
        base_arr = np.array(base_img.convert('RGBA')).astype(np.float32)
        top_arr = np.array(top_img.convert('RGBA')).astype(np.float32)
        if opacity < 1.0:
            top_arr[..., 3] = top_arr[..., 3] * opacity
        A = base_arr[..., :3]
        B = top_arr[..., :3]
        if mode == 'multiply':
            C = (A * B) / 255.0
        elif mode == 'screen':
            C = 255.0 - ((255.0 - A) * (255.0 - B) / 255.0)
        elif mode == 'overlay':
            mask = A <= 128
            C = np.zeros_like(A)
            C[mask] = (2 * A[mask] * B[mask] / 255.0)
            C[~mask] = 255.0 - (2 * (255.0 - A[~mask]) * (255.0 - B[~mask]) / 255.0)
        else:
            C = B
        aA = base_arr[..., 3] / 255.0
        aB = top_arr[..., 3] / 255.0
        aOut = aB + aA * (1 - aB)
        out_rgb = np.zeros_like(A)
        nz = aOut > 0
        out_rgb[nz] = ((C * aB[..., None] + A * aA[..., None] * (1 - aB[..., None]))[nz] / aOut[nz, None])
        out_rgb[~nz] = 0
        out_alpha = (aOut * 255.0).clip(0,255)
        out = np.dstack((out_rgb, out_alpha))
        out = np.clip(out, 0, 255).astype(np.uint8)
        return Image.fromarray(out, mode='RGBA')

    def refresh_layers_panel(self):
        # Skip refresh if nothing changed
        if not self.layer_panel_dirty and self.layers_frame.winfo_children():
            return
        for widget in self.layers_frame.winfo_children():
            widget.destroy()
        if not self.layers:
            return
        self.layer_panel_dirty = False
        for idx in range(len(self.layers) - 1, -1, -1):
            layer = self.layers[idx]
            row = ctk.CTkFrame(self.layers_frame)
            row.pack(fill='x', pady=2, padx=2)
            if idx == self.active_layer_index:
                row.configure(fg_color='#333333')
            name_btn = ctk.CTkButton(row, text=layer['name'], width=100,
                                     command=lambda i=idx: self.set_active_layer(i))
            name_btn.pack(side='left', padx=2)
            vis_var = tk.BooleanVar(value=layer['visible'])
            ctk.CTkCheckBox(row, text='', variable=vis_var,
                            command=lambda i=idx, v=vis_var: self.set_layer_visibility(i, v.get())).pack(side='left', padx=2)
            opacity_var = tk.DoubleVar(value=layer['opacity'] * 100)
            ctk.CTkSlider(row, from_=0, to=100, number_of_steps=100,
                          variable=opacity_var,
                          command=lambda v, i=idx: self.set_layer_opacity(i, float(v)/100)).pack(side='left', fill='x', expand=True, padx=2)
            blend = ctk.CTkOptionMenu(row, values=['normal', 'multiply', 'screen', 'overlay'],
                                      command=lambda m, i=idx: self.set_layer_blend_mode(i, m))
            blend.set(layer.get('blend_mode', 'normal'))
            blend.pack(side='left', padx=2)

    def set_layer_visibility(self, index, visible):
        self.layers[index]['visible'] = visible
        self.layers_dirty = True
        self.layer_panel_dirty = True
        self.save_state()
        self.update_image_display()
        self.refresh_layers_panel()

    def set_layer_opacity(self, index, opacity):
        self.layers[index]['opacity'] = float(opacity)
        self.layers_dirty = True
        self.save_state()
        self.update_image_display()

    def set_layer_blend_mode(self, index, mode):
        if mode in ['normal', 'multiply', 'screen', 'overlay']:
            self.layers[index]['blend_mode'] = mode
            self.layers_dirty = True
            self.save_state()
            self.update_image_display()

    def set_active_layer(self, index):
        self.active_layer_index = index
        self.refresh_layers_panel()

    def add_layer(self):
        if not self.layers:
            return
        name = simpledialog.askstring('Új réteg', 'Réteg neve:')
        if not name:
            name = f'Réteg {len(self.layers)}'
        size = self.layers[0]['image'].size
        new_layer = {
            'name': name,
            'image': Image.new('RGBA', size, (0, 0, 0, 0)),
            'visible': True,
            'opacity': 1.0,
            'blend_mode': 'normal',
            'is_drawing_layer': False
        }
        self.layers.append(new_layer)
        self.active_layer_index = len(self.layers) - 1
        self.layers_dirty = True
        self.layer_panel_dirty = True
        self.save_state()
        self.update_image_display()
        self.refresh_layers_panel()

    def delete_layer(self):
        if self.active_layer_index == 0:
            messagebox.showwarning('Figyelem', 'A háttérréteg nem törölhető.')
            return
        del self.layers[self.active_layer_index]
        self.active_layer_index = max(0, self.active_layer_index - 1)
        self.layers_dirty = True
        self.layer_panel_dirty = True
        self.save_state()
        self.update_image_display()
        self.refresh_layers_panel()

    def move_layer_up(self):
        idx = self.active_layer_index
        if idx <= 1:
            return
        self.layers[idx], self.layers[idx - 1] = self.layers[idx - 1], self.layers[idx]
        self.active_layer_index = idx - 1
        self.layers_dirty = True
        self.layer_panel_dirty = True
        self.save_state()
        self.update_image_display()
        self.refresh_layers_panel()

    def move_layer_down(self):
        idx = self.active_layer_index
        if idx >= len(self.layers) - 1 or idx == 0:
            return
        self.layers[idx], self.layers[idx + 1] = self.layers[idx + 1], self.layers[idx]
        self.active_layer_index = idx + 1
        self.layers_dirty = True
        self.layer_panel_dirty = True
        self.save_state()
        self.update_image_display()
        self.refresh_layers_panel()

    def merge_down(self):
        idx = self.active_layer_index
        if idx == 0 or idx >= len(self.layers):
            return
        bottom = self.layers[idx - 1]
        top = self.layers[idx]
        if top['visible']:
            bottom['image'] = self.blend_images(bottom['image'], top['image'], top['blend_mode'], top['opacity'])
        del self.layers[idx]
        self.active_layer_index = idx - 1
        self.layers_dirty = True
        self.layer_panel_dirty = True
        self.save_state()
        self.update_image_display()
        self.refresh_layers_panel()

    def flatten_all(self):
        if not self.layers:
            return
        base = self.layers[0]['image'].copy()
        for layer in self.layers[1:]:
            if layer['visible']:
                base = self.blend_images(base, layer['image'], layer['blend_mode'], layer['opacity'])
        self.layers = [
            {'name': 'Background', 'image': base, 'visible': True, 'opacity': 1.0, 'blend_mode': 'normal', 'is_drawing_layer': False},
            {'name': 'Drawings', 'image': Image.new('RGBA', base.size, (0,0,0,0)), 'visible': True, 'opacity': 1.0, 'blend_mode': 'normal', 'is_drawing_layer': True}
        ]
        self.active_layer_index = 0
        self.layers_dirty = True
        self.layer_panel_dirty = True
        self.save_state()
        self.update_image_display()
        self.refresh_layers_panel()

    def update_brush_size(self, val):
        self.draw_size = int(float(val))
        self.brush_size_label.configure(text=f'{self.draw_size} px')

    def choose_draw_color(self):
        color = colorchooser.askcolor(title='Válassz ecset/szöveg színt')[1]
        if color:
            self.draw_color = color

    def choose_text_color(self):
        color = colorchooser.askcolor(title='Szöveg színe')[1]
        if color:
            self.text_color = color

    def create_initial_layers(self):
        if not self.current_image:
            return
        base_rgb = self.current_image.convert('RGBA')
        draw_layer = Image.new('RGBA', base_rgb.size, (0,0,0,0))
        self.layers = [
            {'name': 'Background', 'image': base_rgb, 'visible': True, 'opacity': 1.0, 'blend_mode': 'normal', 'is_drawing_layer': False},
            {'name': 'Drawings', 'image': draw_layer, 'visible': True, 'opacity': 1.0, 'blend_mode': 'normal', 'is_drawing_layer': True}
        ]
        self.active_layer_index = 0
        self.refresh_layers_panel()

    def save_state(self):
        if not self.layers:
            return
        self.history = self.history[:self.history_index + 1]
        layers_copy = []
        for layer in self.layers:
            layers_copy.append({
                'name': layer['name'],
                'image': layer['image'].copy(),
                'visible': layer['visible'],
                'opacity': layer['opacity'],
                'blend_mode': layer['blend_mode'],
                'is_drawing_layer': layer.get('is_drawing_layer', False)
            })
        state = {
            'layers': layers_copy,
            'active_layer_index': self.active_layer_index,
            'has_transparency': self.has_transparency,
            'adj_brightness': self.adj_brightness,
            'adj_contrast': self.adj_contrast,
            'adj_saturation': self.adj_saturation,
            'adj_sharpness': self.adj_sharpness
        }
        self.history.append(state)
        self.history_index += 1
        if len(self.history) > 30:
            self.history.pop(0)
            self.history_index -= 1

    def undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.load_state(self.history[self.history_index])

    def redo(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.load_state(self.history[self.history_index])

    def load_state(self, state):
        if not state:
            return
        self.layers = []
        for layer in state.get('layers', []):
            self.layers.append({
                'name': layer['name'],
                'image': layer['image'].copy(),
                'visible': layer['visible'],
                'opacity': layer['opacity'],
                'blend_mode': layer['blend_mode'],
                'is_drawing_layer': layer.get('is_drawing_layer', False)
            })
        self.active_layer_index = state.get('active_layer_index', 0)
        self.has_transparency = state.get('has_transparency', False)
        self.adj_brightness = state.get('adj_brightness', 1.0)
        self.adj_contrast = state.get('adj_contrast', 1.0)
        self.adj_saturation = state.get('adj_saturation', 1.0)
        self.adj_sharpness = state.get('adj_sharpness', 1.0)
        self.current_image = self.layers[0]['image'].copy() if self.layers else None
        self.refresh_layers_panel()
        self.update_image_display()
    
    def reset_image(self):
        if self.original_image:
            self.current_image = self.original_image.copy()
            self.has_transparency = False
            self.create_initial_layers()
            self.history = []
            self.history_index = -1
            self.save_state()
            self.zoom_factor = 1.0
            self.pan_x = self.pan_y = 0
            self.update_image_display()

    def open_image(self):
        path = filedialog.askopenfilename(filetypes=[('Képek', '*.png *.jpg *.jpeg *.bmp *.tiff *.webp')])
        if path:
            try:
                self.original_image = Image.open(path).convert('RGB')
                self.current_image = self.original_image.copy()
                self.has_transparency = False
                self.create_initial_layers()
                self.history = []
                self.history_index = -1
                self.save_state()
                self.zoom_factor = 1.0
                self.pan_x = self.pan_y = 0
                self.update_image_display()
                messagebox.showinfo('Siker!', 'Kép betöltve!')
            except Exception as e:
                messagebox.showerror('Hiba', f'Nem sikerült betölteni: {e}')

    def update_image_display(self):
        self.canvas.delete('all')
        if not self.layers:
            self.canvas.create_text(500, 300, text='Nyiss meg egy képet a bal oldali gombbal!', fill='gray', font=('Arial', 24))
            return
        composed = self.compose_layers()
        if composed is None:
            return
        if composed.mode != 'RGBA':
            composed = composed.convert('RGBA')
        if not self.has_transparency and composed.mode == 'RGBA':
            if composed.getchannel('A').getextrema()[0] < 255:
                self.has_transparency = True
        display = composed.convert('RGB')
        w = int(display.width * self.zoom_factor)
        h = int(display.height * self.zoom_factor)
        if w < 1 or h < 1:
            return
        # Use BILINEAR for preview (faster), LANCZOS only for exports
        resample = Image.Resampling.BILINEAR if self.zoom_factor != 1.0 else Image.Resampling.LANCZOS
        self.display_image = display.resize((w, h), resample)
        self.photo = ImageTk.PhotoImage(self.display_image)
        self.canvas.config(scrollregion=(0, 0, w, h))
        self.canvas.create_image(self.pan_x, self.pan_y, image=self.photo, anchor='nw')

    def on_right_click(self, event):
        self.is_panning = True
        self.last_x = event.x
        self.last_y = event.y
        self.canvas.config(cursor='fleur')

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
        self.canvas.config(cursor='')

    def on_click(self, event):
        if not self.layers:
            return
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        img_x = (canvas_x - self.pan_x) / self.zoom_factor
        img_y = (canvas_y - self.pan_y) / self.zoom_factor
        if self.crop_mode:
            self.crop_start = (img_x, img_y)
            self.crop_rect_id = None
            return
        if self.text_mode.get():
            self.place_text_at(img_x, img_y)
            return
        if not self.draw_enabled.get():
            return
        tool = self.tool_var.get()
        self.draw_overlay = Image.new('RGBA', self.layers[0]['image'].size, (0, 0, 0, 0))
        self.current_draw = ImageDraw.Draw(self.draw_overlay)
        self.start_x = img_x
        self.start_y = img_y
        self.last_x = img_x
        self.last_y = img_y
        if tool == 'brush':
            self.current_draw.ellipse([img_x - self.draw_size/2, img_y - self.draw_size/2, img_x + self.draw_size/2, img_y + self.draw_size/2], fill=self.draw_color)
        elif tool == 'eraser':
            self.current_draw.ellipse([img_x - self.draw_size/2, img_y - self.draw_size/2, img_x + self.draw_size/2, img_y + self.draw_size/2], fill=(0, 0, 0, 0))
        self.update_image_display()

    def on_drag(self, event):
        if not self.layers:
            return
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        img_x = (canvas_x - self.pan_x) / self.zoom_factor
        img_y = (canvas_y - self.pan_y) / self.zoom_factor
        if self.crop_mode and self.crop_start:
            x1, y1 = self.crop_start
            x2, y2 = img_x, img_y
            if self.crop_rect_id:
                self.canvas.delete(self.crop_rect_id)
            self.crop_rect_id = self.canvas.create_rectangle(x1 * self.zoom_factor + self.pan_x,
                                                              y1 * self.zoom_factor + self.pan_y,
                                                              x2 * self.zoom_factor + self.pan_x,
                                                              y2 * self.zoom_factor + self.pan_y,
                                                              dash=(6,4), outline='yellow')
            return
        if not self.draw_enabled.get():
            return
        tool = self.tool_var.get()
        if tool == 'brush':
            self.current_draw.line([self.last_x, self.last_y, img_x, img_y], fill=self.draw_color, width=self.draw_size)
            self.current_draw.ellipse([img_x - self.draw_size/2, img_y - self.draw_size/2,
                                       img_x + self.draw_size/2, img_y + self.draw_size/2], fill=self.draw_color)
            self.last_x = img_x
            self.last_y = img_y
        elif tool == 'eraser':
            self.current_draw.line([self.last_x, self.last_y, img_x, img_y], fill=(0, 0, 0, 0), width=self.draw_size)
            self.current_draw.ellipse([img_x - self.draw_size/2, img_y - self.draw_size/2,
                                       img_x + self.draw_size/2, img_y + self.draw_size/2], fill=(0, 0, 0, 0))
            self.last_x = img_x
            self.last_y = img_y
        self.update_image_display()

    def on_release(self, event):
        if not self.layers:
            return
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        img_x = (canvas_x - self.pan_x) / self.zoom_factor
        img_y = (canvas_y - self.pan_y) / self.zoom_factor
        if self.crop_mode and self.crop_start:
            x1, y1 = self.crop_start
            x2, y2 = img_x, img_y
            self.canvas.delete(self.crop_rect_id)
            self.crop_rect_id = None
            self.crop_mode = False
            if messagebox.askyesno('Crop', 'Crop to this region?'):
                x1i = int(max(0, min(x1, x2)))
                y1i = int(max(0, min(y1, y2)))
                x2i = int(min(self.layers[0]['image'].width, max(x1, x2)))
                y2i = int(min(self.layers[0]['image'].height, max(y1, y2)))
                if x2i > x1i and y2i > y1i:
                    self.save_state()
                    for layer in self.layers:
                        layer['image'] = layer['image'].crop((x1i, y1i, x2i, y2i))
                    self.layers_dirty = True
                    self.current_image = self.layers[0]['image'].copy()
                    self.zoom_factor = 1.0
                    self.pan_x = self.pan_y = 0
                    self.update_image_display()
            self.crop_start = None
            return
        if self.text_mode.get():
            return
        if not self.draw_enabled.get():
            return
        tool = self.tool_var.get()
        if tool in ['brush', 'line', 'rectangle', 'circle', 'eraser'] and self.draw_overlay is not None:
            if tool == 'line':
                self.current_draw.line([self.start_x, self.start_y, img_x, img_y], fill=self.draw_color, width=self.draw_size)
            elif tool == 'rectangle':
                fill_color = self.draw_color if self.fill_var.get() else None
                self.current_draw.rectangle([self.start_x, self.start_y, img_x, img_y], outline=self.draw_color,
                                            width=self.draw_size, fill=fill_color)
            elif tool == 'circle':
                fill_color = self.draw_color if self.fill_var.get() else None
                self.current_draw.ellipse([self.start_x, self.start_y, img_x, img_y], outline=self.draw_color,
                                          width=self.draw_size, fill=fill_color)
            self.finalize_drawing()

    def finalize_drawing(self):
        if self.draw_overlay is None:
            return
        layer, idx = self.get_drawings_layer()
        if layer is None:
            self.create_initial_layers()
            layer, idx = self.get_drawings_layer()
        if layer is None:
            return
        layer['image'] = Image.alpha_composite(layer['image'], self.draw_overlay)
        self.draw_overlay = None
        self.layers_dirty = True
        self.save_state()
        self.update_image_display()

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
        # Add to active layer
        layer = self.layers[self.active_layer_index]
        overlay = Image.new("RGBA", layer['image'].size, (0,0,0,0))
        draw = ImageDraw.Draw(overlay)
        fill_color = self.text_color
        if isinstance(fill_color, str) and fill_color.startswith('#') and len(fill_color) == 7:
            fill_color += 'FF'
        draw.text((x, y), text, font=font, fill=fill_color,
                  stroke_width=2, stroke_fill="black", anchor="mm")
        layer['image'] = Image.alpha_composite(layer['image'], overlay)
        self.layers_dirty = True
        self.save_state()
        self.update_image_display()

    def toggle_drawing_mode(self):
        self.drawing = self.draw_enabled.get()
        if self.drawing:
            tool_names = {'brush': 'Ecset', 'line': 'Vonal', 'rectangle': 'Téglalap', 'circle': 'Kör', 'eraser': 'Radír'}
            tool = tool_names.get(self.tool_var.get(), 'Eszköz')
            messagebox.showinfo('Rajzolás aktív!', f'{tool} mód bekapcsolva!\nBal kattintás + húzás: rajzolás\nJobb kattintás: mozgatás (pan)')

    def toggle_crop_mode(self):
        self.crop_mode = not self.crop_mode
        self.canvas.config(cursor='crosshair' if self.crop_mode else '')
        msg = 'Crop mode aktív' if self.crop_mode else 'Crop mode kikapcsolva'
        messagebox.showinfo('Crop', msg)

    def apply_filter(self, func):
        if not self.layers:
            return
        self.save_state()
        bg = self.layers[0]['image'].convert('RGB')
        arr = cv2.cvtColor(np.array(bg), cv2.COLOR_RGB2BGR)
        result = func(arr)
        if len(result.shape) == 2:
            result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
        self.layers[0]['image'] = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB)).convert('RGBA')
        self.layers_dirty = True
        self.current_image = self.layers[0]['image'].copy()
        self.update_image_display()

    def apply_grayscale(self):
        self.apply_filter(lambda x: cv2.cvtColor(x, cv2.COLOR_BGR2GRAY))

    def apply_blur(self):
        self.apply_filter(lambda x: cv2.GaussianBlur(x, (25, 25), 0))

    def apply_sharpen(self):
        self.apply_filter(lambda x: cv2.filter2D(x, -1, np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]], np.float32)))

    def apply_sepia(self):
        self.apply_filter(lambda x: (cv2.transform(x, np.array([[0.272, 0.534, 0.131], [0.349, 0.686, 0.168], [0.393, 0.769, 0.189]], np.float32)) * 1.1).clip(0,255).astype(np.uint8))

    def apply_vintage(self):
        self.apply_filter(lambda x: cv2.add(x, np.random.randint(0, 40, (x.shape[0], x.shape[1], 3), dtype=np.uint8)))

    def rotate(self, angle):
        if not self.layers:
            return
        self.save_state()
        for layer in self.layers:
            layer['image'] = layer['image'].rotate(-angle, expand=True)
        self.layers_dirty = True
        self.current_image = self.layers[0]['image'].copy()
        self.zoom_factor = 1.0
        self.pan_x = self.pan_y = 0
        self.update_image_display()

    def flip_horizontal(self):
        if not self.layers:
            return
        self.save_state()
        for layer in self.layers:
            layer['image'] = ImageOps.mirror(layer['image'])
        self.layers_dirty = True
        self.current_image = self.layers[0]['image'].copy()
        self.update_image_display()

    def resize_image(self):
        if not self.layers:
            return
        w = simpledialog.askinteger('Szélesség', f"Új szélesség (jelenleg: {self.layers[0]['image'].width}):", minvalue=1)
        if not w:
            return
        h = simpledialog.askinteger('Magasság', f"Új magasság (jelenleg: {self.layers[0]['image'].height}):", minvalue=1)
        if not h:
            return
        self.save_state()
        for layer in self.layers:
            layer['image'] = layer['image'].resize((w, h), Image.Resampling.LANCZOS)
        self.layers_dirty = True
        self.current_image = self.layers[0]['image'].copy()
        self.update_image_display()

    def save_image(self):
        if not self.layers:
            return
        final_image = self.compose_layers()
        if final_image is None:
            return
        path = filedialog.asksaveasfilename(defaultextension='.png', filetypes=[('PNG', '*.png'), ('JPEG', '*.jpg')])
        if not path:
            return
        # Use LANCZOS for high-quality exports
        w = int(final_image.width)
        h = int(final_image.height)
        if w > 0 and h > 0:
            final_image = final_image.resize((w, h), Image.Resampling.LANCZOS)
        
        if path.lower().endswith(('.jpg', '.jpeg')):
            final_image.convert('RGB').save(path, quality=95)
        else:
            final_image.save(path)
        messagebox.showinfo('Mentve', f'Kép elmentve: {os.path.basename(path)}')

    def remove_background_grabcut(self):
        if not self.layers:
            return
        draw_layer, _ = self.get_drawings_layer()
        if draw_layer:
            merge = messagebox.askyesno('Rajzolt elemek', 'Van rajzolt tartalom a képen.\n\nSzeretnéd egyesíteni a rajzokat a képpel a háttér eltávolítása előtt?\n\nIgen = Rajzok megmaradnak\nNem = Rajzok eltávolítása')
            if merge:
                self.layers[0]['image'] = Image.alpha_composite(self.layers[0]['image'].convert('RGBA'), draw_layer['image']).convert('RGBA')
            draw_layer['image'] = Image.new('RGBA', self.layers[0]['image'].size, (0,0,0,0))
        messagebox.showinfo('Háttér eltávolítás - GrabCut', 'Húzz egy téglalapot a MEGTARTANI kívánt objektum körül!\n\nA téglalapon BELÜL lesz a főbb objektum.\nA téglalapon KÍVÜL minden eltávolításra kerül.')
        self.bg_removal_mode = True
        self.bg_removal_method = 'grabcut'
        self.canvas.config(cursor='crosshair')

    def process_grabcut_removal(self, bbox):
        if not self.layers:
            return
        # Run GrabCut in background thread to prevent UI blocking
        def grabcut_thread():
            try:
                x1, y1, x2, y2 = bbox
                img = np.array(self.layers[0]['image'].convert('RGB'))
                mask = np.zeros(img.shape[:2], np.uint8)
                bgd_model = np.zeros((1, 65), np.float64)
                fgd_model = np.zeros((1, 65), np.float64)
                rect = (x1, y1, x2-x1, y2-y1)
                cv2.grabCut(img, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
                mask2 = np.where((mask==2)|(mask==0), 0, 1).astype('uint8')
                self.after(0, lambda: self._finalize_grabcut(img, mask2))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror('Hiba', f'GrabCut sikertelen: {e}'))
        
        self.save_state()
        threading.Thread(target=grabcut_thread, daemon=True).start()
    
    def _finalize_grabcut(self, img, mask2):
        choice = messagebox.askquestion('Háttér színe', 'Átlátszó hátteret szeretnél?\nIgen = Átlátszó\nNem = Válassz színt')
        if choice == 'yes':
            img_rgba = cv2.cvtColor(img, cv2.COLOR_RGB2RGBA)
            img_rgba[..., 3] = mask2*255
            self.layers[0]['image'] = Image.fromarray(img_rgba, 'RGBA')
            self.has_transparency = True
        else:
            bg_color = colorchooser.askcolor(title='Válassz háttérszínt', initialcolor='#FFFFFF')[1]
            if bg_color:
                bg_rgb = tuple(int(bg_color.lstrip('#')[i:i+2], 16) for i in (0,2,4))
                result = img * mask2[..., None]
                background = np.full_like(img, bg_rgb)
                result = np.where(mask2[..., None] == 1, result, background)
                self.layers[0]['image'] = Image.fromarray(result.astype('uint8'))
                self.has_transparency = False
        draw_layer, _ = self.get_drawings_layer()
        if draw_layer:
            draw_layer['image'] = Image.new('RGBA', self.layers[0]['image'].size, (0,0,0,0))
        self.current_image = self.layers[0]['image'].copy()
        self.layers_dirty = True
        self.update_image_display()
        messagebox.showinfo('Kész!', 'Háttér sikeresen eltávolítva!')

    def extract_text(self):
        if not self.layers:
            return
        # Run OCR in background thread to prevent UI blocking
        def ocr_thread():
            try:
                img = self.compose_layers().convert('RGB')
                text = pytesseract.image_to_string(img, lang='hun+eng')
                self.after(0, lambda: self._show_ocr_result(text))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror('Hiba', f'OCR sikertelen: {e}'))
        
        threading.Thread(target=ocr_thread, daemon=True).start()
    
    def _show_ocr_result(self, text):
        win = ctk.CTkToplevel(self)
        win.title('Kinyert szöveg (OCR)')
        win.geometry('800x600')
        txt = ctk.CTkTextbox(win, wrap='word')
        txt.pack(fill='both', expand=True, padx=10, pady=10)
        txt.insert('end', text if text.strip() else '(Nincs felismerhető szöveg)')
        win.mainloop()

    def on_adjustment_change(self, name, value):
        setattr(self, f'adj_{name}', float(value))
        self.preview_adjustments = True
        self.layers_dirty = True
        
        # Throttle preview updates to avoid excessive recomputing
        if self.adjustment_timer is not None:
            self.after_cancel(self.adjustment_timer)
        
        self.adjustment_timer = self.after(self.adjustment_throttle_ms, self.update_image_display)

    def apply_adjustments_to_image(self, base_img):
        img = base_img.convert('RGB')
        img = ImageEnhance.Brightness(img).enhance(self.adj_brightness)
        img = ImageEnhance.Contrast(img).enhance(self.adj_contrast)
        img = ImageEnhance.Color(img).enhance(self.adj_saturation)
        img = ImageEnhance.Sharpness(img).enhance(self.adj_sharpness)
        return img.convert('RGBA')

    def apply_adjustments(self):
        if not self.layers:
            return
        self.save_state()
        self.layers[0]['image'] = self.apply_adjustments_to_image(self.layers[0]['image'])
        self.current_image = self.layers[0]['image'].copy()
        self.preview_adjustments = False
        self.layers_dirty = True
        self.update_image_display()

    def reset_adjustments(self):
        self.adj_brightness = 1.0
        self.adj_contrast = 1.0
        self.adj_saturation = 1.0
        self.adj_sharpness = 1.0
        self.adj_brightness_slider.set(1.0)
        self.adj_contrast_slider.set(1.0)
        self.adj_saturation_slider.set(1.0)
        self.adj_sharpness_slider.set(1.0)
        self.preview_adjustments = False
        self.update_image_display()

    def open_batch_processing(self):
        win = ctk.CTkToplevel(self)
        win.title('Batch Processing')
        win.geometry('500x700')
        win.transient(self)
        win.lift()
        win.focus_force()
        win.after(100, lambda: win.lift())
        win.after(100, lambda: win.focus_force())

        scrollable_frame = ctk.CTkScrollableFrame(win)
        scrollable_frame.pack(fill='both', expand=True, padx=10, pady=10)

        input_path_var = tk.StringVar()
        output_path_var = tk.StringVar()

        def choose_input():
            p = filedialog.askdirectory()
            if p:
                input_path_var.set(p)

        def choose_output():
            p = filedialog.askdirectory()
            if p:
                output_path_var.set(p)

        ctk.CTkButton(scrollable_frame, text='Input mappa', command=choose_input).pack(pady=5, padx=10, fill='x')
        ctk.CTkLabel(scrollable_frame, textvariable=input_path_var, wraplength=460).pack(pady=2, padx=10)
        ctk.CTkButton(scrollable_frame, text='Output mappa', command=choose_output).pack(pady=5, padx=10, fill='x')
        ctk.CTkLabel(scrollable_frame, textvariable=output_path_var, wraplength=460).pack(pady=2, padx=10)

        ops = ['Grayscale', 'Blur', 'Sharpen', 'Sepia', 'Vintage', 'Resize', 'Rotate', 'Flip Horizontal', 'Brightness', 'Contrast']
        op_vars = {op: tk.BooleanVar(value=False) for op in ops}
        ops_frame = ctk.CTkScrollableFrame(scrollable_frame, height=180)
        ops_frame.pack(pady=5, padx=10, fill='x')
        for op in ops:
            ctk.CTkCheckBox(ops_frame, text=op, variable=op_vars[op]).pack(anchor='w', padx=5, pady=2)

        self.batch_blur_kernel = tk.IntVar(value=3)
        blur_frame = ctk.CTkFrame(scrollable_frame)
        blur_frame.pack(pady=5, padx=10, fill='x')
        ctk.CTkLabel(blur_frame, text='Blur kernel').pack(anchor='w')
        blur_label = ctk.CTkLabel(blur_frame, text='3')
        blur_label.pack(anchor='e')
        ctk.CTkSlider(scrollable_frame, from_=3, to=51, number_of_steps=24,
                      command=lambda v: [self.batch_blur_kernel.set(int(max(3, int(float(v)) | 1))), blur_label.configure(text=str(int(max(3, int(float(v)) | 1))))]).pack(fill='x', padx=10)

        self.batch_resize_width = tk.IntVar(value=800)
        self.batch_resize_height = tk.IntVar(value=600)
        rfrm = ctk.CTkFrame(scrollable_frame)
        rfrm.pack(pady=5, padx=10, fill='x')
        ctk.CTkLabel(rfrm, text='Width').pack(side='left', padx=5)
        ctk.CTkEntry(rfrm, textvariable=self.batch_resize_width, width=80).pack(side='left', padx=5)
        ctk.CTkLabel(rfrm, text='Height').pack(side='left', padx=5)
        ctk.CTkEntry(rfrm, textvariable=self.batch_resize_height, width=80).pack(side='left', padx=5)

        self.batch_rotate = tk.StringVar(value='90')
        ctk.CTkOptionMenu(scrollable_frame, values=['90', '180', '270'], variable=self.batch_rotate).pack(pady=5, padx=10, fill='x')

        self.batch_brightness = tk.DoubleVar(value=1.0)
        brightness_frame = ctk.CTkFrame(scrollable_frame)
        brightness_frame.pack(pady=5, padx=10, fill='x')
        ctk.CTkLabel(brightness_frame, text='Brightness').pack(anchor='w')
        brightness_label = ctk.CTkLabel(brightness_frame, text='1.00')
        brightness_label.pack(anchor='e')
        ctk.CTkSlider(scrollable_frame, from_=0.1, to=3.0, number_of_steps=58, variable=self.batch_brightness,
                      command=lambda v: brightness_label.configure(text=f'{float(v):.2f}')).pack(fill='x', padx=10)

        self.batch_contrast = tk.DoubleVar(value=1.0)
        contrast_frame = ctk.CTkFrame(scrollable_frame)
        contrast_frame.pack(pady=5, padx=10, fill='x')
        ctk.CTkLabel(contrast_frame, text='Contrast').pack(anchor='w')
        contrast_label = ctk.CTkLabel(contrast_frame, text='1.00')
        contrast_label.pack(anchor='e')
        ctk.CTkSlider(scrollable_frame, from_=0.1, to=3.0, number_of_steps=58, variable=self.batch_contrast,
                      command=lambda v: contrast_label.configure(text=f'{float(v):.2f}')).pack(fill='x', padx=10)

        self.batch_output_format = tk.StringVar(value='PNG')
        fmt_frame = ctk.CTkFrame(scrollable_frame)
        fmt_frame.pack(pady=5, padx=10, fill='x')
        ctk.CTkRadioButton(fmt_frame, text='PNG', variable=self.batch_output_format, value='PNG').pack(side='left', padx=5)
        ctk.CTkRadioButton(fmt_frame, text='JPEG', variable=self.batch_output_format, value='JPEG').pack(side='left', padx=5)

        self.batch_quality = tk.IntVar(value=90)
        ctk.CTkLabel(scrollable_frame, text='Quality').pack(anchor='w', padx=10)
        ctk.CTkSlider(scrollable_frame, from_=60, to=100, number_of_steps=40, variable=self.batch_quality).pack(fill='x', padx=10)

        self.batch_progress = ctk.CTkProgressBar(scrollable_frame)
        self.batch_progress.pack(pady=5, padx=10, fill='x')
        self.batch_status = ctk.CTkLabel(scrollable_frame, text='Készen áll')
        self.batch_status.pack(pady=2, padx=10)

        self.batch_result_box = ctk.CTkTextbox(scrollable_frame, height=120)
        self.batch_result_box.pack(pady=5, padx=10, fill='both', expand=True)

        def run_batch():
            input_dir = input_path_var.get().strip()
            output_dir = output_path_var.get().strip()
            if not input_dir or not output_dir:
                messagebox.showwarning('Hiba', 'Kérjük válassz input és output mappát.')
                return
            files = [os.path.join(input_dir, f) for f in os.listdir(input_dir)
                     if os.path.splitext(f)[1].lower() in SUPPORTED_BATCH_FORMATS]
            if not files:
                messagebox.showinfo('Hiba', 'Nincs feldolgozható fájl a mappában.')
                return
            self.batch_cancel_event = threading.Event()
            self.batch_progress.set(0)
            self.batch_result_box.delete('0.0', 'end')
            def process_file(file_path, index, total):
                try:
                    img = Image.open(file_path).convert('RGB')
                    if op_vars['Grayscale'].get():
                        img = ImageOps.grayscale(img).convert('RGB')
                    if op_vars['Blur'].get():
                        k = self.batch_blur_kernel.get() or 3
                        if k % 2 == 0:
                            k += 1
                        img = img.filter(ImageFilter.GaussianBlur(radius=(k-1)/2))
                    if op_vars['Sharpen'].get():
                        img = ImageEnhance.Sharpness(img).enhance(2.0)
                    if op_vars['Sepia'].get():
                        sep = np.array(img)
                        tr = (sep[...,0]*0.393 + sep[...,1]*0.769 + sep[...,2]*0.189)
                        tg = (sep[...,0]*0.349 + sep[...,1]*0.686 + sep[...,2]*0.168)
                        tb = (sep[...,0]*0.272 + sep[...,1]*0.534 + sep[...,2]*0.131)
                        sep = np.stack([np.clip(tr,0,255), np.clip(tg,0,255), np.clip(tb,0,255)], axis=2).astype(np.uint8)
                        img = Image.fromarray(sep)
                    if op_vars['Vintage'].get():
                        np_img = np.array(img)
                        np_img[..., :3] = np.clip(np_img[..., :3] * 0.9 + 20, 0, 255).astype(np.uint8)
                        img = Image.fromarray(np_img)
                    if op_vars['Resize'].get():
                        w = self.batch_resize_width.get(); h = self.batch_resize_height.get()
                        if w > 0 and h > 0:
                            img = img.resize((w, h), Image.Resampling.LANCZOS)
                    if op_vars['Rotate'].get():
                        angle = int(self.batch_rotate.get())
                        img = img.rotate(-angle, expand=True)
                    if op_vars['Flip Horizontal'].get():
                        img = ImageOps.mirror(img)
                    if op_vars['Brightness'].get():
                        img = ImageEnhance.Brightness(img).enhance(self.batch_brightness.get())
                    if op_vars['Contrast'].get():
                        img = ImageEnhance.Contrast(img).enhance(self.batch_contrast.get())
                    stem = os.path.splitext(os.path.basename(file_path))[0]
                    out_ext = 'png' if self.batch_output_format.get() == 'PNG' else 'jpg'
                    out_name = f'{stem}_edited.{out_ext}'
                    out_path = os.path.join(output_dir, out_name)
                    if out_ext == 'jpg':
                        img.convert('RGB').save(out_path, quality=self.batch_quality.get())
                    else:
                        img.save(out_path)
                    self.after(0, lambda: self.batch_result_box.insert('end', f'{file_path}: OK\n'))
                except Exception as e:
                    self.after(0, lambda: self.batch_result_box.insert('end', f'{file_path}: ERROR {e}\n'))
                self.after(0, lambda: self.batch_status.configure(text=f'Processing: {os.path.basename(file_path)} ({index}/{total})'))
                self.after(0, lambda: self.batch_progress.set(index / total))
            def worker():
                total = len(files)
                for idx, f in enumerate(files, start=1):
                    if self.batch_cancel_event.is_set():
                        self.after(0, lambda: self.batch_status.configure(text='Cancelled'))
                        break
                    process_file(f, idx, total)
                self.after(0, lambda: self.batch_status.configure(text='Batch Complete'))
            threading.Thread(target=worker, daemon=True).start()
        ctk.CTkButton(scrollable_frame, text='Start Batch Processing', command=run_batch).pack(pady=8, padx=10, fill='x')
        ctk.CTkButton(scrollable_frame, text='Cancel', command=lambda: self.batch_cancel_event.set() if self.batch_cancel_event else None).pack(pady=2, padx=10, fill='x')

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
             
if __name__ == '__main__':
    app = PictureEditor()
    app.mainloop()