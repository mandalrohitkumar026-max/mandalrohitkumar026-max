import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import gaussian_filter
import math
import os

print("Starting banner animation generation...")
base_img = Image.open("banner.jpg").convert("RGB")
W, H = base_img.size
base_arr = np.array(base_img, dtype=np.float32)

print(f"Image loaded: {W}x{H}")
