"""
MappApp ./dump/Demo1DGlider3Point.py - Animation of 3 point glider stimulus for demonstration.

Similar to the ones used in
*
Clark DA, Fitzgerald JE, Ales JM, et al. (2014) Nat Neurosci.
Flies and humans share a motion estimation strategy that exploits natural scene statistics.
doi:10.1038/nn.3600
*
Fitzgerald JE, Clark DA. (2015) Elife
Nonlinear circuits for naturalistic visual motion estimation.
doi:10.7554/eLife.09123

Copyright (C) 2020 Tim Hladnik

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

### Seed
np.random.seed(123)

################
### Setup

order = 3  # 2 or 3

parity = 'even'  # 'odd' or 'even'
mode = 'conv'  # for 3-point: 'div' or 'conv'

stripe_num = 40
seed_row = np.random.randint(0, 2, stripe_num)
frame_num = 100


################
### Calculate

def calcParity(values, rule):
    if rule == 'even':
        return np.sum(values) % 2
    elif rule == 'odd':
        return not (np.sum(values) % 2)


rows = np.ones((frame_num, stripe_num))
rows *= np.nan
rows[0, :] = seed_row
for i in range(1, frame_num):

    ### Seed for new frame
    rows[i, 0] = np.random.randint(0, 2)

    for j in range(1, stripe_num):

        if order == 2:
            rows[i, j] = calcParity(rows[i - 1, j - 1], parity)
        elif order == 3:
            if mode == 'conv':
                rows[i, j] = calcParity((rows[i - 1, j - 1], rows[i - 1, j]), parity)
            elif mode == 'div':
                rows[i, j] = calcParity((rows[i - 1, j - 1], rows[i, j - 1]), parity)

################
### Plot and save

plot = False
save = True


def init():
    ax1.set_aspect('auto')
    ax1.set_ylabel('Elevation')
    ax1.set_xlabel('Azimuth [a.u.]')
    ax1.set_yticks([])

    ax1.imshow(rows[0, :] * np.ones((20, 1)), cmap='Greys')

    ax2.set_ylabel('Frame #')
    ax2.set_xlabel('Azimuth [a.u.]')

    ax2.imshow(rows, cmap='Greys')

    fig.tight_layout()
    return ax1, ax2


def update(frame_idx):
    cur = rows.copy()
    cur[frame_idx + 1:, :] = np.nan

    ax1.images[0].set_data(cur[frame_idx, :].reshape((1, -1)))
    ax2.images[0].set_data(cur)


### Setup
fig = plt.figure(figsize=(13, 5))
gs = fig.add_gridspec(1, 4)
ax1 = fig.add_subplot(gs[:3])
ax2 = fig.add_subplot(gs[3])

### Start animation
ani = animation.FuncAnimation(fig, update, frames=frame_num, init_func=init, interval=(20 if plot else 1))

if plot:
    plt.show()

if save:
    if order == 2:
        filename = 'Demo_1DGlider2Point_Par_{}.mp4'.format(parity)
    elif order == 3:
        filename = 'Demo_1DGlider3Point_Pol_{}_Mode_{}.mp4'.format(parity, mode)

    print('Save to {}...'.format(filename))
    writer = animation.FFMpegWriter(fps=10)
    ani.save(filename, writer)


################
### HRC

def hrc(i1, i2, t, tau):
    pass
