# %% [markdown]
# # Open and convert
# For AVIs, use cv2's `VideoCapture` class, then iterate through to convert it to a numpy array. Perform an averaging z-projection to get the background only (moving worms are removed). Convert to integers.

# %%
from pathlib import Path


import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pyparsing import col
from scipy import ndimage
from scipy.ndimage import sum as ndi_sum
from skimage.draw import circle_perimeter
from skimage.filters import sobel, threshold_triangle
from skimage.transform import hough_circle, hough_circle_peaks
from skimage.morphology import dilation, reconstruction


path = Path.home().joinpath('Desktop/20220527-p02-KTRb.avi')

vid = cv2.VideoCapture(str(path))
ret = True
frames = []
while ret:
    ret, img = vid.read()
    if ret:
        frames.append(img)

array = np.stack(frames, axis=0)
ave = np.mean(array, axis=0)
ave_int = ave.astype(int)

plt.imshow(ave_int)
plt.show()

gry = cv2.cvtColor(ave.astype(np.float32), cv2.COLOR_BGR2GRAY)

edges = sobel(gry)

plt.imshow(edges, cmap='gray')
plt.show()

thresh = threshold_triangle(edges)
binary = edges > thresh

plt.imshow(binary, cmap='gray')
plt.show()

radii = np.arange(71, 75, 2)
hough_res = hough_circle(binary, radii)
accums, cx, cy, radii = hough_circle_peaks(
    hough_res, radii, total_num_peaks=500)

cy = np.ndarray.tolist(cy)
cx = np.ndarray.tolist(cx)
radii = np.ndarray.tolist(radii)

bad_indices = []
i = 0

for x, y in zip(cx, cy):
    if x < 100:
        bad_indices.append(i)
    elif x > 200 and x < 300:
        bad_indices.append(i)
    elif x > 400 and x < 500:
        bad_indices.append(i)
    elif x > 600 and x < 700:
        bad_indices.append(i)
    elif x > 800 and x < 900:
        bad_indices.append(i)
    elif x > 1000 and x < 1100:
        bad_indices.append(i)
    elif x > 1200:
        bad_indices.append(i)
    elif y < 100:
        bad_indices.append(i)
    elif y > 200 and y < 300:
        bad_indices.append(i)
    elif y > 400 and y < 500:
        bad_indices.append(i)
    elif y > 600 and y < 700:
        bad_indices.append(i)
    elif y > 800:
        bad_indices.append(i)
    else:
        i += 1

for i in bad_indices:
    cy.pop(i)
    cx.pop(i)
    radii.pop(i)

ave_int = ave.astype(int)

fig, ax = plt.subplots(ncols=1, nrows=1)
for center_y, center_x, radius in zip(cy, cx, radii):
    circy, circx = circle_perimeter(center_y, center_x, radius)
    ave_int[circy, circx] = (220, 20, 20)

plt.imshow(ave_int)
plt.show()

black = np.zeros(ave_int.shape[0:2])

for center_y, center_x, radius in zip(cy, cx, radii):
    circy, circx = circle_perimeter(center_y, center_x, radius)
    black[circy, circx] = 1

closed = dilation(black)

seed = np.copy(closed)
seed[1:-1, 1:-1] = closed.max()
mask = closed

filled = reconstruction(seed, mask, method='erosion')

lbl, objects = ndimage.label(filled)
centers = ndimage.center_of_mass(filled, lbl, range(1, 25, 1)) # n_wells

# make a data frame with well names linked to coordinates of centers
well_names = pd.DataFrame(centers, columns = ['y', 'x'])
well_names = well_names.sort_values(by=['x'])
well_names['row'] = ['A'] * 4 + ['B'] * 4 + ['C'] * 4 + ['D'] * 4 + ['E'] * 4 + ['F'] * 4 
well_names = well_names.sort_values(by=['y'])
well_names['col'] = ['01'] * 6 + ['02'] * 6 + ['03'] * 6 + ['04'] * 6
well_names['well'] = well_names['row'] + well_names['col']

mask = np.zeros(lbl.shape)
for x, y in centers:
    x = int(x)
    y = int(y)
    circy, circx = circle_perimeter(x, y, 73)
    mask[circy, circx] = 1

closed = dilation(mask)

seed = np.copy(closed)
seed[1:-1, 1:-1] = closed.max()
mask = closed

