"""
MappApp ./routines/camera/core.py
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

from mappapp import Config
from mappapp import Def
from mappapp.core.routine import ArrayAttribute, ArrayDType, CameraRoutine, ObjectAttribute

# Type hinting
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass


class Frames(CameraRoutine):

    def __init__(self, *args, **kwargs):
        CameraRoutine.__init__(self, *args, **kwargs)

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


from mappapp import api
class EyePositionDetection(CameraRoutine):

    camera_device_id = 'fish_embedded'

    extracted_rect_prefix = 'extracted_rect_'
    ang_le_pos_prefix = 'angular_le_pos_'
    ang_re_pos_prefix = 'angular_re_pos_'
    ang_le_vel_prefix = 'angular_le_vel_'
    ang_re_vel_prefix = 'angular_re_vel_'
    le_sacc_prefix = 'le_saccade_'
    re_sacc_prefix = 're_saccade_'
    roi_maxnum = 10


    def __init__(self, *args, **kwargs):
        CameraRoutine.__init__(self, *args, **kwargs)

        self.add_trigger('saccade_trigger')

        # Set accessible methods
        self.exposed.append(EyePositionDetection.set_threshold)
        self.exposed.append(EyePositionDetection.set_threshold_range)
        self.exposed.append(EyePositionDetection.set_threshold_iterations)
        self.exposed.append(EyePositionDetection.set_max_im_value)
        self.exposed.append(EyePositionDetection.set_min_particle_size)
        self.exposed.append(EyePositionDetection.set_roi)
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

        # Set frame buffer
        self.buffer.frame = ArrayAttribute((self.res_y, self.res_x),
                                           ArrayDType.uint8,
                                           length=2*target_fps)
        # Set saccade trigger buffer
        self.buffer.saccade_trigger = ArrayAttribute((1, ), ArrayDType.binary, length=5*target_fps)

    def initialize(self):
        api.set_digital_output('saccade_trigger_out', EyePositionDetection, 'saccade_trigger')

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
            self.register_with_ui_plotter(EyePositionDetection, f'{self.ang_le_pos_prefix}{id}',
                                          start_idx, name=f'eye_pos(LE {id})', axis='eye_pos')
            self.register_with_ui_plotter(EyePositionDetection, f'{self.ang_re_pos_prefix}{id}',
                                          start_idx, name=f'eye_pos(RE {id})', axis='eye_pos')

            # Velocity
            self.register_with_ui_plotter(EyePositionDetection, f'{self.ang_le_vel_prefix}{id}',
                                          start_idx, name=f'eye_vel(LE {id})', axis='eye_vel')
            self.register_with_ui_plotter(EyePositionDetection, f'{self.ang_re_vel_prefix}{id}',
                                          start_idx, name=f'eye_vel(RE {id})', axis='eye_vel')

            # Saccade trigger
            self.register_with_ui_plotter(EyePositionDetection, f'{self.le_sacc_prefix}{id}',
                                          start_idx, name=f'sacc(LE {id})', axis='sacc')
            self.register_with_ui_plotter(EyePositionDetection, f'{self.re_sacc_prefix}{id}',
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

    def coord_transform_pg2cv(self, point, asType : type = np.float32):
        return [asType(point[0]), asType(self.res_y - point[1])]

    def execute(self, **frames):

        # Read frame
        frame = frames.get(self.camera_device_id)
        frame = frame[:,:,0]

        # Check if frame was returned
        if frame is None:
            return

        # Write frame to buffer
        self.buffer.frame.write(frame)

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
                (le_pos, re_pos), new_rect = self.from_ellipse(rot_rect)

                # Get corresponding position attributes
                le_pos_attr = getattr(self.buffer, f'{self.ang_le_pos_prefix}{id}')
                re_pos_attr = getattr(self.buffer, f'{self.ang_re_pos_prefix}{id}')

                # Write to buffer
                le_pos_attr.write(le_pos)
                re_pos_attr.write(re_pos)

                ####
                # Calculate eye angular VELOCITIES

                _, _, last_le_pos = le_pos_attr.read(1)
                last_le_pos = last_le_pos[0]
                _, last_time, last_re_pos = re_pos_attr.read(1)
                last_re_pos = last_re_pos[0]
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

                is_saccade = bool(le_sacc) or bool(re_sacc)
                if is_saccade:
                    self._triggers['saccade_trigger'].emit()
                self.buffer.saccade_trigger.write(is_saccade)

                getattr(self.buffer, f'{self.le_sacc_prefix}{id}').write(le_sacc)
                getattr(self.buffer, f'{self.re_sacc_prefix}{id}').write(re_sacc)

                # Set current rect ROI data
                getattr(self.buffer, f'{self.extracted_rect_prefix}{id}').write(new_rect)


from mappapp import utils
class FishPosDirDetection(CameraRoutine):

    buffer_size = 500

    camera_device_id = 'fish_freeswim'

    def __init__(self, *args, **kwargs):
        CameraRoutine.__init__(self, *args, **kwargs)

        self.add_trigger('saccade_trigger')

        self.exposed.append(FishPosDirDetection.set_threshold)
        self.exposed.append(FishPosDirDetection.set_min_particle_size)
        self.exposed.append(FishPosDirDetection.set_bg_calc_range)
        self.exposed.append(FishPosDirDetection.calculate_background)

        # Set required devices
        self.required.append(self.camera_device_id)

        # Get camera specs
        assert self.camera_device_id in Config.Camera[Def.CameraCfg.device_id], \
            f'Camera device "{self.camera_device_id}" not configured for {self.__class__.__name__}'
        idx = Config.Camera[Def.CameraCfg.device_id].index(self.camera_device_id)
        self.res_x = Config.Camera[Def.CameraCfg.res_x][idx]
        self.res_y = Config.Camera[Def.CameraCfg.res_y][idx]
        target_fps = Config.Camera[Def.CameraCfg.fps]

        # Add attributes
        self.buffer.frame = ArrayAttribute((self.res_y, self.res_x, 3), ArrayDType.uint8, length=self.buffer_size)
        self.buffer.tframe = ArrayAttribute((self.res_y, self.res_x, 3), ArrayDType.uint8, length=self.buffer_size)
        self.buffer.fish_position = ArrayAttribute((2, ), ArrayDType.float32, length=self.buffer_size)

        self.background = None
        self.thresh = None
        self.min_size = None
        self.bg_calc_range = None

    def initialize(self):
        api.set_display_uniform_attribute('u_fish_position', FishPosDirDetection, 'fish_position')

    def calculate_background(self):

        _, _, frames = self.buffer.frame.read(last=self.bg_calc_range)

        self.background = utils.calculate_background_mog2(frames)

    def set_bg_calc_range(self, value):
        self.bg_calc_range = value

    def set_threshold(self, value):
        self.thresh = value

    def set_min_particle_size(self, value):
        self.min_size = value

    def execute(self, **frames):

        # Read frame
        frame = frames.get(self.camera_device_id)
        self.buffer.frame.write(frame)

        # Check if frame was returned
        if frame is None:
            return

        if self.background is None:
            return


        im = cv2.absdiff(self.background[:,:,0], frame[:,:,0])

        #self.buffer.tframe.write(im)


        # Apply threshold
        _, thresh = cv2.threshold(im, self.thresh, 255, cv2.THRESH_BINARY)

        # Detect contours
        cnts, hierarchy = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

        hulls = []
        i = 0
        while i < len(cnts):

            cnt = cnts[i]
            M = cv2.moments(cnt)
            A = M['m00']

            self.min_size = 1
            # Discard if contour has no area
            if A < self.min_size:
                del cnts[i]
                continue

            # Particle center
            center = (M['m10'] / A, M['m01'] / A)

            # Hull of particle
            hull = cv2.convexHull(cnt).squeeze()
            hulls.append(hull)

            # Ellipse axes lengths
            a = M['m20'] / M['m00'] - center[0] ** 2
            b = 2 * (M['m11'] / M['m00'] - center[0] * center[1])
            c = M['m02'] / M['m00'] - center[1] ** 2

            # Avoid divisions by zero
            if (a - c) == 0.:
                del cnts[i]
                continue

            # Ellipse's major axis angle
            theta = (1 / 2 * np.arctan(b / (a - c)) + (a < c) - 1) / np.pi * 180  # * np.pi / 2
            W = np.sqrt(8 * (a + c - np.sqrt(b ** 2 + (a - c) ** 2))) / 2
            L = np.sqrt(8 * (a + c + np.sqrt(b ** 2 + (a - c) ** 2))) / 2

            i += 1

        # Draw hull contours for debugging (before possible premature return)
        thresh = np.repeat(thresh[:,:,np.newaxis], 3, axis=-1)
        try:
            cv2.drawContours(thresh, hulls, -1, (255, 0, 0), 1)
        except:
            pass

        self.buffer.tframe.write(thresh)
