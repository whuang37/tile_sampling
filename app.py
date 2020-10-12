import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import math
import os
import constants
import time
from database import Database
import numpy as np
import h5py
"""
Notes/Design

Essentially 3 main windows: 1 a window to see data being entered for this particular grid 
most likely gonna be some sort of scrolling list.

2. a 2x zoomed window that shows what is next to the mouse
3. a normal view of the grid the mouse hovers over to generate the zoomed in window to the right.

Potential tools: color channel changing, annotations, warnings for what annotations at, exporting

class: the canvas itself and building its functions

markers: markers for the 4 types of things
"""

parent_dir = r"test"
class Application(tk.Frame):
    def __init__(self, master):
        self.master = master
        tk.Frame.__init__(self, master)
        self.master.title("Tile Sampling")
        
        self.finished_bools = Database(parent_dir).get_tiles()
        bools = [i[1] for i in self.finished_bools]
        first_unfinished = next((i for i, j in enumerate(bools) if j == False), 0)
        
        self.cur_tile = tk.IntVar()
        self.cur_tile.set(self.finished_bools[first_unfinished][0])
        
        self.cur_img = self.format_image()
        self.img_width, self.img_height = self.cur_img.size
        
        self.create_image_canvas()
        gr_img = GridImages(self.canvas, self.zoomed_canvas, self.cur_img)
        self.initiate_markers()
        self.create_scrollbar()
        
        self.master.rowconfigure(1, weight=1)
        self.master.columnconfigure(1, weight=1)
        self.master.columnconfigure(3, weight =1)
        
        self.create_binds()
        self.create_navigator()
        
        
    def create_scrollbar(self):
        self.vbar = tk.Scrollbar(self.master, orient='vertical', command=self.canvas.yview)
        self.vbar.grid(row=1, column=2, sticky='ns')
        self.hbar = tk.Scrollbar(self.master, orient='horizontal', command=self.canvas.xview)
        self.hbar.grid(row=2, column=1, sticky='we')
        
        self.canvas.configure(xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set,
                              xscrollincrement='2', yscrollincrement='2', scrollregion=self.canvas.bbox("all"))
        self.canvas.update()
        self.canvas.bind('<MouseWheel>', self.verti_wheel)
        self.canvas.bind('<Shift-MouseWheel>', self.hori_wheel) 
        
        
    def verti_wheel(self, event):
        if event.num == 5 or event.delta == -120:  # scroll down
            self.canvas.yview('scroll', 20, 'units')
        if event.num == 4 or event.delta == 120:
            self.canvas.yview('scroll', -20, 'units')

    def hori_wheel(self, event):
        if event.num == 5 or event.delta == -120:  # scroll down
            self.canvas.xview('scroll', 20, 'units')
        if event.num == 4 or event.delta == 120:
            self.canvas.xview('scroll', -20, 'units')

    def create_navigator(self):
        self.navigator = tk.Frame(self.master)
        self.navigator.grid(row=3, column=1, columnspan=3)
        
        self.goto = ttk.Combobox(self.navigator, values=[str(i) for i in range(1,101)],
                                 font=("Calibri", 30), width=3, justify="center", 
                                 state="normal")
        self.goto.bind("<<ComboboxSelected>>", self._nav_goto)
        self.goto.bind("<Return>", self._nav_goto)
        self.goto.set(str(self.cur_tile.get() + 1))
        self.goto.grid(row=1, column=1, pady=25, padx=25)
        
        self.n_forward_button = tk.Button(self.navigator, text =">", font=("Calibri", 20),
                                           command=lambda: self._increment_tile(1))
        self.n_forward_button.grid(row=1, column=2)
        
        self.n_backward_button = tk.Button(self.navigator, text ="<", font=("Calibri", 20),
                                           command=lambda: self._increment_tile(-1))
        self.n_backward_button.grid(row=1, column=0)
        self.create_finished()
        # self.unfinished = next((i for i, j in enumerate(bools) if j == False), 0) # finds the first unfinished
        
    def _nav_goto(self, event):
        self.cur_tile.set(int(self.goto.get()) - 1)
        self._update_image()
    
    def create_finished(self):
        self.var_fin = tk.IntVar()
        self.var_fin.set(self.finished_bools[self.cur_tile.get()][1])
        self.finished = tk.Checkbutton(self.navigator, text = "Finished", variable = self.var_fin, # finished squares
                                        onvalue = 1, offvalue = 0, command = lambda i = self.cur_tile.get(): self._update_finished(i))
        self.finished.grid(row = 3, column = 1)
        
    def _update_finished(self, tile_id):
        Database(parent_dir).finish_tile(tile_id, self.var_fin.get())
        
    def _increment_tile(self, i):
        if (self.cur_tile.get() >= constants.grids_h * constants.grids_w) & (i == 1):
            return
        elif (self.cur_tile.get() <= 0) & (i == -1):
            return
        else: 
            self.cur_tile.set(self.cur_tile.get() + i)
            self._update_image()
            self.goto.set(str(self.cur_tile.get() + 1))
        
    def _update_image(self, *colors):
        if not colors:
            self.cur_img = self.format_image()
        else:
            self.cur_img = self.format_image(colors[0])
            
        self.canvas.destroy()
        self.zoomed_canvas.destroy()
        self.create_image_canvas()
        gr_img = GridImages(self.canvas, self.zoomed_canvas, self.cur_img)
        self.initiate_markers()
        self.create_scrollbar()
        self.create_binds()
        
        self.cur_img = self.format_image((1, 1, 1))
        self.img_width, self.img_height = self.cur_img.size
        
        self.finished.destroy()
        self.create_finished()
        
    def create_image_canvas(self):
        self.canvas = tk.Canvas(self.master, highlightthickness=0, bg="white")
        self.canvas.grid(row=1, column=1, sticky="nswe")
        self.zoomed_canvas = tk.Canvas(self.master, highlightthickness=0, bg="black")
        self.zoomed_canvas.grid(row=1, column=3, sticky="nswe")
        self.canvas.focus_set()
    
    def format_image(self, *colors): # opening and changing color channels of the picture
        array_path = os.path.join(parent_dir, "tile_array.h5")
        
        with h5py.File(array_path, "r") as hf:
            cur_array = hf["tiles"][self.cur_tile.get()]
        
        cur_img = Image.fromarray(cur_array, "RGB")
        del cur_array
        
        if not colors:
            return cur_img
        else:
            intensity = colors[0]
        
        r, g, b = cur_img.split()
        r = r.point(lambda i: i * intensity[0])
        g = g.point(lambda i: i * intensity[1])
        b = b.point(lambda i: i * intensity[2])
        
        return Image.merge("RGB", (r, g, b))
    
    def create_binds(self):
        for key, binding in constants.bindings.items():
            self.canvas.bind(binding, lambda event, m_type = key: self._markers(event, m_type))
        
    def _markers(self, event, m_type):
        if self.var_fin.get() == 1: # if the grid is marked as finished
            return
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        self.create_marker(m_type, self.cur_tile.get(), x, y)
        
        Database(parent_dir).add_value(m_type, self.cur_tile.get(), x, y)
        
    def initiate_markers(self):
        data = Database(parent_dir).query_tile_annotations(self.cur_tile.get())
        for i in data:
            self.create_marker(i[0], i[1], i[2], i[3]) # type, tileid, x, y
    
    def create_marker(self, m_type, tile_id, x, y):
        # prevents users from making markers off of the image
        if (x < 0) | (x > self.img_width):
            return
        elif (y < 0) | (y > self.img_height):
            return
        
        color = constants.marker_color[m_type]
        
        tag = f"{tile_id}_{x}_{y}"
        
        self.canvas.create_line(x , y + 3, x, y + 10, fill = color, width = 2, tag = tag)
        self.canvas.create_line(x , y - 3, x, y - 10, fill = color, width = 2, tag = tag)
        self.canvas.create_line(x + 3, y, x + 10, y, fill = color, width = 2, tag = tag)
        self.canvas.create_line(x - 3, y, x - 10, y, fill = color, width = 2, tag = tag)
        self.canvas.tag_bind(tag, '<ButtonPress-1>', lambda event, tag = tag, tile = tile_id, x = x, y = y: self._on_click(event, tag, tile, x, y))
        self.canvas.tag_bind(tag, '<Enter>', lambda event, tag = tag: self._on_enter(event, tag))
        self.canvas.tag_bind(tag, '<Leave>', lambda event, tag = tag: self._on_leave(event, tag, color))
        self.canvas.update() 
        
    def _on_enter(self, event, tag):
        self.canvas.itemconfig(tag, fill="white")
        
    def _on_leave(self, event, tag, color):
        self.canvas.itemconfig(tag, fill=color)
    
    def _on_click(self, event, tag, tile, x, y):
        self.canvas.delete(tag)
        
        Database(parent_dir).delete_value(tile, x, y)
