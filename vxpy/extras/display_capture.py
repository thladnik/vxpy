"""vxPy core display capture routine"""

import numpy as np

import vxpy.config
from vxpy import calib
import vxpy.api.attribute as vxattribute
import vxpy.api.routine as vxroutine
import vxpy.core.visual as vxvisual


class Frames(vxroutine.DisplayRoutine):

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)

        self.downsample_by = kwargs.get('downsample_by', 1)

        self.frame = None
        self.height = None
        self.width = None

    def require(self, *args, **kwargs):
        # Set up shared variables
        self.width = vxpy.config.DISPLAY_WIN_SIZE_WIDTH_PX // self.downsample_by
        self.height = vxpy.config.DISPLAY_WIN_SIZE_HEIGHT_PX // self.downsample_by
        self.frame = vxattribute.ArrayAttribute('display_frame',
                                                (self.width, self.height, 3),
                                                vxattribute.ArrayType.uint8)

    def initialize(self):
        pass

    def main(self, visual: vxvisual.AbstractVisual):
        if visual is None:
            return

        frame = np.swapaxes(visual.transform.frame.read('color', alpha=False), 0, 1)

        self.frame.write(frame[::self.downsample_by, ::self.downsample_by, :])
