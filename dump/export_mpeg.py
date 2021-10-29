import cv2
import h5py
import numpy as np

folderpath = '../output/rec_2020-04-06-15-33-25'

f = h5py.File('{}/Camera.hdf5'.format(folderpath), 'r')

vid = f['FrameBuffer/frame'][:]
out = cv2.VideoWriter('{}/output.mpeg'.format(folderpath),
                      cv2.VideoWriter_fourcc(*'MP42'), 10, (vid.shape[2], vid.shape[1]), True)

for i in range(vid.shape[0]):
    frame = vid[i,:,:,:]
    out.write(np.flip(frame,0))

f.close()