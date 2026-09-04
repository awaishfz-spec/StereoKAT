import ir_marker
from pprint import pprint
import numpy as np

def cart2pol(x, y):
    rho = np.sqrt(x**2 + y**2)
    phi = np.arctan2(y, x)
    return(rho, phi)

def pol2cart(rho, phi):
    x = rho * np.cos(phi)
    y = rho * np.sin(phi)
    return(x, y)

offset_angle = 45

markers = [{'name': "A", 'pos': (649.5,657.5), 'radius': 1, 'center': (0,0), 'compactness': 1},
           {'name': "B", 'pos': (729.5, 649.5), 'radius': 1, 'center': (1,0), 'compactness': 1},
           {'name': "C", 'pos': (666, 540.5), 'radius': 1, 'center': (1,0), 'compactness': 1}]

last_markers = [{'name': "A", 'pos': (650,658), 'radius': 1, 'center': (0,0), 'compactness': 1},
                {'name': "B", 'pos': (666.6429, 539.9286), 'radius': 1, 'center': (1,0), 'compactness': 1},
                {'name': "C", 'pos': (729.5, 649.5), 'radius': 1, 'center': (1,0), 'compactness': 1}]

x = np.array([i['pos'][0] for i in markers])
y = np.array([i['pos'][1] for i in markers])

r, phi = cart2pol(x, y)

new_ang = phi + np.pi * offset_angle / 180
x_new, y_new = pol2cart(r, new_ang)

# order by new x position after rotation
markers = [marker for _, marker in sorted(zip(x_new, markers))]

pprint(markers)