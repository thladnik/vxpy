from MappApp_Stimulus import Stimulus
# TODO: Fix shader compatibility, write stimulus, test if stimulus class allows multiple program
class icoCMN(Stimulus):

    _sphere_model = 'dividable_icosphere>diviable_icosphere_sd1'
    _base_vertex_shader = "_v_mono_base.shader"
    _base_fragment_shader = "_f_empty.shader"
    _vertex_shader = "v_mono"
    _fragment_shader = 'f_grating.shader'

    def __init__(self, protocol, orientation, shape, velocity, num):
        """

        :param protocol: protocol of which stimulus is currently part of

        :param orientation: orientation of grating; either 'vertical' or 'horizontal'
        :param shape: shape of underlying function; either 'rectangular' or 'sinusoidal'
        :param velocity:
        :param num:
        """
        super().__init__(protocol)

        self.setShape(shape)
        self.setOrientation(orientation)
        self.protocol.program['u_velocity'] = velocity
        self.protocol.program['u_stripes_num'] = num

    def readCurrentParameters(self):
        return dict(orientation = self.protocol.program['u_orientation'],
                    shape = self.protocol.program['u_shape'],
                    velocity = self.protocol.program['u_velocity'],
                    num = self.protocol.program['u_stripes_num']
                    )

    def update(self, shape=None, orientation=None, velocity=None, num=None):

        if shape is not None:
            self.setShape(shape)

        if orientation is not None:
            self.setOrientation(orientation)

        if velocity is not None:
            self.protocol.program['u_velocity'] = velocity

        if num is not None and num > 0:
            self.protocol.program['u_stripes_num'] = num

    def setShape(self, shape):
        if shape == 'rectangular':
            self.protocol.program['u_shape'] = 1
        elif shape == 'sinusoidal':
            self.protocol.program['u_shape'] = 2

    def setOrientation(self, orientation):
        if orientation == 'vertical':
            self.protocol.program['u_orientation'] = 1
        elif orientation == 'horizontal':
            self.protocol.program['u_orientation'] = 2