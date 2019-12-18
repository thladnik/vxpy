from glumpy import gloo, transforms
import importlib

import MappApp_Definition as madef

class StimulationProtocol:

    def __init__(self, display):
        self.display = display

        self._stimuli = list()
        self._stimulus_index = -1
        self._time = 0.0
        self._advanceTime = 0.0

        self.program = None
        self.model = None
        self._current = None

    def addStimulus(self, stimulus, kwargs, duration=None):
        self._stimuli.append((stimulus, kwargs, duration))

    def _advance(self):
        self._stimulus_index += 1

        if self._stimulus_index >= len(self._stimuli):
            print('End of stimulation protocol')
            return
        print('Starting protocol phase %i' % self._stimulus_index)

        new_stimulus, kwargs, duration = self._stimuli[self._stimulus_index]

        # First: Create new sphere model (if necessary)
        if self.model is None or self._current.__class__._sphere_model != new_stimulus._sphere_model:
            new_model = new_stimulus._sphere_model.split('>')
            self.model = getattr(importlib.import_module('%s.%s' % (madef.Path.Model, new_model[0])), new_model[1])()

        # Second: Create new program (if necessary)
        if self.program is None or self._current.__class__.getShaderHash() != new_stimulus.getShaderHash():

            # Create program
            self.program = gloo.Program(vertex=new_stimulus.getVertexShader(), fragment=new_stimulus.getFragmentShader())

            # Set viewport and attach
            self.program['viewport'] = transforms.Viewport()
            self.display._glWindow.attach(self.program['viewport'])

            # Set uniforms on new program
            self.display._updateUniforms()

            # Bind vertex buffer of model to program
            self.program.bind(self.model.vertexBuffer)

        # Set new stimulus
        self._current = new_stimulus(self, **kwargs)

        # Set new time when protocol should advance
        if duration is not None:
            self._advanceTime = self._time + duration
        else:
            self._advanceTime = None

        # FINALLY: dispatch resize event
        self.display._glWindow.dispatch_event('on_resize', self.display._glWindow.width, self.display._glWindow.height)

    def draw(self, dt):
        self._time += dt

        if self._shouldAdvance() or self._current is None:
            self._advance()

        self._current.draw(dt)

    def _shouldAdvance(self):
        if (self._advanceTime is None) or (self._time < self._advanceTime):
            return False
        return True
