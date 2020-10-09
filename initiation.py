from PIL import Image
import os
import constants


def color_image(red, blue, green):
    r = Image.open(red)
    g = Image.open(green)
    b = Image.open(blue)
    
    return Image.merge("RGB", (r, g, b))

def crop_image(img):
    im_w, im_h = img.size
    
    w = im_w / constants.grids_w
    h = im_h / constants.grids_h
    
    z = 1 # for the name of each grid
    for i in range(0, constants.grids_h):
        for j in range(0, constants.grids_w):
            left = j * w
            right = (j + 1) * w
            upper = i * h
            lower = (i + 1) * h
            
            cropped = img.crop((left, upper, right, lower))
            
            cropped_path = os.path.join(image_path, f"{z}.tif")
            cropped.save(cropped_path)
            z += 1

parent_dir = r"test" # change later to reflect what the user puts in
red_path = r"test\r.tif" # replace later
blue_path = r"test\b.tif"
green_path = r"test\g.tif"

image_path = os.path.join(parent_dir, "images")
try:
    os.mkdir(image_path)
except FileExistsError:
    print("already exists")
    pass

colorized = color_image(red_path, blue_path, green_path)
crop_image(colorized)