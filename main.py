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


    
if __name__ == '__main__':
    app = PictureEditor()
    app.mainloop()