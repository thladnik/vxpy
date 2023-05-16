"""vxPy core display capture routine"""

import numpy as np

from vxpy import calib
import vxpy.api.attribute as vxattribute
import vxpy.api.routine as vxroutine
import vxpy.core.visual as vxvisual


class Frames(vxroutine.DisplayRoutine):

    def require(self, *args, **kwargs):

        # Set up shared variables
        self.width = calib.CALIB_DISP_WIN_SIZE_WIDTH
        self.height = calib.CALIB_DISP_WIN_SIZE_HEIGHT
        self.frame = vxattribute.ArrayAttribute('display_frame',
                                                (self.width, self.height, 3),
                                                vxattribute.ArrayType.uint8)

    def initialize(self):
        self.frame.add_to_file()

    def main(self, visual: vxvisual.AbstractVisual):
        if visual is None:
            return

        frame = np.swapaxes(visual.transform.frame.read('color', alpha=False), 0, 1)

        self.frame.write(frame)
