from glumpy import gl
from MappApp_Shader import Shader

class Stimulus:
    _base_vertex_shader = '_v_base.shader'
    _vertex_shader = 'v_default.shader'

    _base_fragment_shader = '_f_base.shader'
    _fragment_shader = 'f_default.shader'

    @classmethod
    def getShaderHash(cls):
        return '%s>%s/%s>%s' % \
               (cls._base_vertex_shader, cls._vertex_shader, cls._base_fragment_shader, cls._fragment_shader)

    @classmethod
    def getVertexShader(cls):
        return Shader(cls._base_vertex_shader, cls._vertex_shader).getString()

    @classmethod
    def getFragmentShader(cls):
        return Shader(cls._base_fragment_shader, cls._fragment_shader).getString()

    def __init__(self, protocol):
        self.protocol = protocol

        self.time = 0.0

    def draw(self, dt):
        """
        METHOD CAN BE RE-IMPLEMENTED.

        By default this method uses the indexBuffer object to draw GL_TRIANGLES.

        :param dt: time since last call
        :return:
        """
        self.time += dt
        self.protocol.program['u_time'] = self.time

        # GL commands
        self.protocol.display._glWindow.clear(color=(0.0, 0.0, 0.0, 1.0))
        gl.glEnable(gl.GL_DEPTH_TEST)

        # Draw
        self.protocol.program.draw(gl.GL_TRIANGLES, self.protocol.model.indexBuffer)

    def update(self, *args, **kwargs):
        """
        Method that is called by default to update stimulus parameters.

        Has to be re-implemented in child class if stimulus contains
        uniforms which can be manipulated externally.
        """
        print('WARNING: update method not implemented for stimulus!')
        pass

