import tkinter as tk
from PIL import Image, ImageTk
import math
import os
import constants
import time
from database import Database

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
        
        self.cur_tile = tk.IntVar()
        self.cur_tile.set(5)
        self.cur_img = self.format_image((1, 1, 1))
        self.img_width, self.img_height = self.cur_img.size
        
        self.create_image_canvas()
        gr_img = GridImages(self.canvas, self.zoomed_canvas, self.cur_img)
        self.create_scrollbar()
        
        self.create_marker_binds()
        self.create_navigator()
        
    def create_scrollbar(self):
        vbar = tk.Scrollbar(self.master, orient='vertical', command=self.canvas.yview)
        vbar.grid(row=1, column=2, sticky='ns')
        hbar = tk.Scrollbar(self.master, orient='horizontal', command=self.canvas.xview)
        hbar.grid(row=2, column=1, sticky='we')
        
        self.canvas.configure(xscrollcommand=hbar.set, yscrollcommand=vbar.set,
                              xscrollincrement='2', yscrollincrement='2', scrollregion=self.canvas.bbox("all"))
        self.canvas.update()
        
        self.master.rowconfigure(1, weight=1)
        self.master.columnconfigure(1, weight=1)
        self.master.columnconfigure(3, weight =1)
        self.canvas.bind('<MouseWheel>', self.verti_wheel)
        self.canvas.bind('<Shift-MouseWheel>', self.hori_wheel) 
        
    def verti_wheel(self, event):
        """Event method that scrolls the image vertically using the mousewheel.

        Scrolls the image 20 units up or down depending on the direction of the mousewheel input.
        """
        if event.num == 5 or event.delta == -120:  # scroll down
            self.canvas.yview('scroll', 20, 'units')
        if event.num == 4 or event.delta == 120:
            self.canvas.yview('scroll', -20, 'units')

    def hori_wheel(self, event):
        """Event method that scrolls the image horizontally using shift + mousewheel.

        Scrolls the image 20 units left or right depending on the direction of the mousewheel.
        """
        if event.num == 5 or event.delta == -120:  # scroll down
            self.canvas.xview('scroll', 20, 'units')
        if event.num == 4 or event.delta == 120:
            self.canvas.xview('scroll', -20, 'units')

    def create_navigator(self):
        self.navigator = tk.Frame(self.master)
        self.navigator.grid(row=3, column=1, columnspan=3)
        self.n_text = tk.Label(self.navigator, text = str(self.cur_tile.get()), font = ("Calibri", 30))
        self.n_text.grid(row = 1, column = 1, pady = 25, padx = 25)
        
        self.n_forward_button = tk.Button(self.navigator, text =">", font = ("Calibri", 20),
                                           command=self._forward)
        self.n_forward_button.grid(row = 1, column = 2)
        
        self.n_backward_button = tk.Button(self.navigator, text ="<", font = ("Calibri", 20),
                                           command=self._backward)
        self.n_backward_button.grid(row = 1, column = 0)
        self.create_finished()
        # self.unfinished = next((i for i, j in enumerate(bools) if j == False), 0) # finds the first unfinished
        
    def create_finished(self):
        self.var_fin = tk.IntVar()
        self.var_fin.set(0)
        self.finished = tk.Checkbutton(self.navigator, text = "Finished", variable = self.var_fin, # finished squares
                                        onvalue = 1, offvalue = 0)
        self.finished.grid(row = 3, column = 1)
        
    def _forward(self):
        if self.cur_tile.get() < constants.grids_h * constants.grids_w:
            self.cur_tile.set(self.cur_tile.get() + 1)
        else: 
            return
        self.n_text.configure(text = str(self.cur_tile.get()))
        self.n_text.update()
        
        self._update_image()
        
    def _backward(self):
        if self.cur_tile.get() > 0:
            self.cur_tile.set(self.cur_tile.get() - 1)
        else:
            return
        self.n_text.configure(text = str(self.cur_tile.get()))
        self.n_text.update()
        
        self._update_image()
        
    def _update_image(self):
        self.canvas.delete("all")
        self.zoomed_canvas.delete("all")
        self.cur_img = self.format_image((1, 1, 1))
        self.img_width, self.img_height = self.cur_img.size
        gr_img = GridImages(self.canvas, self.zoomed_canvas, self.cur_img)
        
    def create_image_canvas(self):
        self.canvas = tk.Canvas(self.master, highlightthickness=0)
        self.canvas.grid(row=1, column=1, sticky="nswe")
        self.zoomed_canvas = tk.Canvas(self.master, highlightthickness=0)
        self.zoomed_canvas.grid(row=1, column=3, sticky="nswe")
        self.canvas.focus_set()
    
    def format_image(self, *intensity): # changing color channels of the picture
        cur_img_path = os.path.join(parent_dir, "images", f"{self.cur_tile.get()}.tif")
        cur_img = Image.open(cur_img_path)
        
        if not intensity:
            return cur_img
        else:
            intensity = intensity[0]
        
        r, g, b = cur_img.split()
        r = r.point(lambda i: i * intensity[0])
        g = g.point(lambda i: i * intensity[1])
        b = b.point(lambda i: i * intensity[2])
        
        return Image.merge("RGB", (r, g, b))
    
    def create_marker_binds(self):
        self.canvas.bind("q", lambda event, m_type = "u": self._markers(event, m_type))
        self.canvas.bind("w", lambda event, m_type = "bb": self._markers(event, m_type))
        self.canvas.bind("e", lambda event, m_type = "ms": self._markers(event, m_type))
        self.canvas.bind("r", lambda event, m_type = "bbms": self._markers(event, m_type))
        
    def _markers(self, event, m_type):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        self.create_marker(m_type, self.cur_tile.get(), x, y)
        
        Database(parent_dir).add_value(m_type, self.cur_tile.get(), x, y)
        
    def create_marker(self, m_type, tile_id, x, y):
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
    
if __name__ == "__main__":
    root = tk.Tk()
    app = Application(root)
    root.mainloop()