filled_mask = reconstruction(seed, mask, method='erosion')

plt.imshow(filled_mask, cmap='gray')
for index, row, in well_names.iterrows():
    plt.text(row['x'] - 25, row['y'], row['well'], fontsize=12)
plt.show()

# %% optical flow

vid = cv2.VideoCapture(str(path))

length = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
width = int(vid.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(vid.get(cv2.CAP_PROP_FRAME_HEIGHT))

vid_array = np.zeros((length, height, width))

# read first frame
ret, frame1 = vid.read()

# convert to gray scale
prvs = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
hsv = np.zeros_like(frame1)
hsv[..., 1] = 255
vid_array[0] = prvs

all_mag = np.zeros((length - 1, height, width))
count = 0
while(1):
    if count < length - 1:
        ret, frame2 = vid.read()
        next = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        vid_array[count + 1] = next
        flow = cv2.calcOpticalFlowFarneback(prvs, next, None, 0.5, 3, 15,
                                            3, 5, 1.2, 0)
        mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        prvs = next
        all_mag[count] = mag
        count += 1
        # for testing
        # if count > 4:
        #     break
    else:
        break

# sum the pixels inside the objects defined in filled_mask
sum = np.sum(all_mag, axis=0)
masked_sum = sum * filled_mask
well_sums = ndi_sum(masked_sum, lbl, range(1, objects + 1, 1))

# join the sums with the coordinate centers of each object
sum_df = pd.DataFrame(centers, columns=['y', 'x'])
sum_df['well_sum'] = well_sums
sum_df = well_names.merge(sum_df, on=['x', 'y'])

plt.imshow(masked_sum, cmap='inferno')
for index, row, in sum_df.iterrows():
    plt.text(row['x'] - 25, row['y'], int(row['well_sum']), fontsize=12, color='white')
plt.show()


# %% [markdown]
# # Schisto
# Try with schisto in a 6-well plate

# %%
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
from scipy import ndimage
from scipy.ndimage import sum as ndi_sum
from skimage.draw import circle_perimeter
from skimage.filters import sobel, threshold_triangle
from skimage.morphology import dilation, reconstruction
from skimage.transform import hough_circle, hough_circle_peaks

path = Path.home().joinpath('Desktop/19_30.av')

vid = cv2.VideoCapture(str(path))
ret = True
frames = []
while ret:
    ret, img = vid.read()
    if ret:
        frames.append(img)

array = np.stack(frames, axis=0)
ave = np.mean(array, axis=0)
ave_int = ave.astype(int)

plt.imshow(ave_int)
plt.show()

gry = cv2.cvtColor(ave.astype(np.float32), cv2.COLOR_BGR2GRAY)

edges = sobel(gry)

plt.imshow(edges, cmap='gray')
plt.show()


thresh = threshold_triangle(edges)
binary = edges > thresh

plt.imshow(binary, cmap='gray')
plt.show()


radii = np.arange(178, 182, 2)
hough_res = hough_circle(binary, radii)
accums, cx, cy, radii = hough_circle_peaks(
    hough_res, radii, total_num_peaks=400)

cy = np.ndarray.tolist(cy)
cx = np.ndarray.tolist(cx)
radii = np.ndarray.tolist(radii)


filtered_y = []
bad_indices = []
i = 0

for y in cy:
    if y < 200:
        bad_indices.append(i)
    elif y > 300 and y < 625:
        bad_indices.append(i)
    elif y > 750:
        bad_indices.append(i)
    else:
        i += 1

for i in bad_indices:
    cy.pop(i)
    cx.pop(i)
    radii.pop(i)

ave_int = ave.astype(int)

fig, ax = plt.subplots(ncols=1, nrows=1)
for center_y, center_x, radius in zip(cy, cx, radii):
    circy, circx = circle_perimeter(center_y, center_x, radius)
    ave_int[circy, circx] = (220, 20, 20)

plt.imshow(ave_int)
plt.show()

black = np.zeros(ave_int.shape[0:2])

for center_y, center_x, radius in zip(cy, cx, radii):
    circy, circx = circle_perimeter(center_y, center_x, radius)
    black[circy, circx] = 1

plt.imshow(black, cmap='gray')
plt.show()

closed = dilation(black)

plt.imshow(closed, cmap='gray')
plt.show()

seed = np.copy(closed)
seed[1:-1, 1:-1] = closed.max()
mask = closed

filled = reconstruction(seed, mask, method='erosion')

lbl, objects = ndimage.label(filled)
centers = ndimage.center_of_mass(filled, lbl, range(1, objects + 1, 1))
object_n = []
for x, y in centers:
    x = int(x)
    y = int(y)
    object_n.append(lbl[x, y])

mask = np.zeros(lbl.shape)
for x, y in centers:
    x = int(x)
    y = int(y)
    circy, circx = circle_perimeter(x, y, 180)
    mask[circy, circx] = 1

closed = dilation(mask)

seed = np.copy(closed)
seed[1:-1, 1:-1] = closed.max()
mask = closed

filled_mask = reconstruction(seed, mask, method='erosion')

plt.imshow(filled_mask, cmap='gray')
for i, center, in enumerate(centers):
    y, x = center
    plt.text(x, y, i, fontsize=12)
plt.show()


path = Path.home().joinpath('Desktop/19_30.avi')

vid = cv2.VideoCapture(str(path))

length = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
width = int(vid.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(vid.get(cv2.CAP_PROP_FRAME_HEIGHT))

vid_array = np.zeros((length, height, width))

# read first frame
ret, frame1 = vid.read()

# convert to gray scale
prvs = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
hsv = np.zeros_like(frame1)
hsv[..., 1] = 255
vid_array[0] = prvs

all_mag = np.zeros((length - 1, height, width))
# print(all_mag.shape)
count = 0
while(1):
    if count < length - 1:
        ret, frame2 = vid.read()
        next = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        vid_array[count + 1] = next
        flow = cv2.calcOpticalFlowFarneback(prvs, next, None, 0.5, 3, 15,
                                            3, 5, 1.2, 0)
        mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        prvs = next
        all_mag[count] = mag
        count += 1
        # for testing
        # if count > 4:
        #     break
    else:
        break

sum = np.sum(all_mag, axis=0)
masked_sum = sum * filled_mask
well_sums = ndi_sum(masked_sum, lbl, range(1, objects + 1, 1))

center_sums = []

for t, sum in zip(centers, well_sums):
    t = list(t)
    t.append(sum)
    center_sums.append(t)

plt.imshow(masked_sum, cmap='inferno')
for y, x, i in center_sums:
    plt.text(x, y, int(i), fontsize=12, ha='center', color='white')
plt.show()


# %% [markdown]
# # 96-well plate

# %%
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
from scipy import ndimage
from scipy.ndimage import sum as ndi_sum
from skimage.draw import circle_perimeter
from skimage.filters import sobel, threshold_triangle
from skimage.morphology import dilation, reconstruction
from skimage.transform import hough_circle, hough_circle_peaks

path = Path.home().joinpath('Desktop/20220622-p02-KTR.avi')

vid = cv2.VideoCapture(str(path))
ret = True
frames = []
while ret:
    ret, img = vid.read()
    if ret:
        frames.append(img)

array = np.stack(frames, axis=0)
ave = np.mean(array, axis=0)
ave_int = ave.astype(int)

plt.imshow(ave_int)
plt.show()

gry = cv2.cvtColor(ave.astype(np.float32), cv2.COLOR_BGR2GRAY)

edges = sobel(gry)

plt.imshow(edges, cmap='gray')
plt.show()


thresh = threshold_triangle(edges)
binary = edges > thresh

plt.imshow(binary, cmap='gray')
plt.show()


radii = np.arange(20, 25, 2)
hough_res = hough_circle(binary, radii)
accums, cx, cy, radii = hough_circle_peaks(
    hough_res, radii, total_num_peaks=5000)

cy = np.ndarray.tolist(cy)
cx = np.ndarray.tolist(cx)
radii = np.ndarray.tolist(radii)

filtered_y = []


bad_indices = []
i = 0

for x in cx:
    if x > 130 and x < 180:
        bad_indices.append(i)
    elif x > 220 and x < 270:
        bad_indices.append(i)
    elif x > 310 and x < 370:
        bad_indices.append(i)
    elif x > 390 and x < 470:
        bad_indices.append(i)
    elif x > 490 and x < 540:
        bad_indices.append(i)
    elif x > 590 and x < 640:
        bad_indices.append(i)
    elif x > 690 and x < 740:
        bad_indices.append(i)
    elif x > 790 and x < 840:
        bad_indices.append(i)
    elif x > 875 and x < 940:
        bad_indices.append(i)
    elif x > 960 and x < 1020:
        bad_indices.append(i)
    elif x > 1060 and x < 1120:
        bad_indices.append(i)
    else:
        i += 1

for i in bad_indices:
    cy.pop(i)
    cx.pop(i)
    radii.pop(i)

filtered_x = []
bad_indices = []
i = 0

for y in cy:
    if y > 50 and y < 90:
        bad_indices.append(i)
    elif y > 150 and y < 190:
        bad_indices.append(i)
    elif y > 230 and y < 280:
        bad_indices.append(i)
    elif y > 320 and y < 370:
        bad_indices.append(i)
    elif y > 420 and y < 470:
        bad_indices.append(i)
    elif y > 520 and y < 570:
        bad_indices.append(i)
    elif y > 620 and y < 670:
        bad_indices.append(i)
    else:
        i += 1

for i in bad_indices:
    cy.pop(i)
    cx.pop(i)
    radii.pop(i)

ave_int = ave.astype(int)

fig, ax = plt.subplots(ncols=1, nrows=1)
for center_y, center_x, radius in zip(cy, cx, radii):
    circy, circx = circle_perimeter(center_y, center_x, radius)
    ave_int[circy, circx] = (220, 20, 20)

plt.imshow(ave_int)
plt.show()

black = np.zeros(ave_int.shape[0:2])

for center_y, center_x, radius in zip(cy, cx, radii):
    circy, circx = circle_perimeter(center_y, center_x, radius)
    black[circy, circx] = 1

plt.imshow(black, cmap='gray')
plt.show()

closed = dilation(black)

plt.imshow(closed, cmap='gray')
plt.show()

seed = np.copy(closed)
seed[1:-1, 1:-1] = closed.max()
mask = closed

filled = reconstruction(seed, mask, method='erosion')

lbl, objects = ndimage.label(filled)
centers = ndimage.center_of_mass(filled, lbl, range(1, objects + 1, 1))
object_n = []
for x, y in centers:
    x = int(x)
    y = int(y)
    try:
        object_n.append(lbl[x, y])
    except IndexError:
        pass


mask = np.zeros(lbl.shape)
for x, y in centers:
    x = int(x)
    y = int(y)
    circy, circx = circle_perimeter(x, y, 180)
    try:
        mask[circy, circx] = 1
    except IndexError:
        pass

closed = dilation(mask)

seed = np.copy(closed)
seed[1:-1, 1:-1] = closed.max()
mask = closed

filled_mask = reconstruction(seed, mask, method='erosion')

plt.imshow(filled_mask, cmap='gray')
for i, center, in enumerate(centers):
    y, x = center
    plt.text(x, y, i, fontsize=12)
plt.show()


path = Path.home().joinpath('Desktop/19_30.avi')

vid = cv2.VideoCapture(str(path))

length = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
width = int(vid.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(vid.get(cv2.CAP_PROP_FRAME_HEIGHT))

vid_array = np.zeros((length, height, width))

# read first frame
ret, frame1 = vid.read()

# convert to gray scale
prvs = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
hsv = np.zeros_like(frame1)
hsv[..., 1] = 255
vid_array[0] = prvs

all_mag = np.zeros((length - 1, height, width))
# print(all_mag.shape)
count = 0
while(1):
    if count < length - 1:
        ret, frame2 = vid.read()
        next = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        vid_array[count + 1] = next
        flow = cv2.calcOpticalFlowFarneback(prvs, next, None, 0.5, 3, 15,
                                            3, 5, 1.2, 0)
        mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        prvs = next
        all_mag[count] = mag
        count += 1
        # for testing
        # if count > 4:
        #     break
    else:
        break

sum = np.sum(all_mag, axis=0)
masked_sum = sum * filled_mask
well_sums = ndi_sum(masked_sum, lbl, range(1, objects + 1, 1))

center_sums = []

for t, sum in zip(centers, well_sums):
    t = list(t)
    t.append(sum)
    center_sums.append(t)

plt.imshow(masked_sum, cmap='inferno')
for y, x, i in center_sums:
    plt.text(x, y, int(i), fontsize=12, ha='center', color='white')
plt.show()


# %%



