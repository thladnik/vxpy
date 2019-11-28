from glumpy import gloo, transforms
import importlib

import MappApp_Definition as madef

class StimulationProtocol:

    def __init__(self):
        self._stimuli = list()
        self._stimulus_index = -1
        self._time = 0.0
        self._advanceTime = 0.0

        self.program = None
        self.model = None
        self._current = None

    def addStimulus(self, stimulus, args, kwargs, duration=None):
        self._stimuli.append((stimulus, args, kwargs, duration))

    def _advance(self):
        self._stimulus_index += 1

        if self._stimulus_index >= len(self._stimuli):
            print('End of stimulation protocol')
            return

        new_stimulus, args, kwargs, duration = self._stimuli[self._stimulus_index]

        # Set new program (if shaders differ from previous program)
        if self.program is None or self._current.__class__getShaderHash() != new_stimulus.getShaderHash():
            # Create program
            self.program = gloo.Program(vertex=new_stimulus.getVertexShader(), fragment=new_stimulus.getFragmentShader())
            # Set viewport
            self.program['viewport'] = transforms.Viewport()

        # Set new sphere model
        if self.model is None or self._current.__class__._sphere_model != new_stimulus._sphere_model:
            new_model = new_stimulus._sphere_model.split('>')
            self.model = getattr(importlib.import_module('%s.%s' % (madef.Paths.Model, new_model[0])), new_model[1])()

            ## Bind vertex buffer of model to program
            self.program.bind(self.model.vertexBuffer)

        # Set new current stimulus
        self._current = new_stimulus(*args, **kwargs, duration)

    def draw(self, dt):
        self._time += dt

        if self._shouldAdvance():
            self._advance()

        self._current.draw(dt)

    def _shouldAdvance(self):
        if (self._advanceTime is None) or (self._time < self._advanceTime):
            return False
        return True