class GridImages:
    def __init__(self, unzoomed, zoomed, img):
        self.unzoomed = unzoomed # canvas for unzoomed image
        self.zoomed = zoomed # canvas for zoomed image
        self.img = img
        
        w, h = self.img.size
        factor = constants.zooming_factor
        self.zoomed_img = img.resize((int(w * factor), int (h * factor)), Image.ANTIALIAS)
        
        self.show_img(self.img, self.unzoomed)
        self.show_img(self.zoomed_img, self.zoomed)
        
        # self.unzoomed.bind("<Button-1>", self._move_from)
        self.unzoomed.bind("<Motion>", self._hover_zoom)
        
    def _hover_zoom(self, event):
        self.w, self.h = self.zoomed.winfo_width(), self.zoomed.winfo_height()
        x = self.unzoomed.canvasx(event.x) # converts the x coord from relative to frame to relative to canvas
        x = -x * constants.zooming_factor + self.w / 2 - constants.tuning_factor 
        if x < -self.zoomed_img.width + self.w: # bounding coords including a margin
            x = -self.zoomed_img.width + self.w
        if x > 0:
            x = 0
        
        y = self.unzoomed.canvasy(event.y) # converts the x coord from relative to frame to relative to canvas
        y = -y * constants.zooming_factor + self.h / 2 - constants.tuning_factor 
        if y < -self.zoomed_img.height + self.h: # bounding coords including a margin
            y = -self.zoomed_img.height + self.h
        if y > 0:
            y = 0
            
        self.zoomed.moveto("image", x=str(x), y=str(y)) # very under documented function
        
    def show_img(self, img, canvas):
        imagetk = ImageTk.PhotoImage(img)
        imageid = canvas.create_image(0, 0, anchor="nw", image = imagetk, tag = "image")
        canvas.lower(imageid)
        canvas.imagetk = imagetk # reference for garbage collection
    
class InformationFrame(tk.Frame):
    def __init__(self, master):
        tk.Frame.__init__(self)
        self.master = master
        
        
if __name__ == "__main__":
    root = tk.Tk()
    app = Application(root)
    root.mainloop()