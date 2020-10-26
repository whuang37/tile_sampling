import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from PIL import Image, ImageTk
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

global parent_dir 
parent_dir = r"test"

class Application(tk.Frame):
    def __init__(self, master):
        self.master = master
        tk.Frame.__init__(self, master)
        self.master.title("Tile Sampling")
        
        self.finished_bools = Database(parent_dir).get_tiles()
        
        bools = [i[1] for i in self.finished_bools]
        first_unfinished = next((i for i, j in enumerate(bools) if j == False), 0)
        
        self.max_tiles = Database(parent_dir).get_num_tiles()
        
        self.cur_tile = tk.IntVar()
        self.cur_tile.set(self.finished_bools[first_unfinished][0])
        self.cur_img = self.format_image()
        self.img_width, self.img_height = self.cur_img.size
        
        self.create_navigator()
        self.next_call = time.time() - 1
        self._update_image()
        
        self.master.rowconfigure(1, weight=1)
        self.master.columnconfigure(1, weight=1)
        self.master.columnconfigure(3, weight=1)
        
        self.inf_frame = InformationFrame(self.master, self.cur_tile.get())
        self.inf_frame.grid(row=0, column=0, sticky="ns", rowspan=4)
        
        self.create_optionbar()
        
        self.r = tk.DoubleVar(value=100)
        self.g = tk.DoubleVar(value=100)
        self.b = tk.DoubleVar(value=100)
        
    def create_optionbar(self):
        self.option_bar = tk.Frame(self.master)
        self.option_bar.grid(row=0, column=1, columnspan=3, sticky='we')
        # file menu
        file_b = tk.Menubutton(self.option_bar, text="File", relief="raised")
        file_menu = tk.Menu(file_b, tearoff=False)
        file_b.configure(menu=file_menu)
        file_b.pack(side="left")
        
        file_menu.add_command (label="Open New Folder", command=self.open_new_folder)
        file_menu.add_command(label="Export Images", command=self.export_images)
        file_menu.add_command(label="Update HDF5 File", command=self.update_hdf5)
        file_menu.add_command(label="Exit", command=root.quit)
        
        # view menu
        view_b = tk.Menubutton(self.option_bar, text="View", relief="raised")
        view_menu = tk.Menu(view_b, tearoff=False)
        view_b.configure(menu=view_menu)
        view_b.pack(side="left")
        
        view_menu.add_command(label="Calibrate Colors", command=self.calibrate_colors)
        # view_menu.add_command(label = "Set Window to Original Size", command = self.original_size)
        
        # variables for color calibration
        
    def update_hdf5(self):
        updater = tk.Toplevel()
        updater.title("Update HDF5 File")
        updater.transient(root)
        hdf5 = tk.Label(updater, text="Select new HDF5 file:")
        hdf5.grid(row=0, column=0, padx=5, sticky="w")
        
        new_hdf5_path = tk.StringVar()
        
        folder_entry = tk.Entry(updater, textvariable = new_hdf5_path, width=50)
        folder_entry.grid(row=1, column=0, padx=10, pady=10, sticky = "nsew")
        
        def select_folder():
            """Selects folder where exported images should go.

                Gets the image path from file explorer on click of the browse button.
            """
            path = filedialog.askopenfilename()
            if path == "":
                return
            else:
                new_hdf5_path.set(path + "/")
                folder_entry.update()
            
        folder_button = tk.Button(updater, text = "Browse", command = select_folder)
        folder_button.grid(row = 1, column = 1, padx = 10, pady = 10, sticky = "w")
        
        def confirm():
            """Exports images to folder_path.

            Takes case name and folder path and exports biondi images to the designated folder.
            """
            if new_hdf5_path.get() == "/":
                return
            else:
                Database(parent_dir).update_hdf5(new_hdf5_path.get())
                self.max_tiles = Database(parent_dir).get_num_tiles()
                self.finished_bools = Database(parent_dir).get_tiles()
                combo_values = [str(i) for i in range(1, self.max_tiles+1)]
                self.goto.configure(values=combo_values)
                self.goto.update()
                updater.destroy()
        
        ok_button = tk.Button(updater, text = "Okay", command = confirm)
        ok_button.grid(row = 3, column = 1, padx = 10, pady = 10, sticky = "e")
        
    def open_new_folder(self):
        global parent_dir
        previous_dir = parent_dir
        parent_dir = filedialog.askdirectory()

        if parent_dir:
            self._update_image()
            self.inf_frame._update_graphs()
        else:
            parent_dir = previous_dir
            
    def export_images(self):
        pass
    
    def calibrate_colors(self):
        colors = tk.Toplevel()
        colors.transient(root)
        colors.title("Color Calibration")
        colors.grab_set()
        
        colors.rowconfigure(5, weight=1)
        r_scale = tk.Scale(colors, from_=0, to=400, orient="horizontal", length=250, variable=self.r, label="Red", fg="red")
        r_scale.grid(column=1, row=2, columnspan=3)
        g_scale = tk.Scale(colors, from_=0, to=400, orient="horizontal", length=250, variable=self.g, label="Green", fg="green")
        g_scale.grid(column=1, row=3, columnspan=3)
        b_scale = tk.Scale(colors, from_=0, to=400, orient="horizontal", length=250, variable=self.b, label="Blue", fg="blue")
        b_scale.grid(column=1, row=4, columnspan=3)
        
        def color_reset():
            self.r.set(100)
            self.g.set(100)
            self.b.set(100)
            
        reset_button = tk.Button(colors, text="Reset", command=color_reset)
        reset_button.grid(column=3, row=5, pady=3, padx=3)
        
        def confirm_colors():
            channels = (self.r.get() / 100, self.g.get() / 100, self.b.get() / 100)
            self._update_image(channels)
            colors.destroy()
        ok_button = tk.Button(colors, text="Ok", command=confirm_colors)
        ok_button.grid(column=3, row=5, sticky="e", pady=3, padx=3)
        
    def export_images(self):
        export = tk.Toplevel()
        export.transient(root)
        export.title("Export")
        export.columnconfigure(2, weight = 1)
        
        case_name = tk.StringVar()
        new_folder_path = tk.StringVar()
        
        name = tk.Label(export, text = "Case Name:")
        name.grid(row = 1, column = 0, padx =10, pady = 10, sticky = "nsew")
        
        name_entry = tk.Entry(export, textvariable = case_name)
        name_entry.grid(row = 1, column = 1, padx =10, pady = 10, sticky = "nsew")
        
        folder_entry = tk.Entry(export, textvariable = new_folder_path)
        folder_entry.grid(row = 2, column = 0, padx =10, pady = 10, sticky = "nsew")
        
        def select_folder():
            """Selects folder where exported images should go.

                Gets the image path from file explorer on click of the browse button.
            """
            path = filedialog.askdirectory()
            if path == "":
                return
            else:
                new_folder_path.set(path + "/")
                folder_entry.update()
            
        folder_button = tk.Button(export, text = "Browse", command = select_folder)
        folder_button.grid(row = 2, column = 1, padx = 10, pady = 10, sticky = "w")
        
        def confirm():
            """Exports images to folder_path.

            Takes case name and folder path and exports biondi images to the designated folder.
            """
            if case_name.get() == "" or new_folder_path.get() == "/":
                return
            else:
                Database(parent_dir).export_all_annotations(new_folder_path.get(), case_name.get())
                export.destroy()
        
        ok_button = tk.Button(export, text = "Okay", command = confirm)
        ok_button.grid(row = 3, column = 1, padx = 10, pady = 10, sticky = "e")
        
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
        combo_values = [str(i) for i in range(1, self.max_tiles+1)]
        
        self.goto = ttk.Combobox(self.navigator, values=combo_values,
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
        channels = (self.r.get() / 100, self.g.get() / 100, self.b.get() / 100)
        self._update_image(channels)
    
    def create_finished(self):
        self.var_fin = tk.IntVar()
        self.var_fin.set(self.finished_bools[self.cur_tile.get()][1])
        self.finished = tk.Checkbutton(self.navigator, text = "Finished", variable = self.var_fin, # finished squares
                                        onvalue = 1, offvalue = 0, command = lambda i = self.cur_tile.get(): self._update_finished(i))
        self.finished.grid(row = 3, column = 1)
        
    def _update_finished(self, tile_id):
        if self.var_fin.get() == 1:
            self.inf_frame._update_graphs()
        
        Database(parent_dir).finish_tile(tile_id, self.var_fin.get())
        self.inf_frame._update_completed_label(self.var_fin.get())
        
    def _increment_tile(self, i):
        if (self.cur_tile.get() >= self.max_tiles) & (i == 1):
            return
        elif (self.cur_tile.get() <= 0) & (i == -1):
            return
        else: 
            self.cur_tile.set(self.cur_tile.get() + i)
            channels = (self.r.get() / 100, self.g.get() / 100, self.b.get() / 100)
            self._update_image(channels)
            self.goto.set(str(self.cur_tile.get() + 1))
            self.inf_frame._update_tile_info(self.cur_tile.get())
        
    def _update_image(self, *colors):
        if not colors:
            self.cur_img = self.format_image()
        else:
            self.cur_img = self.format_image(colors[0])
            
        try: # try for startup call
            self.canvas.destroy()
            self.zoomed_canvas.destroy()
        except:
            pass
        self.create_image_canvas()
        gr_img = GridImages(self.canvas, self.zoomed_canvas, self.cur_img)
        self.initiate_markers()
        self.create_scrollbar()
        self._create_binds()
        
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
        array_path = os.path.join(parent_dir, "tile_array.hdf5")
        
        with h5py.File(array_path, "r") as hf:
            cur_array = hf["images"][self.cur_tile.get()]
        
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
    
    def _create_binds(self):
        for key, binding in constants.bindings.items():
            self.canvas.bind(binding, lambda event, m_type = key: self._markers(event, m_type))
        
    def _markers(self, event, m_type):
        if self.var_fin.get() == 1: # if the grid is marked as finished
            return
        elif time.time() > self.next_call: # adds a time delay to allow counter to go up
            self.next_call = time.time() + .5
        else:
            return
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        self.create_marker(m_type, self.cur_tile.get(), x, y)
        
        Database(parent_dir).add_value(m_type, self.cur_tile.get(), x, y)
        
        self.inf_frame._update_tile_info(self.cur_tile.get())
        
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
        
        # can optimize later
        self.canvas.create_line(x , y - 10, x, y + 10, fill = color, width = 2, tag = tag)
        # self.canvas.create_line(x , y - 3, x, y - 10, fill = color, width = 2, tag = tag)
        self.canvas.create_line(x - 10, y, x + 10, y, fill = color, width = 2, tag = tag)
        # self.canvas.create_line(x - 3, y, x - 10, y, fill = color, width = 2, tag = tag)
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
        self.inf_frame._update_tile_info(self.cur_tile.get())
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
            
        self.zoomed.moveto("image", x=str(x), y=str(y)) # very under documented function11
        
    def show_img(self, img, canvas):
        imagetk = ImageTk.PhotoImage(img)
        imageid = canvas.create_image(0, 0, anchor="nw", image = imagetk, tag = "image")
        canvas.lower(imageid)
        canvas.imagetk = imagetk # reference for garbage collection
    
class InformationFrame(tk.Frame):
    def __init__(self, master, cur_tile):
        tk.Frame.__init__(self)
        self.master = master
        self.cur_tile = cur_tile
        self.create_tile_info()
        self.create_graph_canvas()
        
        self.rowconfigure(3, weight=1)
        
        self.completed = False
        
        self.update_graph_button = tk.Button(self, text="Update Graphs", font=("Calibri 15"), command=self._update_graphs)
        self.update_graph_button.grid(row=5,column=0, sticky="we", padx=3, pady=3)
        
        self.completed_label = tk.Label(self, bg="red", font="Calibri 18", height=3)
        self._update_completed_label(True)
        
    def create_tile_info(self):
        self.tile_info = tk.Frame(self)
        self.tile_info.grid(row=4, column=0)
        binds = constants.bindings.copy()
        binds["total"] = ""
        
        colors = constants.marker_color.copy()
        colors["total"] = "limegreen"
        i = 0
        labels = []
        for key, color in colors.items():
            labels.append(tk.Label(self.tile_info, text=f"{binds[key]}\n{key}", bg=color, font=("Calibri, 10"), width=9))
            labels[i].grid(row=3, column=i, sticky='we')
            i += 1
        
        values = Database(parent_dir).tile_annotation_values(self.cur_tile)
        
        self.ann_counts = {}
        i = 0
        for key, color in colors.items():
            self.ann_counts[key] = tk.Label(self.tile_info, text=f"{values[key]}", bg=color, font=("Calibri, 10"), width=9)
            self.ann_counts[key].grid(row=4, column=i, sticky="we")
            i += 1
        
    def _update_tile_info(self, tile_id):
        values = Database(parent_dir).tile_annotation_values(tile_id)
        
        for key in values:
            self.ann_counts[key].config(text =str(values[key]))
    
    def _update_completed_label(self, finished):
        # finished to check when the user checks/unchecks the finished box
        if finished:
            self.completed, total_annotated = Database(parent_dir).check_completed()
            # self.completed = True
            
            if self.completed:
                completed_text = f"COMPLETED - EXPORT IMMEDIATELY\n{total_annotated} CELLS ANNOTATED"
                self.completed_label.config(text=completed_text)
                self.completed_label.grid(row=0, column=0, columnspan=2, sticky='nsew')
            else:
                self.completed_label.grid_forget()
        else:
            self.completed_label.grid_forget()
                
    
    def create_graph_canvas(self):
        self.graphs_canvas = tk.Canvas(self)
        img = Database(parent_dir).create_graphs()
        imagetk = ImageTk.PhotoImage(img)
        imageid = self.graphs_canvas.create_image(0, 0, anchor="nw", image=imagetk)
        self.graphs_canvas.lower(imageid)
        self.graphs_canvas.imagetk = imagetk
        self.graphs_canvas.update()
        
        self.create_graph_scrollbar()
        self.graphs_canvas.grid(row=3, column=0, sticky="ns")
        
    def create_graph_scrollbar(self):
        self.vbar = tk.Scrollbar(self, orient="vertical", command=self.graphs_canvas.yview)
        self.graphs_canvas.configure(yscrollcommand=self.vbar.set, yscrollincrement="2", 
                                     scrollregion=self.graphs_canvas.bbox("all"))
        self.graphs_canvas.update()
        
        self.vbar.grid(row=3, column=1, sticky="ns")
        self.graphs_canvas.bind('<MouseWheel>', self.verti_wheel)
        self.graphs_canvas.bind('<Shift-MouseWheel>', self.hori_wheel) 
        
    def verti_wheel(self, event):
        if event.num == 5 or event.delta == -120:  # scroll down
            self.graphs_canvas.yview('scroll', 20, 'units')
        if event.num == 4 or event.delta == 120:
            self.graphs_canvas.yview('scroll', -20, 'units')

    def hori_wheel(self, event):
        if event.num == 5 or event.delta == -120:  # scroll down
            self.graphs_canvas.xview('scroll', 20, 'units')
        if event.num == 4 or event.delta == 120:
            self.graphs_canvas.xview('scroll', -20, 'units')
    
    def _update_graphs(self):
        self.graphs_canvas.delete("all")
        img = Database(parent_dir).create_graphs()
        imagetk = ImageTk.PhotoImage(img)
        imageid = self.graphs_canvas.create_image(0, 0, anchor="nw", image=imagetk)
        self.graphs_canvas.lower(imageid)
        self.graphs_canvas.imagetk = imagetk
        self.graphs_canvas.update()
        
class OpeningWindow:
    def __init__(self, master):
        self.master = master
        # self.master.geometry("580x100")
        self.master.title("Tile Sampling Tool")

        w1 = f"Welcome to the Tile Sampling  Tool!\nIf you are returning to a previous session, please click on the \"Open Previous Folder\" button.\nIf you are starting a new session, please create an empty folder and select it using the \"Initiate Folder\" button."

        self.welcome_label1 = tk.Label(self.master, text = w1)
        self.welcome_label1.grid(row = 0, column = 2, sticky = 'nswe')
        
        self.button_frame = tk.Frame(self.master)
        self.button_frame.grid(row = 4, column = 2, sticky = 'ns')

        self.find_image_button = tk.Button(self.button_frame, text="Open Previous Folder", command = lambda: self.open_image())
        self.find_image_button.pack(side = "left", padx = 2 , pady = 2)
        
        self.initiate_folder_button = tk.Button(self.button_frame, text = "Initiate Folder", command = self.initiate_folder)
        self.initiate_folder_button.pack(side = "left", padx = 2 , pady = 2)
    
    def open_image(self):
        """Opens initial Application and destroys initial window assess

        Creates Application and destroys initial assets so they do not interfere with
        the Application class.
        
        Args:
            welcome_label1 (tk.Label): Label of text used to welcome user into the program.
            welcome_label2 (tk.Label): Label of text used to welcome user into the program.
            welcome_label3 (tk.Label): Label of text used to welcome user into the program.
            welcome_label4 (tk.Label): Label of text used to welcome user into the program.
            button_frame (tk.Frame): Frame containing buttons in the opening window.
        """
        path = filedialog.askdirectory()
        if path == "":
            return
        else:
            self.welcome_label1.destroy()
            self.button_frame.destroy()
            global parent_dir
            parent_dir = path
            i = Application(root)

    def confirm_function(self, folder_path, file_path, nf):
        """Initializes a new folder and creates a success label

        Calls FileManagement to initate a folder with a grid image file 
        and annotator initials. Creates a success window on completion.
        
        Args:
            folder_path (str): Path to folder where images will be saved selected from the askdirectory.
            file_path (str): Path to the hdf5 image to be moved into the saving folder.
            nf (tk.Toplevel): Toplevel window to select the folder path and file path.
        """
        if folder_path == "" or file_path == "":
            return
        
        nf.destroy()

        global parent_dir
        parent_dir = folder_path
        
        Database(parent_dir).initiate(file_path)
        done_screen = tk.Toplevel()

        success_label1 = tk.Label(done_screen, text = "Folder sucessfully initialized!")
        success_label1.grid(row = 0, column = 0, sticky = 'nswe')

        def init_confirm():
            done_screen.destroy()
            self.welcome_label1.destroy()
            self.button_frame.destroy()
            i = Application(root)
            
        close_button = tk.Button(done_screen, text = "OK", command = lambda: init_confirm())
        close_button.grid(row = 3, column = 0, sticky = 's')

    def initiate_folder(self):
        """Creates a Window for inputting args to initialize folder

        Creates a window and corresponding buttons and entry fields for users
        to enter in data to initialize a folder for biondi body analysis.
        """
        nf = tk.Toplevel()
        # nf.geometry("365x165")
        nf.transient(root)

        folder_path = tk.StringVar()
        folder_ebox = tk.Entry(nf, textvariable = folder_path, width = 50)
        folder_ebox.grid(row = 1, column = 0)
        
        folder_button = tk.Button(nf, text = "Browse...", command = lambda: folder_path.set(filedialog.askdirectory()))
        folder_button.grid(row = 1, column = 1)

        file_name = tk.StringVar()
        file_ebox = tk.Entry(nf, textvariable = file_name, width = 50)
        file_ebox.grid(row = 4, column = 0)

        file_button = tk.Button(nf, text = "Browse...", command = lambda: file_name.set(filedialog.askopenfilename()))
        file_button.grid(row = 4, column = 1)

        confirm_button = tk.Button(nf, text = "Confirm", command = lambda: self.confirm_function(folder_path.get(), file_name.get(), nf))
        confirm_button.grid(row = 8, column = 1)

        folder_label = tk.Label(nf, text = "Enter an empty folder directory:")
        folder_label.grid(row = 0, column = 0, sticky = 'w')

        file_label = tk.Label(nf, text = "Enter the hdf5 file directory:")
        file_label.grid(row = 3, column = 0, sticky = 'w')

if __name__ == "__main__":
    root = tk.Tk()
    app = OpeningWindow(root)
    root.mainloop()