"""
MappApp ./routines/CameraRoutines.py - Custom processing routine implementations for the camera process.
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
import cv2
import numpy as np
from sklearn import metrics
from scipy.spatial import distance
from time import perf_counter, time
# TODO: remove scikit-learn, unnecessarily large dependency
#  and only used by old eye detection

from Routine import AbstractRoutine, ArrayAttribute, ArrayDType, ObjectAttribute
import Config
import Def
from helper import Geometry
import IPC
import routines.io.IoRoutines

class FrameRoutine(AbstractRoutine):

    def __init__(self, *args, **kwargs):
        AbstractRoutine.__init__(self, *args, **kwargs)

        self.device_list = list(zip(Config.Camera[Def.CameraCfg.device_id],
                                    Config.Camera[Def.CameraCfg.res_x],
                                    Config.Camera[Def.CameraCfg.res_y]))

        target_fps = Config.Camera[Def.CameraCfg.fps]

        # Set up buffer frame attribute for each camera device
        for device_id, res_x, res_y in self.device_list:
            array_attr = ArrayAttribute((res_y, res_x), ArrayDType.uint8, length=2*target_fps)
            setattr(self.buffer, '{}_frame'.format(device_id), array_attr)


    def _compute(self, **frames):

        for device_id, frame in frames.items():

            if frame is None:
                continue

            # Update shared attributes
            if frame.ndim > 2:
                getattr(self.buffer, f'{device_id}_frame').write(frame[:, :, 0])
            else:
                getattr(self.buffer, f'{device_id}_frame').write(frame[:, :])

    def _out(self):
        for device_id, _, _ in self.device_list:
            frame_attr_name = f'{device_id}_frame'
            _, time, frame = getattr(self.buffer, frame_attr_name).read(0)
            yield frame_attr_name, time[0], frame[0]


class EyePosDetectRoutine(AbstractRoutine):

    camera_device_id = 'behavior'
    extracted_rect_prefix = 'extracted_rect_'
    ang_le_pos_prefix = 'angular_le_pos_'
    ang_re_pos_prefix = 'angular_re_pos_'
    le_sacc_prefix = 'le_saccade_'
    re_sacc_prefix = 're_saccade_'
    roi_maxnum = 10

    def __init__(self, *args, **kwargs):
        AbstractRoutine.__init__(self, *args, **kwargs)

        # Set accessible methods
        self.exposed.append(EyePosDetectRoutine.set_threshold)
        self.exposed.append(EyePosDetectRoutine.set_max_im_value)
        self.exposed.append(EyePosDetectRoutine.set_min_particle_size)
        self.exposed.append(EyePosDetectRoutine.set_roi)
        self.exposed.append(EyePosDetectRoutine.set_detection_mode)
        self.exposed.append(EyePosDetectRoutine.set_saccade_threshold)

        # Set required devices
        self.required.append(self.camera_device_id)

        # Get camera specs
        assert self.camera_device_id in Config.Camera[Def.CameraCfg.device_id], \
            f'Camera device "{self.camera_device_id}" not configured for {self.__class__.__name__}'
        idx = Config.Camera[Def.CameraCfg.device_id].index(self.camera_device_id)
        self.res_x = Config.Camera[Def.CameraCfg.res_x][idx]
        self.res_y = Config.Camera[Def.CameraCfg.res_y][idx]
        target_fps = Config.Camera[Def.CameraCfg.fps]

        # Set up parameter variables (accessible externally)
        self.rois = dict()
        self.thresh = None
        self.min_size = None
        self.maxvalue = None
        self.detection_mode = None
        self.saccade_threshold = 10#None

        # Set up buffer attributes
        length = 1000
        for id in range(self.roi_maxnum):
            setattr(self.buffer, f'{self.extracted_rect_prefix}{id}', ObjectAttribute())
            setattr(self.buffer, f'{self.ang_le_pos_prefix}{id}', ArrayAttribute(size=(1,), dtype=ArrayDType.float64, length=length))
            setattr(self.buffer, f'{self.ang_re_pos_prefix}{id}', ArrayAttribute(size=(1,), dtype=ArrayDType.float64, length=length))
            setattr(self.buffer, f'{self.le_sacc_prefix}{id}', ArrayAttribute(size=(1,), dtype=ArrayDType.float64, length=length))
            setattr(self.buffer, f'{self.re_sacc_prefix}{id}', ArrayAttribute(size=(1,), dtype=ArrayDType.float64, length=length))
        self.buffer.frame = ArrayAttribute((self.res_y, self.res_x),
                                           ArrayDType.uint8,
                                           length=2*target_fps)

    def set_detection_mode(self, mode):
        self.detection_mode = mode

    def set_threshold(self, thresh):
        self.thresh = thresh

    def set_max_im_value(self, value):
        self.maxvalue = value

    def set_min_particle_size(self, size):
        self.min_size = size

    def set_roi(self, id, params):
        self.rois[id] = params

    def set_saccade_threshold(self, thresh):
        self.saccade_threshold = thresh

    def feret_diameter(self, rect):
        """Method for extracting angular fish eye position estimates using the Feret diameter.

        :param rect: 2d image which contains both of the fish's eyes.
                     Upward image direction if assumed to be forward fish direction.
                     Rect center is assumed to be located between both eyes.

        :return:
            angular eye positions for left and right eye in degree
            modified 2d image for parameter debugging
        """

        # Formatting for drawing
        line_thickness = np.ceil(np.mean(rect.shape) / 100).astype(int)
        line_thickness = 1 if line_thickness == 0 else line_thickness
        marker_size = line_thickness * 5

        # Set rect center
        rect_center = (rect.shape[1] // 2, rect.shape[0] // 2)

        # Apply threshold
        _, thresh = cv2.threshold(rect[:,:], self.thresh, self.maxvalue, cv2.THRESH_BINARY_INV)

        # Detect contours
        cnts, hierarchy = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

        # Make RGB
        thresh = np.stack((thresh, thresh, thresh), axis=-1)

        # Collect contour parameters and filter contours
        areas = list()
        centroids = list()
        hulls = list()
        feret_points = list()
        dists = list()
        i = 0
        while i < len(cnts):

            cnt = cnts[i]
            M = cv2.moments(cnt)
            A = M['m00']

            # Discard if contour has no area
            if A < self.min_size:
                del cnts[i]
                continue

            center = (int(M['m10']/A), int(M['m01']/A))
            hull = cv2.convexHull(cnt).squeeze()

            areas.append(A)
            centroids.append(center)
            dists.append(distance.euclidean(center, rect_center))
            hulls.append(hull)

            feret_points.append((hull[np.argmin(hull[:,1])], hull[np.argmax(hull[:,1])]))

            i += 1


        # Additional filtering of particles to idenfity both eyes if more than 2
        if len(cnts) > 2:
            dists, areas, centroids, hulls, feret_points = list(zip(*sorted(list(zip(dists,
                                                                                     areas,
                                                                                     centroids,
                                                                                     hulls,
                                                                                     feret_points)))[:2]))




        forward_vec = np.array([0,-1])
        forward_vec_norm = forward_vec / np.linalg.norm(forward_vec)
        # Draw rect center and midline marker for debugging
        # (Important: this has to happen AFTER detection of contours,
        # as it alters the tresh'ed image)
        cv2.drawMarker(thresh, rect_center, (0, 255, 0), cv2.MARKER_DIAMOND, marker_size * 2, line_thickness)
        cv2.arrowedLine(thresh,
                        tuple(rect_center), tuple((rect_center + rect.shape[0]/3 * forward_vec_norm).astype(int)),
                        (0, 255, 0), line_thickness, tipLength=0.3)

        # Draw hull contours for debugging (before possible premature return)
        cv2.drawContours(thresh, hulls, -1, (128,128,0), line_thickness)

        # If less than two particles, return
        if len(cnts) < 2:
            return None, thresh

        # At this point there should only be 2 particles left
        le_idx = 0 if (centroids[0][0] < rect_center[0]) else 1
        re_idx = 1 if (centroids[0][0] < rect_center[0]) else 0


        le_axis = feret_points[le_idx][0] - feret_points[le_idx][1]
        le_axis_norm = le_axis / np.linalg.norm(le_axis)
        le_ortho = np.array([le_axis_norm[1], -le_axis_norm[0]])
        re_axis = feret_points[re_idx][0] - feret_points[re_idx][1]
        re_axis_norm = re_axis / np.linalg.norm(re_axis)
        re_ortho = np.array([-re_axis_norm[1], re_axis_norm[0]])

        # Calculate angles
        # LE
        le_ref_norm = np.array([forward_vec_norm[1], forward_vec_norm[0]])
        le_ortho_norm = le_ortho / np.linalg.norm(le_ortho)
        le_angle = np.arcsin(np.cross(le_ortho_norm, le_ref_norm)) / (2 * np.pi) * 360
        # RE
        re_ref_norm = np.array([-forward_vec_norm[1], forward_vec_norm[0]])
        re_ortho_norm = re_ortho / np.linalg.norm(re_ortho)
        re_angle = np.arcsin(np.cross(re_ortho_norm, re_ref_norm)) / (2 * np.pi) * 360

        # Draw eyes and axes

        # LE
        # Feret diameter
        cv2.line(thresh, tuple(feret_points[le_idx][0]), tuple(feret_points[le_idx][1]), (0, 0, 255), line_thickness)
        # Eye center of mass
        cv2.drawMarker(thresh, centroids[le_idx], (0, 0, 255), cv2.MARKER_CROSS, marker_size, line_thickness)
        # Reference
        le_draw_ref = tuple((np.array(rect_center) + le_ref_norm * 0.5 * np.linalg.norm(le_axis)).astype(int))
        cv2.line(thresh, rect_center, le_draw_ref, (0, 255, 0), line_thickness)
        # Ortho to feret
        le_draw_ortho = tuple((np.array(rect_center) + le_ortho * 0.5 * np.linalg.norm(le_axis)).astype(int))
        cv2.line(thresh, rect_center, le_draw_ortho, (0, 0, 255), line_thickness)

        # RE
        # Feret diameter
        cv2.line(thresh, tuple(feret_points[re_idx][0]), tuple(feret_points[re_idx][1]), (255, 0, 0), line_thickness)
        # Eye center of mass
        cv2.drawMarker(thresh, centroids[re_idx], (255, 0, 0), cv2.MARKER_CROSS, marker_size, line_thickness)
        # Reference
        re_draw_ref = tuple((np.array(rect_center) + re_ref_norm * 0.5 * np.linalg.norm(re_axis)).astype(int))
        cv2.line(thresh, rect_center, re_draw_ref, (0, 255, 0), line_thickness)
        # Ortho to feret
        re_draw_ortho = tuple((np.array(rect_center) + re_ortho * 0.5 * np.linalg.norm(re_axis)).astype(int))
        cv2.line(thresh, rect_center, re_draw_ortho, (255, 0, 0), line_thickness)

        # Return result
        return [le_angle, re_angle], thresh

    def longest_distance(self, rect):
        """Default function for extracting fish eyes' angular position.

        :param rect: 2d image (usually the rectangular ROI around the eyes)
                     which contains both of the fish's eyes. Upward image direction -> forward fish direction
        :return: modified 2d image
        """


        # Apply threshold
        _, thresh = cv2.threshold(rect, self.thresh, self.maxvalue, cv2.THRESH_BINARY_INV)

        # Make RGB
        thresh = np.stack((thresh, thresh, thresh), axis=-1)

        ################
        # Extract right eye angular position
        reThresh = thresh[:,int(rect.shape[1]/2):,0]
        reCnts, _ = cv2.findContours(reThresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

        if len(reCnts) == 0:
            return None, rect

        reCnt = None
        if len(reCnts) > 1:
            for cnt in reCnts:
                if cnt.shape[0] < 5:
                    continue
                if reCnt is None or cv2.contourArea(cnt) > cv2.contourArea(reCnt):
                    reCnt = cnt.squeeze()

        if reCnt is None:
            return None, rect

        reCntSort = reCnt[reCnt[:, 1].argsort()]
        upperPoints = reCntSort[-reCntSort.shape[0] // 3:, :]
        lowerPoints = reCntSort[:reCntSort.shape[0] // 3, :]

        ### Draw contour points
        for i in range(upperPoints.shape[0]):
            p = upperPoints[i,:].copy()
            p[0] += rect.shape[1]//2
            cv2.drawMarker(thresh, tuple(p), (0, 255, 0), cv2.MARKER_DIAMOND, 3)

        for i in range(lowerPoints.shape[0]):
            p = lowerPoints[i,:].copy()
            p[0] += rect.shape[1]//2
            cv2.drawMarker(thresh, tuple(p), (0, 0, 255), cv2.MARKER_DIAMOND, 3)

        if upperPoints.shape[0] < 2 or lowerPoints.shape[0] < 2:
            return None, rect

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
        cv2.line(thresh, tuple(p1), tuple(p2), (255, 128, 0), 1)
        cv2.drawMarker(thresh, tuple(p1), (255, 0, 0), cv2.MARKER_CROSS, 4)
        cv2.drawMarker(thresh, tuple(p2), (255, 0, 0), cv2.MARKER_CROSS, 4)

        ## Display perpendicular axis
        cv2.line(thresh, tuple(p2), tuple((p2 + 0.75 * reAngle * np.linalg.norm(axis) * perpAxis).astype(int)), (255, 128, 0), 1)


        ################
        # Extract left eye angular position
        leThresh = thresh[:,:int(rect.shape[1]/2),0]
        leCnts, _ = cv2.findContours(leThresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

        if len(leCnts) == 0:
            return None, rect

        leCnt = None
        if len(leCnts) > 1:
            for cnt in leCnts:
                if cnt.shape[0] < 5:
                    continue
                if leCnt is None or cv2.contourArea(cnt) > cv2.contourArea(leCnt):
                    leCnt = cnt.squeeze()

        if leCnt is None:
            return None, rect

        leCntSort = leCnt[leCnt[:, 1].argsort()]
        upperPoints = leCntSort[-leCntSort.shape[0] // 3:, :]
        lowerPoints = leCntSort[:leCntSort.shape[0] // 3, :]

        ### Draw detected contour points
        ## Upper part
        for i in range(upperPoints.shape[0]):
            cv2.drawMarker(thresh, tuple(upperPoints[i,:]), (0, 255, 0), cv2.MARKER_DIAMOND, 3)
        ## Lower part
        for i in range(lowerPoints.shape[0]):
            cv2.drawMarker(thresh, tuple(lowerPoints[i,:]), (0, 0, 255), cv2.MARKER_DIAMOND, 3)

        ## Return if thete are to few contour points
        if upperPoints.shape[0] < 2 or lowerPoints.shape[0] < 2:
            return None, rect

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
        cv2.drawMarker(thresh, tuple(p1), (255, 0, 0), cv2.MARKER_CROSS, 4)
        cv2.drawMarker(thresh, tuple(p2), (255, 0, 0), cv2.MARKER_CROSS, 4)
        ## Display perpendicular axis
        cv2.line(thresh, tuple(p2), tuple((p2 + 0.75 * leAngle * np.linalg.norm(axis) * perpAxis).astype(int)), (255, 255, 0), 1)

        return [leAngle, reAngle], thresh

    def coord_transform_pg2cv(self, point, asType : type = np.float32):
        return [asType(point[0]), asType(self.res_y - point[1])]

    def _compute(self, **frames):

        # Read frame
        frame = frames.get(self.camera_device_id)

        # Check if frame was returned
        if frame is None:
            return

        # Write frame to buffer
        self.buffer.frame.write(frame[:,:])

        # Do eye detection and angular position estimation
        if bool(self.rois):

            # If eyes were marked: iterate over ROIs and extract eye positions
            for id, rect_params in self.rois.items():

                # Convert from pyqtgraph image coordinates to openCV
                rect_params = (tuple(self.coord_transform_pg2cv(rect_params[0])), tuple(rect_params[1]), -rect_params[2],)

                # For debugging: draw rectangle
                #box = cv2.boxPoints(rect)
                #box = np.int0(box)
                #cv2.drawContours(newframe, [box], 0, (255, 0, 0), 1)

                # Get rect and frame parameters
                center, size, angle = rect_params[0], rect_params[1], rect_params[2]
                center, size = tuple(map(int, center)), tuple(map(int, size))
                height, width = frame.shape[0], frame.shape[1]


                # Rotate
                M = cv2.getRotationMatrix2D(center, angle, 1)
                rotFrame = cv2.warpAffine(frame, M, (width, height))

                # Crop rect from frame
                cropRect = cv2.getRectSubPix(rotFrame, size, center)

                # Rotate rect so that "up" direction in image corresponds to "foward" for the fish
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
                #self.segmentationMode = 'feretDiameter'
                eye_pos, new_rect = getattr(self, self.detection_mode)(rotRect)

                # Debug: write to file
                #cv2.imwrite('meh/test{}.jpg'.format(id), rotRect)

                ### Append angular eye positions to shared list
                if eye_pos is not None:
                    le_pos = eye_pos[0]
                    re_pos = eye_pos[1]

                    le_pos_attr = getattr(self.buffer, f'{self.ang_le_pos_prefix}{id}')
                    re_pos_attr = getattr(self.buffer, f'{self.ang_re_pos_prefix}{id}')

                    # Write
                    le_pos_attr.write(le_pos)
                    re_pos_attr.write(re_pos)

                    # Read last positions
                    _, _, last_le_pos = le_pos_attr.read(1)
                    last_le_pos = last_le_pos[0]
                    _, last_time, last_re_pos = re_pos_attr.read(1)
                    last_re_pos = last_re_pos[0]
                    last_time = last_time[0]

                    # Get current reference time
                    current_time = self.buffer.get_time()

                    # Calculate velocities
                    le_sacc = False
                    re_sacc = False
                    #if last_le_pos is not None and last_re_pos is not None:
                    if last_le_pos != 0 and last_re_pos != 0:
                        le_vel = (le_pos-last_le_pos)/(current_time-last_time)
                        re_vel = (re_pos-last_re_pos)/(current_time-last_time)

                        #print(le_vel, re_vel)

                        le_sacc = abs(le_vel) > self.saccade_threshold
                        re_sacc = abs(re_vel) > self.saccade_threshold

                    # if le_sacc:
                    #     print('LE SACCADE!')
                    # if re_sacc:
                    #     print('RE SACCADE!')
                    if le_sacc or re_sacc:
                        #TODO:  Trigger here for _now_, this is stupid
                        IPC.rpc(Def.Process.Io,
                                routines.io.IoRoutines.TriggerLedArenaFlash.trigger_flash,
                                0.01, 2.0)
                    if le_sacc or re_sacc:
                        print(le_sacc, re_sacc)
                    getattr(self.buffer, f'{self.le_sacc_prefix}{id}').write(int(le_sacc))
                    getattr(self.buffer, f'{self.re_sacc_prefix}{id}').write(int(re_sacc))

                # Set current rect ROI data
                getattr(self.buffer, f'{self.extracted_rect_prefix}{id}').write(new_rect)

    def _out(self):
        for id in range(self.roi_maxnum):
            le_attr_name = f'{self.ang_le_pos_prefix}{id}'
            re_attr_name = f'{self.ang_re_pos_prefix}{id}'

            _, le_time, le_ang_pos = getattr(self.buffer, le_attr_name).read(0)
            _, re_time, re_ang_pos = getattr(self.buffer, re_attr_name).read(0)

            if le_ang_pos[0] is None or re_ang_pos[0] is None:
                continue

            yield le_attr_name, le_time[0], le_ang_pos[0]
            yield re_attr_name, re_time[0], re_ang_pos[0]

