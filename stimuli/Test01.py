from Stimulus import Stimulus

class TestA(Stimulus):

    _sphere_model = 'UVSphere>UVSphere_80thetas_40phis'
    _fragment_shader = 'f_checkerboard.shader'

    def __init__(self, protocol, param_a):
        super().__init__(protocol)

        self.protocol.program['u_param_a'] = param_a


    def update(self, cols=None, rows=None):

        if cols is not None and cols > 0:
            self.protocol.program['u_checker_cols'] = cols

        if rows is not None and rows > 0:
            self.protocol.program['u_checker_rows'] = rows
