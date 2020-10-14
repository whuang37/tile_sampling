import h5py
import numpy as np
import pandas as pd

with h5py.File(r"test/A18-1_sample_1.hdf5", "r") as hf:
    print(hf["tile_index"][0:100])