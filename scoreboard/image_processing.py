from collections import defaultdict
import imageio
import numpy as np

MAX_COMP = 50
N_SUPPORT = 20
NOTE_RADIUS_X, NOTE_RADIUS_Y = 10, 10

def index_image(path):
    print(path)
    im = imageio.imread(path)

    # Ignore alpha channel
    im = im[:, :, :3]

    # Mark noise entries
    mask = (np.min(im, axis=2) == 0) | (np.max(im, axis=2) > MAX_COMP)
    # Use one number for each colour
    im = im[:, :, 0] * 2**16 + im[:, :, 1] * 2**8 + im[:, :, 2]

    colour_map = defaultdict(list)
    for y, x in zip(*np.where(~mask)):
        colour = im[y, x]
        colour_map[colour].append((x, y))

    result = {}

    for colour, points in colour_map.items():
        if len(points) < N_SUPPORT: continue

        points = np.array(points)
        cx = points[len(points) // 2, 0]
        cy = points[len(points) // 2, 1]

        points = points[(np.abs(points[:, 0] - cx) <= NOTE_RADIUS_X) &
                        (np.abs(points[:, 1] - cy) <= NOTE_RADIUS_Y)]
        if len(points) < N_SUPPORT: continue

        rects = []
        if len(points):
            x1, y1 = points[0]
            x2 = points[0][0]
            for x, y in points[1:]:
                if y != y1:
                    rects.append([int(i) for i in [x1, y1, x2 - x1 + 1, 1]])
                    x1, y1 = x, y
                x2 = x
            rects.append([int(i) for i in [x1, y1, x2 - x1 + 1, 1]])

        result['#{:06X}'.format(colour)] = {
            'cx': int(cx),
            'cy': int(cy),
            'rects': rects
            }

    return result
