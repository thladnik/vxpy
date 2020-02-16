
import cv2
import numpy as np
from sklearn import metrics

from Buffer import FrameBuffer
import Config
import Definition
from helper import Geometry
import IPC

class EyePositionDetector(FrameBuffer):

    def __init__(self, *args, **kwargs):
        FrameBuffer.__init__(self, *args, **kwargs)

        self.recording = False

        self.extractedRects = IPC.Manager.dict()
        self.eyePositions = IPC.Manager.list()
        self.eyeMarkerRects = IPC.Manager.dict()
        self.segmentationMode = IPC.Manager.Value('s', '')
        self.areaThreshold = IPC.Manager.Value('i', 0)

    def default(self, rect):
        """Default function for extracting fish eyes' angular position.

        :param rect: 2d image (usually the rectangular ROI around the eyes)
                     which contains both of the fish's eyes. Upward image direction -> forward fish direction
        :return: modified 2d image
        """

        ### Subdivide into left and right eye rectangles
        re = rect[:,int(rect.shape[1]/2):,:]
        le = rect[:,:int(rect.shape[1]/2),:]

        ################
        ### Extract right eye angular position
        _, reThresh = cv2.threshold(re[:,:,0], 60, 255, cv2.THRESH_BINARY_INV)
        reCnts, _ = cv2.findContours(reThresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

        if len(reCnts) == 0:
            return rect

        reCnt = None
        if len(reCnts) > 1:
            for cnt in reCnts:
                if cnt.shape[0] < 5:
                    continue
                if reCnt is None or cv2.contourArea(cnt) > cv2.contourArea(reCnt):
                    reCnt = cnt.squeeze()

        if reCnt is None:
            return rect

        reCntSort = reCnt[reCnt[:, 1].argsort()]
        upperPoints = reCntSort[-reCntSort.shape[0] // 3:, :]
        lowerPoints = reCntSort[:reCntSort.shape[0] // 3, :]

        ### Draw contour points
        for i in range(upperPoints.shape[0]):
            p = upperPoints[i,:].copy()
            p[0] += rect.shape[1]//2
            cv2.drawMarker(rect, tuple(p), (0, 255, 0), cv2.MARKER_DIAMOND, 3)

        for i in range(lowerPoints.shape[0]):
            p = lowerPoints[i,:].copy()
            p[0] += rect.shape[1]//2
            cv2.drawMarker(rect, tuple(p), (0, 0, 255), cv2.MARKER_DIAMOND, 3)

        if upperPoints.shape[0] < 2 or lowerPoints.shape[0] < 2:
            return rect

        dists = metrics.pairwise_distances(upperPoints, lowerPoints)
        maxIdcs = np.unravel_index(dists.argmax(), dists.shape)
        p1 = lowerPoints[maxIdcs[1]]
        p1[0] += int(rect.shape[1]/2)
        p2 = upperPoints[maxIdcs[0]]
        p2[0] += int(rect.shape[1]/2)

        axis = p1-p2
        perpAxis = -Geometry.vecNormalize(np.array([axis[1], -axis[0]]))
        reAngle = np.arccos(np.dot(Geometry.vecNormalize(np.array([0.0, 1.0])), perpAxis)) - np.pi/2

        ## Display axis
        cv2.line(rect, tuple(p1), tuple(p2), (255, 128, 0), 1)
        cv2.drawMarker(rect, tuple(p1), (255, 0, 0), cv2.MARKER_CROSS, 4)
        cv2.drawMarker(rect, tuple(p2), (255, 0, 0), cv2.MARKER_CROSS, 4)

        ## Display perpendicular axis
        cv2.line(rect, tuple(p2), tuple((p2 + 0.75 * reAngle * np.linalg.norm(axis) * perpAxis).astype(int)), (255, 128, 0), 1)


        ################
        ### Extract left eye angular position
        _, leThresh = cv2.threshold(le[:,:,0], 60, 255, cv2.THRESH_BINARY_INV)
        leCnts, _ = cv2.findContours(leThresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

        if len(leCnts) == 0:
            return rect

        leCnt = None
        if len(leCnts) > 1:
            for cnt in leCnts:
                if cnt.shape[0] < 5:
                    continue
                if leCnt is None or cv2.contourArea(cnt) > cv2.contourArea(leCnt):
                    leCnt = cnt.squeeze()

        if leCnt is None:
            return rect

        leCntSort = leCnt[leCnt[:, 1].argsort()]
        upperPoints = leCntSort[-leCntSort.shape[0] // 3:, :]
        lowerPoints = leCntSort[:leCntSort.shape[0] // 3, :]

        ### Draw detected contour points
        ## Upper part
        for i in range(upperPoints.shape[0]):
            cv2.drawMarker(rect, tuple(upperPoints[i,:]), (0, 255, 0), cv2.MARKER_DIAMOND, 3)
        ## Lower part
        for i in range(lowerPoints.shape[0]):
            cv2.drawMarker(rect, tuple(lowerPoints[i,:]), (0, 0, 255), cv2.MARKER_DIAMOND, 3)

        ## Return if thete are to few contour points
        if upperPoints.shape[0] < 2 or lowerPoints.shape[0] < 2:
            return rect

        ### Calculate distances between upper and lower points and find longest axis
        dists = metrics.pairwise_distances(upperPoints, lowerPoints)
        maxIdcs = np.unravel_index(dists.argmax(), dists.shape)
        p1 = lowerPoints[maxIdcs[1]]
        p2 = upperPoints[maxIdcs[0]]

        ### Calculate axes and angular eye position
        axis = p1-p2
        perpAxis = Geometry.vecNormalize(np.array([axis[1], -axis[0]]))
        leAngle = np.arccos(np.dot(Geometry.vecNormalize(np.array([0.0, 1.0])), perpAxis)) - np.pi/2

        ### Mark orientation axes
        ## Display axis
        cv2.line(rect, tuple(p1), tuple(p2), (255, 255, 0), 1)
        cv2.drawMarker(rect, tuple(p1), (255, 0, 0), cv2.MARKER_CROSS, 4)
        cv2.drawMarker(rect, tuple(p2), (255, 0, 0), cv2.MARKER_CROSS, 4)
        ## Display perpendicular axis
        cv2.line(rect, tuple(p2), tuple((p2 + 0.75 * leAngle * np.linalg.norm(axis) * perpAxis).astype(int)), (255, 255, 0), 1)

        ### Append angular eye positions to shared list
        self.eyePositions.append([leAngle, reAngle])

        return rect

    def coordsPg2Cv(self, point, asType : type = np.float32):
        return [asType(point[0]), asType(Config.Camera[Definition.Camera.res_y] - point[1])]

    def _grab(self, frame):
        if self.recording:
            pass
        return frame

    def _compute(self, frame):

        newframe = frame.copy()

        ### If eyes were marked: iterate over rects and extract eye positions
        if bool(self.eyeMarkerRects):

            for id, rectParams in self.eyeMarkerRects.items():

                ## Draw contour points of rect
                rect = (tuple(self.coordsPg2Cv(rectParams[0])), tuple(rectParams[1]), -rectParams[2],)
                # For debugging: draw rectangle
                #box = cv2.boxPoints(rect)
                #box = np.int0(box)
                #cv2.drawContours(newframe, [box], 0, (255, 0, 0), 1)

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
                if self.segmentationMode.value == 'something':
                    newRect = []
                    #newRect = self.watershed(self._grab(rotRect))
                else:  # default
                    newRect = self.default(self._grab(rotRect))

                # Debug: write to file
                #cv2.imwrite('meh/test{}.jpg'.format(id), rotRect)

                self.extractedRects[id] = newRect

        return newframe

class TailDeflectionDetector(FrameBuffer):

    def __init__(self, *args, **kwargs):
        FrameBuffer.__init__(self, *args, **kwargs)

        self.recording = False

        self.fishMarkerRects = IPC.Manager.dict()
        self.extractedRects = IPC.Manager.dict()
        self.tailDeflectionAngles = IPC.Manager.list()

    def _grab(self, frame):
        if self.recording:
            pass
        return frame

    def coordsPg2Cv(self, point, asType : type = np.float32):
        return [asType(point[0]), asType(Config.Camera[Definition.Camera.res_y] - point[1])]

    def default(self, rect):

        _, thresh = cv2.threshold(rect, 130, 255, cv2.THRESH_BINARY)


        return thresh

    def _compute(self, frame):
        newframe = frame.copy()

        ### If fish were marked: iterate over rects and extract tail deflection angles
        if bool(self.fishMarkerRects):

            for id, rectParams in self.fishMarkerRects.items():

                ## Draw contour points of rect
                rect = (tuple(self.coordsPg2Cv(rectParams[0])), tuple(rectParams[1]), -rectParams[2],)
                # For debugging: draw rectangle
                #box = cv2.boxPoints(rect)
                #box = np.int0(box)
                #cv2.drawContours(newframe, [box], 0, (255, 0, 0), 1)

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
                newRect = self.default(self._grab(rotRect))

                # Debug: write to file
                #cv2.imwrite('meh/test{}.jpg'.format(id), rotRect)

                self.extractedRects[id] = newRect

        return newframe