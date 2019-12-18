import os

from MappApp_Definition import Path

class Shader:

    _glumpy_placeholders = {
        '//<viewport.transform>;': '<viewport.transform>;',
        '//<viewport.clipping>;': '<viewport.clipping>;'
    }

    def __init__(self, base, main):
        self._compile(base, main)

    def _compile(self, base, main):
        self.shader = ''

        # Load base shader
        with open(os.path.join(Path.Shader, base), 'r') as fobj:
            self.shader += fobj.read()
            fobj.close()
        self.shader += '\n'

        # Load shader containing void main()
        with open(os.path.join(Path.Shader, main), 'r') as fobj:
            self.shader += fobj.read()
            fobj.close()

            # Substitute Glumpy-specific placeholders
        for key, str in self._glumpy_placeholders.items():
            self.shader = self.shader.replace(key, str)

    def getString(self):
            return self.shader