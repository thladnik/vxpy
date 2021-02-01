"""
MappApp ./routines/Core.py - Custom processing routine implementations for the camera process.
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
from scipy.spatial import distance

import Config
import Def
import gui.Integrated
import IPC
from core.routine import AbstractRoutine, ArrayAttribute, ArrayDType, ObjectAttribute


class Frames(AbstractRoutine):

    def __init__(self, *args, **kwargs):
        AbstractRoutine.__init__(self, *args, **kwargs)

        self.device_list = list(zip(Config.Camera[Def.CameraCfg.device_id],
                                    Config.Camera[Def.CameraCfg.res_x],
                                    Config.Camera[Def.CameraCfg.res_y]))

        target_fps = Config.Camera[Def.CameraCfg.fps]

        # Set up buffer frame attribute for each camera device
        for device_id, res_x, res_y in self.device_list:
            # Set one array attribute per camera device
            array_attr = ArrayAttribute((res_y, res_x), ArrayDType.uint8, length=2*target_fps)
            attr_name = f'{device_id}_frame'
            setattr(self.buffer, attr_name, array_attr)
            # Add to be written to file
            self.file_attrs.append(attr_name)

    def execute(self, **frames):
        for device_id, frame in frames.items():

            if frame is None:
                continue

            # Update shared attributes
            if frame.ndim > 2:
                getattr(self.buffer, f'{device_id}_frame').write(frame[:, :, 0])
            else:
                getattr(self.buffer, f'{device_id}_frame').write(frame[:, :])


class EyePositionDetection(AbstractRoutine):

    camera_device_id = 'behavior'
    extracted_rect_prefix = 'extracted_rect_'
    ang_le_pos_prefix = 'angular_le_pos_'
    ang_re_pos_prefix = 'angular_re_pos_'
    ang_le_vel_prefix = 'angular_le_vel_'
    ang_re_vel_prefix = 'angular_re_vel_'
    le_sacc_prefix = 'le_saccade_'
    re_sacc_prefix = 're_saccade_'
    roi_maxnum = 10

    def __init__(self, *args, **kwargs):
        AbstractRoutine.__init__(self, *args, **kwargs)

        # Set accessible methods
        self.exposed.append(EyePositionDetection.set_threshold)
        self.exposed.append(EyePositionDetection.set_threshold_range)
        self.exposed.append(EyePositionDetection.set_threshold_iterations)
        self.exposed.append(EyePositionDetection.set_max_im_value)
        self.exposed.append(EyePositionDetection.set_min_particle_size)
        self.exposed.append(EyePositionDetection.set_roi)
        self.exposed.append(EyePositionDetection.set_detection_mode)
        self.exposed.append(EyePositionDetection.set_saccade_threshold)

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
        self.detection_mode = None
        self.saccade_threshold = None

        # Set up buffer attributes
        for id in range(self.roi_maxnum):
            # Rectangle
            setattr(self.buffer, f'{self.extracted_rect_prefix}{id}',
                    ObjectAttribute(length=2*target_fps))

            # Position
            setattr(self.buffer, f'{self.ang_le_pos_prefix}{id}',
                    ArrayAttribute(shape=(1,), dtype=ArrayDType.float64, length=5 * target_fps))
            setattr(self.buffer, f'{self.ang_re_pos_prefix}{id}',
                    ArrayAttribute(shape=(1,), dtype=ArrayDType.float64, length=5 * target_fps))

            # Velocity
            setattr(self.buffer, f'{self.ang_le_vel_prefix}{id}',
                    ArrayAttribute(shape=(1,), dtype=ArrayDType.float64, length=5 * target_fps))
            setattr(self.buffer, f'{self.ang_re_vel_prefix}{id}',
                    ArrayAttribute(shape=(1,), dtype=ArrayDType.float64, length=5 * target_fps))

            # Saccade detection
            setattr(self.buffer, f'{self.le_sacc_prefix}{id}',
                    ArrayAttribute(shape=(1,), dtype=ArrayDType.float64, length=5 * target_fps))
            setattr(self.buffer, f'{self.re_sacc_prefix}{id}',
                    ArrayAttribute(shape=(1,), dtype=ArrayDType.float64, length=5 * target_fps))
        self.buffer.frame = ArrayAttribute((self.res_y, self.res_x),
                                           ArrayDType.uint8,
                                           length=2*target_fps)

    def set_detection_mode(self, mode):
        self.detection_mode = mode

    def set_threshold(self, thresh):
        self.thresh = thresh

    def set_threshold_range(self, range):
        self.thresh_range = range

    def set_threshold_iterations(self, n):
        self.thresh_iter = n

    def set_max_im_value(self, value):
        self.maxvalue = value

    def set_min_particle_size(self, size):
        self.min_size = size

    def set_roi(self, id, params):
        if id not in self.rois:
            start_idx = self.buffer.get_index() + 1
            # Send buffer attributes to plotter
            # Position
            self.register_with_ui_plotter(f'{EyePositionDetection.__name__}/{self.ang_le_pos_prefix}{id}',
                                          start_idx, name=f'eye_pos(LE {id})', axis='eye_pos')
            self.register_with_ui_plotter(f'{EyePositionDetection.__name__}/{self.ang_re_pos_prefix}{id}',
                                          start_idx, name=f'eye_pos(RE {id})', axis='eye_pos')

            # Velocity
            self.register_with_ui_plotter(f'{EyePositionDetection.__name__}/{self.ang_le_vel_prefix}{id}',
                                          start_idx, name=f'eye_vel(LE {id})', axis='eye_vel')
            self.register_with_ui_plotter(f'{EyePositionDetection.__name__}/{self.ang_re_vel_prefix}{id}',
                                          start_idx, name=f'eye_vel(RE {id})', axis='eye_vel')

            # Saccade trigger
            self.register_with_ui_plotter(f'{EyePositionDetection.__name__}/{self.le_sacc_prefix}{id}',
                                          start_idx, name=f'sacc(LE {id})', axis='sacc')
            self.register_with_ui_plotter(f'{EyePositionDetection.__name__}/{self.re_sacc_prefix}{id}',
                                          start_idx, name=f'sacc(RE {id})', axis='sacc')

            # Add attributes to save-to-file list:
            self.file_attrs.append(f'{self.ang_le_pos_prefix}{id}')
            self.file_attrs.append(f'{self.ang_re_pos_prefix}{id}')
            self.file_attrs.append(f'{self.ang_le_vel_prefix}{id}')
            self.file_attrs.append(f'{self.ang_re_vel_prefix}{id}')
            self.file_attrs.append(f'{self.le_sacc_prefix}{id}')
            self.file_attrs.append(f'{self.re_sacc_prefix}{id}')


        self.rois[id] = params

    def set_saccade_threshold(self, thresh):
        self.saccade_threshold = thresh

    @staticmethod
    def tuple_o_ints(t):
        return tuple((int(i) for i in t))

    def from_ellipse(self, rect):
        # Formatting for drawing
        line_thickness = np.ceil(np.mean(rect.shape) / 50).astype(int)
        line_thickness = 1 if line_thickness == 0 else line_thickness
        marker_size = line_thickness * 5

        # Set rect center
        rect_center = (rect.shape[1] // 2, rect.shape[0] // 2)

        # Apply threshold
        _, thresh = cv2.threshold(rect[:,:], self.thresh, 255, cv2.THRESH_BINARY_INV)

        # Detect contours
        cnts, hierarchy = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

        # Make RGB
        thresh = np.stack((thresh, thresh, thresh), axis=-1)
        #
        # Collect contour parameters and filter contours
        areas = list()
        barycenters = list()
        hulls = list()
        feret_points = list()
        thetas = list()
        axes = list()
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

            # Particle center
            center = (M['m10']/A, M['m01']/A)

            # Hull of particle
            hull = cv2.convexHull(cnt).squeeze()

            # Ellipse axes lengths
            a = M['m20'] / M['m00'] - center[0] ** 2
            b = 2 * (M['m11'] / M['m00'] - center[0] * center[1])
            c = M['m02'] / M['m00'] - center[1] ** 2

            # Avoid divisions by zero
            if (a - c) == 0.:
                del cnts[i]
                continue

            # Ellipse's major axis angle
            theta = (1 / 2 * np.arctan(b / (a - c)) + (a < c) - 1) / np.pi * 180 #* np.pi / 2
            W = np.sqrt(8 * (a + c - np.sqrt(b ** 2 + (a - c) ** 2))) / 2
            L = np.sqrt(8 * (a + c + np.sqrt(b ** 2 + (a - c) ** 2))) / 2

            thetas.append(theta)
            barycenters.append(center)
            axes.append((W, L))
            areas.append(A)
            hulls.append(hull)
            dists.append(distance.euclidean(center, rect_center))
            feret_points.append((hull[np.argmin(hull[:,1])], hull[np.argmax(hull[:,1])]))

            i += 1

        # Additional filtering of particles to idenfity both eyes if more than 2
        if len(cnts) > 2:
            dists, areas, barycenters, hulls, feret_points, thetas, axes = \
                list(zip(*sorted(list(zip(dists, areas, barycenters, hulls, feret_points, thetas, axes)))[:2]))

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
            return [np.nan, np.nan], thresh

        # At this point there should only be 2 particles left
        le_idx = 0 if (barycenters[0][0] < rect_center[0]) else 1
        re_idx = 1 if (barycenters[0][0] < rect_center[0]) else 0

        try:
            for center, axis, theta in zip(barycenters, axes, thetas):
                center = self.tuple_o_ints(center)
                axis = self.tuple_o_ints(axis)
                angle = float(theta)
                start_angle = 0.
                end_angle = 360.
                color = (255, 0, 0)

                cv2.ellipse(thresh,
                            center,
                            axis,
                            angle, start_angle, end_angle, color, line_thickness)
        except Exception as exc:
            import traceback
            traceback.print_exc()

        return [thetas[le_idx], thetas[re_idx]], thresh


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
        _, thresh = cv2.threshold(rect[:,:], self.thresh, 255, cv2.THRESH_BINARY_INV)

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
            return [np.nan, np.nan], thresh

        # At this point there should only be 2 particles left
        le_idx = 0 if (centroids[0][0] < rect_center[0]) else 1
        re_idx = 1 if (centroids[0][0] < rect_center[0]) else 0

        # LE
        le_axis = feret_points[le_idx][0] - feret_points[le_idx][1]
        le_axis_norm = le_axis / np.linalg.norm(le_axis)
        le_ortho = np.array([le_axis_norm[1], -le_axis_norm[0]])
        # RE
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

    def coord_transform_pg2cv(self, point, asType : type = np.float32):
        return [asType(point[0]), asType(self.res_y - point[1])]

    def execute(self, **frames):

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

                ####
                # Extract rectanglular ROI

                # Convert from pyqtgraph image coordinates to openCV
                rect_params = (tuple(self.coord_transform_pg2cv(rect_params[0])), tuple(rect_params[1]), -rect_params[2],)

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
                rot_rect = cv2.warpAffine(cropRect, M, (wBound, hBound))

                ####
                # Calculate eye angular POSITIONS

                # Apply detection function on cropped rect which contains eyes
                (le_pos, re_pos), new_rect = getattr(self, self.detection_mode)(rot_rect)

                # Get corresponding position attributes
                le_pos_attr = getattr(self.buffer, f'{self.ang_le_pos_prefix}{id}')
                re_pos_attr = getattr(self.buffer, f'{self.ang_re_pos_prefix}{id}')

                # Write to buffer
                le_pos_attr.write(le_pos)
                re_pos_attr.write(re_pos)

                ####
                # Calculate eye angular VELOCITIES

                # Read last positions
                _, _, last_le_pos = le_pos_attr.read(3)
                last_le_pos = np.median(last_le_pos)
                _, last_time, last_re_pos = re_pos_attr.read(3)
                last_re_pos = np.median(last_re_pos)
                last_time = last_time[-1]
                if last_time is None:
                    last_time = -np.inf

                # Calculate time elapsed since last frame
                current_time = self.buffer.get_time()
                dt = (current_time - last_time)

                # Calculate velocities
                le_vel = np.abs((le_pos - last_le_pos) / dt)
                re_vel = np.abs((re_pos - last_re_pos) / dt)

                # Get velocity attributes
                le_vel_attr = getattr(self.buffer, f'{self.ang_le_vel_prefix}{id}')
                re_vel_attr = getattr(self.buffer, f'{self.ang_re_vel_prefix}{id}')

                # Write velocity to buffer
                le_vel_attr.write(le_vel)
                re_vel_attr.write(re_vel)

                ####
                # Calculate saccade trigger

                _, _, last_le_vel = le_vel_attr.read(1)
                last_le_vel = last_le_vel[0]
                _, _, last_re_vel = re_vel_attr.read(1)
                last_re_vel = last_re_vel[0]

                le_sacc = int(last_le_vel < self.saccade_threshold and le_vel > self.saccade_threshold)
                re_sacc = int(last_re_vel < self.saccade_threshold and re_vel > self.saccade_threshold)

                getattr(self.buffer, f'{self.le_sacc_prefix}{id}').write(le_sacc)
                getattr(self.buffer, f'{self.re_sacc_prefix}{id}').write(re_sacc)

                # Set current rect ROI data
                getattr(self.buffer, f'{self.extracted_rect_prefix}{id}').write(new_rect)
