"""
MappApp ./routines/camera/__init__.py
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
from __future__ import annotations
import cv2
import numpy as np
from scipy.spatial import distance

from vxpy import config
from vxpy.definitions import *
from vxpy import definitions
from vxpy.api import get_time
from vxpy.api.attribute import ArrayAttribute, ArrayType, ObjectAttribute, write_to_file, get_attribute
from vxpy.api.routine import CameraRoutine
from vxpy.api.ui import register_with_plotter
from vxpy.api.io import set_digital_output
from vxpy.api.dependency import require_camera_device
from vxpy.core.camera import find_config_for_camera_id, Format


class EyePositionDetection(CameraRoutine):

    # Set required device
    camera_device_id = 'fish_embedded'

    routine_prefix = 'eyepos_'

    extracted_rect_prefix = f'{routine_prefix}extracted_rect_'
    ang_le_pos_prefix = f'{routine_prefix}angular_le_pos_'
    ang_re_pos_prefix = f'{routine_prefix}angular_re_pos_'
    ang_le_vel_prefix = f'{routine_prefix}angular_le_vel_'
    ang_re_vel_prefix = f'{routine_prefix}angular_re_vel_'
    le_sacc_prefix = f'{routine_prefix}le_saccade_'
    re_sacc_prefix = f'{routine_prefix}re_saccade_'
    roi_maxnum = 10

    def setup(self):
        require_camera_device(self.camera_device_id)

        self.add_trigger('saccade_trigger')

        # Set accessible methods
        self.exposed.append(EyePositionDetection.set_threshold)
        self.exposed.append(EyePositionDetection.set_threshold_range)
        self.exposed.append(EyePositionDetection.set_threshold_iterations)
        self.exposed.append(EyePositionDetection.set_max_im_value)
        self.exposed.append(EyePositionDetection.set_min_particle_size)
        self.exposed.append(EyePositionDetection.set_roi)
        self.exposed.append(EyePositionDetection.set_saccade_threshold)

        # Get camera specs
        config = find_config_for_camera_id(self.camera_device_id)
        fmt = Format.from_str(config['format'])
        self.res_x = fmt.width
        self.res_y = fmt.height

        # Set up parameter variables (accessible externally)
        self.rois = dict()
        self.thresh = None
        self.min_size = None
        self.saccade_threshold = None

        # Set up attributes
        # self.data = []
        for id in range(self.roi_maxnum):
            roi = {}

            # Rectangle
            extracted_roi_name = f'{self.extracted_rect_prefix}{id}'
            roi[extracted_roi_name] = ObjectAttribute(extracted_roi_name)

            # Position
            # LE
            le_pos_name = f'{self.ang_le_pos_prefix}{id}'
            roi[le_pos_name] = ArrayAttribute(le_pos_name, (1,), ArrayType.float64)
            # RE
            re_pos_name = f'{self.ang_re_pos_prefix}{id}'
            roi[re_pos_name] = ArrayAttribute(re_pos_name, (1,), ArrayType.float64)

            # Velocity
            # LE
            le_vel_name = f'{self.ang_le_vel_prefix}{id}'
            roi[le_vel_name] = ArrayAttribute(le_vel_name, (1,), ArrayType.float64)
            # RE
            re_vel_name = f'{self.ang_re_vel_prefix}{id}'
            roi[re_vel_name] = ArrayAttribute(re_vel_name, (1,), ArrayType.float64)

            # Saccade detection
            # LE
            le_sacc_name = f'{self.le_sacc_prefix}{id}'
            roi[le_sacc_name] = ArrayAttribute(le_sacc_name, (1,), ArrayType.float64)
            # RE
            re_sacc_name = f'{self.re_sacc_prefix}{id}'
            roi[re_sacc_name] = ArrayAttribute(re_sacc_name, (1,), ArrayType.float64)
            # self.data.append(roi)

        # Set frame buffer
        self.frame = ArrayAttribute('eyeposdetect_frame', (self.res_y, self.res_x), ArrayType.uint8)

        # Set saccade trigger buffer
        self.saccade_trigger = ArrayAttribute('eyeposdetect_saccade_trigger', (1, ), ArrayType.bool)

    def initialize(self):
        set_digital_output('saccade_trigger_out', 'eyeposdetect_saccade_trigger')

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
            # Send buffer attributes to plotter
            # Position
            register_with_plotter(f'{self.ang_le_pos_prefix}{id}', name=f'eye_pos(LE {id})', axis='eye_pos')
            register_with_plotter(f'{self.ang_re_pos_prefix}{id}', name=f'eye_pos(RE {id})', axis='eye_pos')

            # Velocity
            register_with_plotter(f'{self.ang_le_vel_prefix}{id}', name=f'eye_vel(LE {id})', axis='eye_vel')
            register_with_plotter(f'{self.ang_re_vel_prefix}{id}', name=f'eye_vel(RE {id})', axis='eye_vel')

            # Saccade trigger
            register_with_plotter(f'{self.le_sacc_prefix}{id}', name=f'sacc(LE {id})', axis='sacc')
            register_with_plotter(f'{self.re_sacc_prefix}{id}', name=f'sacc(RE {id})', axis='sacc')

            # Add attributes to save-to-file list:
            write_to_file(self, f'{self.ang_le_pos_prefix}{id}')
            write_to_file(self, f'{self.ang_re_pos_prefix}{id}')
            write_to_file(self, f'{self.ang_le_vel_prefix}{id}')
            write_to_file(self, f'{self.ang_re_vel_prefix}{id}')
            write_to_file(self, f'{self.le_sacc_prefix}{id}')
            write_to_file(self, f'{self.re_sacc_prefix}{id}')

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

    def coord_transform_pg2cv(self, point, asType : type = np.float32):
        return [asType(point[0]), asType(self.res_y - point[1])]

    def main(self, **frames):

        # Read frame
        frame = frames.get(self.camera_device_id)

        # Check if frame was returned
        if frame is None:
            return

        # Reduce to mono
        if frame.ndim > 2:
            frame = frame[:,:,0]

        # Write frame to buffer
        self.frame.write(frame)

        # Do eye detection and angular position estimation
        if not bool(self.rois):
            return

        # If eyes were marked: iterate over ROIs and extract eye positions
        saccade_happened = False
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
            (le_pos, re_pos), new_rect = self.from_ellipse(rot_rect)

            # Get shared attributes
            le_pos_attr = get_attribute(f'{self.ang_le_pos_prefix}{id}')
            re_pos_attr = get_attribute(f'{self.ang_re_pos_prefix}{id}')
            le_vel_attr = get_attribute(f'{self.ang_le_vel_prefix}{id}')
            re_vel_attr = get_attribute(f'{self.ang_re_vel_prefix}{id}')
            le_sacc_attr = get_attribute(f'{self.le_sacc_prefix}{id}')
            re_sacc_attr = get_attribute(f'{self.re_sacc_prefix}{id}')
            rect_roi_attr = get_attribute(f'{self.extracted_rect_prefix}{id}')

            # Calculate eye angular VELOCITIES
            _, _, last_le_pos = le_pos_attr.read()
            last_le_pos = last_le_pos[0]
            _, last_time, last_re_pos = re_pos_attr.read()
            last_re_pos = last_re_pos[0]
            last_time = last_time[-1]
            if last_time is None:
                last_time = -np.inf

            # Calculate time elapsed since last frame
            current_time = get_time()
            dt = (current_time - last_time)

            # Calculate velocities
            le_vel = np.abs((le_pos - last_le_pos) / dt)
            re_vel = np.abs((re_pos - last_re_pos) / dt)

            # Calculate saccade trigger
            _, _, last_le_vel = le_vel_attr.read()
            last_le_vel = last_le_vel[0]
            _, _, last_re_vel = re_vel_attr.read()
            last_re_vel = last_re_vel[0]

            le_sacc = int(last_le_vel < self.saccade_threshold < le_vel)
            re_sacc = int(last_re_vel < self.saccade_threshold < re_vel)

            is_saccade = bool(le_sacc) or bool(re_sacc)
            saccade_happened = saccade_happened or is_saccade
            if is_saccade:
                self.emit_trigger('saccade_trigger')

            # Write to buffer
            le_pos_attr.write(le_pos)
            re_pos_attr.write(re_pos)
            le_vel_attr.write(le_vel)
            re_vel_attr.write(re_vel)

            le_sacc_attr.write(le_sacc)
            re_sacc_attr.write(re_sacc)

            # Set current rect ROI data
            rect_roi_attr.write(new_rect)

        self.saccade_trigger.write(saccade_happened)
