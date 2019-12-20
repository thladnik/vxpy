from Stimulus import Stimulus

class Checkerboard(Stimulus):

    _sphere_model = 'UVSphere>UVSphere_80thetas_40phis'
    _fragment_shader = 'f_checkerboard.shader'

    def __init__(self, protocol, rows, cols):
        super().__init__(protocol)

        self.protocol.program['u_checker_rows'] = rows
        self.protocol.program['u_checker_cols'] = cols

    def update(self, cols=None, rows=None):

        if cols is not None and cols > 0:
            self.protocol.program['u_checker_cols'] = cols

        if rows is not None and rows > 0:
            self.protocol.program['u_checker_rows'] = rows
