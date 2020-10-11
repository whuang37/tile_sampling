from PIL import Image
import numpy as np
import pandas as pd
import os
import constants
import h5py

# def color_image(array_path):
#     array = np.load(array_path)
#     img = Image.fromarray(array[12], "RGB")
    
#     return img

# def crop_image(img):
#     im_w, im_h = img.size
    
#     w = im_w / constants.grids_w
#     h = im_h / constants.grids_h
    
#     z = 1 # for the name of each grid
#     for i in range(0, constants.grids_h):
#         for j in range(0, constants.grids_w):
#             left = j * w
#             right = (j + 1) * w
#             upper = i * h
#             lower = (i + 1) * h
            
#             cropped = img.crop((left, upper, right, lower))
            
#             cropped_path = os.path.join(image_path, f"{z}.tif")
#             cropped.save(cropped_path)
#             z += 1

parent_dir = r"test" # change later to reflect what the user puts in
np_path = os.path.join(parent_dir, "test_100_tile_stack.npy")
array = np.load(np_path)
save_path = os.path.join(parent_dir, "tile_array.h5")
with h5py.File(save_path, "w") as hf:
    hf.create_dataset("tiles", data=array)