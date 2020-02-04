"""
MappApp ./Buffers.py - Buffer-objects for inter-process-communication
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

import ctypes
import cv2
import multiprocessing as mp
import numpy as np
from time import perf_counter
from sklearn import metrics

import Config
import Definition
from helper import Geometry
import IPC

################################
## Camera Buffer Object

class CameraBufferObject:
    """Camera Buffer Object: wrapper for individual buffers between FrameGrabber (producer)
    and any number of consumers.

    Consumers have to initially call constructBuffers() to be able to read data from buffers.
    """

    def __init__(self):
        self.dims = (int(Config.Camera[Definition.CameraConfig.resolution_y]),
                     int(Config.Camera[Definition.CameraConfig.resolution_x]))

        self._buffers = dict()
        self._npBuffers = dict()

    def addBuffer(self, buffer, **kwargs):
        self._buffers[buffer.__name__] = buffer(frameDims=self.dims, **kwargs)

    def constructBuffers(self):
        for name in self._buffers:
            self._npBuffers[name] = self._buffers[name].constructBuffer()

    def update(self, frame):
        for name in self._buffers:
            self._buffers[name].update(frame)

    def readBuffer(self, name):
        return self._buffers[name].readBuffer()

    def updateBufferEvalParams(self, name, **kwargs):
        if name in self._buffers:
            self._buffers[name].evalParamUpdate(**kwargs)

    def buffers(self):
        return self._buffers


################################
## Frame Buffers

## Basic Frame Buffer
class FrameBuffer:

    def __init__(self, frameDims, _useLock = True, _recordBuffer=True):
        self._recordBuffer = _recordBuffer

        # Set up lock
        self._useLock = _useLock
        self._lock = None
        if self._useLock:
            self._lock = mp.Lock()

        # Set up shared array (in parent process)
        self.frameDims = frameDims
        self._cBuffer = mp.Array(ctypes.c_uint8, frameDims[0] * frameDims[1] * 3, lock=self._useLock)
        self._npBuffer = None

        self.frametimes = list()
        self.t = perf_counter()

    def constructBuffer(self):
        """Construct the numpy buffer from the cArray pointer object

        :return: numpy buffer object to be used in child process instances
        """
        if self._npBuffer is None:
            if not(self._useLock):
                self._npBuffer = np.ctypeslib.as_array(self._cBuffer)
            else:
                self._npBuffer = np.ctypeslib.as_array(self._cBuffer.get_obj())
            self._npBuffer = self._npBuffer.reshape((*self.frameDims, 3))

        return self._npBuffer

    def readBuffer(self):
        if self._lock is not None:
            self._lock.acquire()
        buffer = self._npBuffer.copy()
        if self._lock is not None:
            self._lock.release()
        return buffer

    def evalParamUpdate(self, **kwargs):
        """Re-implement in subclass

        :param kwargs:
        :return:
        """
        pass

    def _format(self, frame):
        return np.rot90(frame, 2)

    def _out(self, newframe):
        """Write contents of newframe to the numpy buffer

        :param newframe:
        :return:
        """
        if self._lock is not None:
            self._lock.acquire()
        self._npBuffer[:,:,:] = newframe
        if self._lock is not None:
            self._lock.release()

    def _compute(self, frame):
        """Re-implement in subclass
        :param frame: AxB frame image data
        :return: new frame
        """

        newframe = frame.copy()
        if self.__class__.__name__ == 'FrameBuffer':
            # Add FPS counter
            self.frametimes.append(perf_counter() - self.t)
            self.t = perf_counter()
            fps = 1. / np.mean(self.frametimes[-20:])
            newframe[:40,:200,:] = 0.
            newframe = cv2.putText(newframe, 'FPS %.2f' % fps, (0, 25), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 255, 2)#.get()

        return newframe

    def update(self, frame):
        """Method to be called by producer (FramGrabber).
        Automatically calls the _compute method and passes the result to _out.

        Ususally this method will be called implicitly by calling the Camera Buffer Object's update method.

        :param frame: new frame to be processed and written to buffer
        :return: None
        """
        self._out(self._compute(frame))


################
## Custom Frame Buffers

class EyePositionDetector(FrameBuffer):

    def __init__(self, *args, **kwargs):
        FrameBuffer.__init__(self, *args, **kwargs)

        self.recording = False

        self.eyeMarkerLines = IPC.Manager.dict()
        self.eyeMarkerRects = IPC.Manager.dict()
        self.segmentationMode = IPC.Manager.Value('s', '')
        self.areaThreshold = IPC.Manager.Value('i', 0)

    def default(self, rect):

        ################
        ### Right eye
        re = rect[:,int(rect.shape[1]/2):,:]
        _, rethresh = cv2.threshold(re[:,:,0], 60, 255, cv2.THRESH_BINARY_INV)
        recnts, _ = cv2.findContours(rethresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        recnt = np.array([])
        for cnt in recnts:
            if cnt.shape[0] > recnt.shape[0]:
                recnt = cnt.squeeze()

        # TODO: THIS is a pure PERFORMANCE KILLER!
        #       Need to somehow reduce the number of potential contour points for
        #       calculation of Feret diameter
        #       (Restricting to upper/lower distances already helps a lot. Can this be done better?)

        if True:  # Upper/lower restriction
            upperPoints = recnt[recnt[:,1] > rect.shape[0]/2,:]
            lowerPoints = recnt[recnt[:, 1] < rect.shape[0] / 2, :]
            dists = metrics.pairwise_distances(upperPoints, lowerPoints)
            maxIdcs = np.unravel_index(dists.argmax(), dists.shape)
            p1 = upperPoints[maxIdcs[0]]
            p1[0] += int(rect.shape[1]/2)
            p2 = lowerPoints[maxIdcs[1]]
            p2[0] += int(rect.shape[1]/2)
        else:
            dists = metrics.pairwise_distances(recnt)
            maxIdcs = np.unravel_index(dists.argmax(), dists.shape)
            p1 = recnt[maxIdcs[0]]
            p1[0] += int(rect.shape[1]/2)
            p2 = recnt[maxIdcs[1]]
            p2[0] += int(rect.shape[1]/2)

        if p1[1] > p2[1]:
            p0 = p2
            p2 = p1
            p1 = p0
        axis = p1-p2
        perpAxis = Geometry.vecNormalize(np.array([axis[1], -axis[0]]))
        reangle = np.arccos(np.dot(Geometry.vecNormalize(np.array([0.0, 1.0])),
                                   perpAxis))

        ## Connection line
        cv2.line(rect, tuple(p1), tuple(p2), (0, 0, 255), 1)
        cv2.drawMarker(rect, tuple(p1), (0, 0, 255), cv2.MARKER_CROSS, 4)
        cv2.drawMarker(rect, tuple(p2), (0, 0, 255), cv2.MARKER_CROSS, 4)

        ### Perpendicular line
        cv2.line(rect, tuple(p2), tuple((p2 - 0.2 * np.linalg.norm(axis) * perpAxis).astype(int)), (0, 0, 255), 1)


        ################
        ### Left eye
        le = rect[:,:int(rect.shape[1]/2),:]

        _, lethresh = cv2.threshold(le[:,:,0], 60, 255, cv2.THRESH_BINARY_INV)
        lecnts, _ = cv2.findContours(lethresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        lecnt = np.array([])
        for cnt in lecnts:
            if cnt.shape[0] > lecnt.shape[0]:
                lecnt = cnt.squeeze()

        if True:  # Upper/lower restriction
            upperPoints = recnt[recnt[:,1] > rect.shape[0]/2,:]
            lowerPoints = recnt[recnt[:, 1] < rect.shape[0] / 2, :]
            dists = metrics.pairwise_distances(upperPoints, lowerPoints)
            maxIdcs = np.unravel_index(dists.argmax(), dists.shape)
            p1 = upperPoints[maxIdcs[0]]
            p2 = lowerPoints[maxIdcs[1]]
        else:
            dists = metrics.pairwise_distances(lecnt)
            maxIdcs = np.unravel_index(dists.argmax(), dists.shape)
            p1 = lecnt[maxIdcs[0]]
            p2 = lecnt[maxIdcs[1]]

        if p1[1] > p2[1]:
            p0 = p2
            p2 = p1
            p1 = p0

        axis = p1-p2
        perpAxis = Geometry.vecNormalize(np.array([axis[1], -axis[0]]))
        leangle = np.arccos(np.dot(Geometry.vecNormalize(np.array([0.0, 1.0])),
                                   perpAxis))

        ## Connection line
        cv2.line(rect, tuple(p1), tuple(p2), (0, 255, 0), 1)
        cv2.drawMarker(rect, tuple(p1), (0, 255, 0), cv2.MARKER_CROSS, 4)
        cv2.drawMarker(rect, tuple(p2), (0, 255, 0), cv2.MARKER_CROSS, 4)

        ### Perpendicular line
        cv2.line(rect, tuple(p2), tuple((p2 + 0.2 * np.linalg.norm(axis) * perpAxis).astype(int)), (0, 255, 0), 1)


        #cv2.imwrite('meh/testX.jpg', rect)

    def watershed(self, frame):

        img = np.repeat(frame[:,:,np.newaxis], 3, axis=-1)
        ret, thresh = cv2.threshold(frame, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # noise removal
        kernel = np.ones((3, 3), np.uint8)
        opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)

        # sure background area
        sure_bg = cv2.dilate(opening, kernel, iterations=3)

        # Finding sure foreground area
        dist_transform = cv2.distanceTransform(opening, cv2.DIST_L2, 5)
        ret, sure_fg = cv2.threshold(dist_transform, 0.7 * dist_transform.max(), 255, 0)

        # Finding unknown region
        sure_fg = np.uint8(sure_fg)
        unknown = cv2.subtract(sure_bg, sure_fg)

        # Marker labelling
        ret, markers = cv2.connectedComponents(sure_fg)

        # Add one to all labels so that sure background is not 0, but 1
        markers = markers + 1

        # Now, mark the region of unknown with zero
        markers[unknown == 255] = 0

        markers = cv2.watershed(img, markers)
        newframe = (markers == -1) * 255

        return newframe

    def coordsPg2Cv(self, point, asType : type = np.float32):
        return [asType(point[0]), asType(Config.Camera[Definition.CameraConfig.resolution_y] - point[1])]

    def _grab(self, frame):
        if self.recording:
            pass
        return frame

    def _compute(self, frame):

        newframe = frame.copy()
        ret, threshed = cv2.threshold(newframe[:, :, 0], 60, 255, cv2.THRESH_BINARY_INV)

        ### If eyes were marked: iterate over rects and extract eye positions
        if bool(self.eyeMarkerRects):

            for i, rectParams in self.eyeMarkerRects.items():

                ## Draw contour points of rect
                rect = (tuple(self.coordsPg2Cv(rectParams[0])), tuple(rectParams[1]), -rectParams[2],)
                box = cv2.boxPoints(rect)
                box = np.int0(box)
                cv2.drawContours(newframe, [box], 0, (255, 0, 0), 2)

                ## Get rect and frame parameters
                center, size, angle = rect[0], rect[1], rect[2]
                center, size = tuple(map(int, center)), tuple(map(int, size))
                height, width = newframe.shape[0], newframe.shape[1]

                ## Rotate
                M = cv2.getRotationMatrix2D(center, angle, 1)
                rotFrame = cv2.warpAffine(newframe, M, (width, height))

                ## Crop rect from frame
                cropRect = cv2.getRectSubPix(rotFrame, size, center)

                ## Rotate rect so that "up" direction in image corresponds to "foward" for the fish
                center = (size[0]/2, size[1]/2)
                width, height = size
                M = cv2.getRotationMatrix2D(center, 90, 1)
                absCos = abs(M[0, 0])
                absSin = abs(M[0, 1])

                # New bound width/height
                wBound = int(height * absSin + width * absCos)
                hBound = int(height * absCos + width * absSin)

                # Subtract old image center
                M[0, 2] += wBound / 2 - center[0]
                M[1, 2] += hBound / 2 - center[1]
                # Rotate
                rotRect = cv2.warpAffine(cropRect, M, (wBound, hBound))

                ## Apply detection function on cropped rect which contains eyes
                if self.segmentationMode.value == 'default' or self.segmentationMode.value == '':
                    self.default(self._grab(rotRect))

                elif self.segmentationMode.value == 'watershed':
                    self.watershed(self._grab(rotRect))

                elif self.segmentationMode.value == 'blob_detect':
                    detector = cv2.SimpleBlobDetector()
                    keypoints = detector.detect(newframe[:, :, 0])
                    newframe = cv2.drawKeypoints(newframe, keypoints, np.array([]), (0, 0, 255),
                                                 cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

                # Debug: write to file
                cv2.imwrite('meh/test{}.jpg'.format(i), rotRect)

        ### Mark filtered particles in red
        newframe[threshed > 0, :] = [255, 0, 0]

        ### Convert to OpenCV image coordinates
        lines = dict()
        for id, line in self.eyeMarkerLines.items():
            lines[id] = [tuple(self.coordsPg2Cv(line[0], asType=np.int)),
                        tuple(self.coordsPg2Cv(line[1], asType=np.int))]

        ### Just for illustration: plot lines
        for id, line in lines.items():
            newframe = cv2.line(newframe,
                     line[0],
                     line[1],
                     (0, 255, 0), 6)

        return newframe

