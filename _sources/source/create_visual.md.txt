# Creating a new visual

Visuals are a way to define what's being shown on a display device, like a computer or a video projector screen, during an experiment. 
All visuals should inherit directly from one of the base visuals, which are direct subclasses of `AbstractVisual` in the `vxpy.core.visual` module. 

## Base visuals

Currently existing base visual classes are:

### `vxpy.core.visual.BaseVisual`
A visual with a perspective projection on the 2 or 3D model without any particular transformation

### `vxpy.core.visual.PlanarVisual` 
Stimuli meant to be presented on a flat screen. Coordinates are defined in a 2D cartesian coordinate system in the range from -1.0 to +1.0. 
The base unit for `PlanarVisual`s is **mm** and the conversion for a given display situation is based on the `CALIB_DISP_PLA_*` calibration parameters.

### `vxpy.core.visual.SphericalVisual`
Stimuli meant to be presented on a spherical surface, using the 4-way projection system described **here** (coming soon-ish). 
The coordinate system for models is a unit sphere and the necessary conversion to fit the display situation is based on the `CALIB_DISP_SPH_*` calibration parameters.


## Example: creating a moving grating visual stimulus

### On a flat surface (e.g. projection from below onto a petridish)

All visuals need to implement the `__init__`, `initialize` and `render` methods. 

The constructor `__init__` creates everything needed to run the visual stimulus and also initializes its parent base visual class (`PlanarVisual`, `SphericalVisual`, etc) by passing all arguments to it.

The `initialize` method resets the visual stimulus prior to each presentation.

The 'render' method gets called with a single argument `dt`, which contains the elapsed time since the last presented frame. 
It, as the name implies, is used to render the scene for the visual display.

#### Minmal visual implementation

A minimal implementation of a `PlanarVisual` looks like this:
```python
import vxpy.core.visual as vxvisual

class BlackAndWhiteGrating(vxvisual.PlanarVisual):

    def __init__(self, *args, **kwargs):
        vxvisual.PlanarVisual.__init__(self, *args, **kwargs)
        
    def initialize(self, **kwargs):
        """Method to initialize and reset all parameters."""

    def render(self, dt: float):
        """This function is called for each rendered frame"""

```
The above implementation would, however, not display anything, because we didn't tell it what to do. 


#### Creating shader program and defining visual parameters
In order to make the visual display something when active, we need to define a **program** and parameters that dictate what the program should do. 
`vxPy` uses the [VisPy](https://github.com/vispy/vispy) library for fast and easy 2d and 3d visualization, so the program is an instance of `vispy.gloo.Program`. 

Generally, a program consists of a mesh model of something to be displayed (e.g. a 2D plane, sphere, ...) and two so-called shaders, a vertex and a fragment shader, which perform linear transformations on the model (vertex) and determine pixel colors (fragment) based on those coordinates and additional global parameters (uniforms). 

VisPy uses OpenGL to accomplish visualizations (for more in-depth information on how to program 2D and 3D visualizations in OpenGL, have a look at [this](https://learnopengl.com/Getting-started/OpenGL) great tutorial).

The shader program must be created in the `__init__` method of the visual class:
```python
from vispy import gloo

import vxpy.core.visual as vxvisual
from vxpy.utils import plane

class BlackAndWhiteGrating(vxvisual.PlanarVisual):

    # Define parameters
    time = vxvisual.FloatParameter('time', internal=True)
    waveform = vxvisual.IntParameter('waveform', static=True)
    direction = vxvisual.IntParameter('direction', static=True)
    linear_velocity = vxvisual.FloatParameter('linear_velocity', static=True)
    spatial_period = vxvisual.FloatParameter('spatial_period', static=True)
    
    def __init__(self, *args, **kwargs):
        vxvisual.PlanarVisual.__init__(self, *args, **kwargs)

        # Set up model of a 2d plane
        self.plane_2d = plane.XYPlane()

        # Get vertex positions and corresponding face indices
        vertices = self.plane_2d.a_position  # These are the coordinates in a [-1.0, 1.0] 2D cartesian coordinate system
        faces = self.plane_2d.indices  # These are the indices of connected vertices to form triangles (so-called faces)

        # Create vertex and index buffers to be passed to program
        self.index_buffer = gloo.IndexBuffer(faces)
        self.position_buffer = gloo.VertexBuffer(vertices)

        # Create a shader program
        # Load shaders
        vert = self.load_vertex_shader('./planar_grating.vert')
        frag = self.load_shader('./planar_grating.frag')
        # Create program
        self.grating = gloo.Program(vert, frag)

        # Connect the parameters to the program for automatic updating on change
        self.time.connect(self.grating)
        self.waveform.connect(self.grating)
        self.direction.connect(self.grating)
        self.linear_velocity.connect(self.grating)
        self.spatial_period.connect(self.grating)

    def render(self, frame_time):
        """This function is called at least once for every new rendered frame"""
```


#### Vertex shader
The vertex shader takes care of any transformations necessary for the physical presentation. 
It sets the `gl_Position` variable and may pass additional coordinates such as `v_position` (real coordinates, mapped to mm) or normalized positions (`v_nposition`) on to the fragment shader.

In most simple cases this example vertex shader would suffice:
```glsl
// Vertex shader: ./planar_grating.vert

// Input
attribute vec3 a_position;

// Output
varying vec2 v_position;
varying vec2 v_nposition;

// Main
void main() {
    gl_Position = transform_position(a_position);
    v_position = real_position(a_position);
    v_nposition = norm_position(a_position);
}
```

#### Fragment shader
The fragment shader defines what should ultimately be displayed, based on the position (here `v_position` in mm) and global visual parameters (`uniforms`).

In the case of this moving grating stimulus, it uses the `direction` value to determine whether the grating moves along the x- or y-axis. 
The `linear_velocity` [mm/s] and `spatial_period` [mm] determine the sinusoidal brightness value for a pixel at a given `v_position` [mm].
The `waveform` optionally thresholds the sinewave to create a binary grating.

```glsl
// Fragment shader: ./planar_grating.frag

// Constants
const float PI = 3.14159265359;

// Uniform input
uniform int waveform;
uniform int direction;
uniform float linear_velocity;
uniform float spatial_period;
uniform float time;

// Input
varying vec2 v_position;

void main() {

    // Set position to be used
    float p;
    if (direction == 1) {
        p = v_position.y;
    } else {
        p = v_position.x;
    }

    // Calculate brightness using position
    float c = sin((p + time * linear_velocity) / spatial_period * 2.0 * PI);

    // If shape is rectangular (1): apply threshold to brightness
    if(waveform == 1) {
        c = step(c, 0.);
    }

    // Set final color
    gl_FragColor = vec4(c, c, c, 1.0);
}
```

#### Resetting the visual and rendering a frame
With the code above, the visual stimulus would, in principle, be able to display a grating. 
However, we actually need to tell the program to draw the stimulus. 
For this, the `render` method needs to be implemented:

```python
from vispy import gloo

import vxpy.core.visual as vxvisual
from vxpy.utils import plane

class BlackAndWhiteGrating(vxvisual.PlanarVisual):
    
    # Define parameters
    time = vxvisual.FloatParameter('time', internal=True)
    waveform = vxvisual.IntParameter('waveform', static=True)
    direction = vxvisual.IntParameter('direction', static=True)
    linear_velocity = vxvisual.FloatParameter('linear_velocity', static=True)
    spatial_period = vxvisual.FloatParameter('spatial_period', static=True)
    
    def __init__(self, *args, **kwargs):
        vxvisual.PlanarVisual.__init__(self, *args, **kwargs)

        # Set up model of a 2d plane
        self.plane_2d = plane.XYPlane()

        # Get vertex positions and corresponding face indices
        vertices = self.plane_2d.a_position  # These are the coordinates in a [-1.0, 1.0] 2D cartesian coordinate system
        faces = self.plane_2d.indices  # These are the indices of connected vertices to form triangles (so-called faces)

        # Create vertex and index buffers to be passed to program
        self.index_buffer = gloo.IndexBuffer(faces)
        self.position_buffer = gloo.VertexBuffer(vertices)

        # Create a shader program
        # Load shaders
        vert = self.load_vertex_shader('./planar_grating.vert')
        frag = self.load_shader('./planar_grating.frag')
        # Create program
        self.grating = gloo.Program(vert, frag)

        # Connect the parameters to the program for automatic updating on change
        self.time.connect(self.grating)
        self.waveform.connect(self.grating)
        self.direction.connect(self.grating)
        self.linear_velocity.connect(self.grating)
        self.spatial_period.connect(self.grating)
    
    def initialize(self, *args, **kwargs):
        # Reset time to 0.0 on each visual initialization
        self.time.data = 0.0
        
    def render(self, dt):
        # Add elapsed time to time
        self.time.data += dt

        # Apply default transforms to the program for mapping according to hardware calibration
        self.apply_transform(self.grating)

        # Draw the actual visual stimulus using the indices of the triangular faces
        self.grating.draw('triangles', self.index_buffer)
```
The `render` method first increments the `time` parameter by the elapsed time since the last time it was called. 
It then calls the `apply_transform` method on the shader program to apply any necessary transforms to the program's models.

Finally, the draw method of the shader program is called, telling `VisPy` to render the scene.

Note, that the `initialze` method here simply resets the time back to zero. 
This means, that repeated stimulations with this particular visual don't carry any history effect.

#### Interactive visual stimulation
The code above would now be a fully functional visual stimulus that could be used as part of a [stimulation protocol](./create_protocol). 
Beyond that, `vxPy` also supports interactive visual stimulation, for testing of stimuli or quick probing of different parameter combinations outside of any experimental protocol.
In order for this to work, a valid parameter range and default values may optionally be specified for each parameter:

```python
class BlackAndWhiteGrating(vxvisual.PlanarVisual):
    
    # Define parameters
    time = vxvisual.FloatParameter('time', internal=True)
    
    waveform = vxvisual.IntParameter('waveform', static=True,
                                     value_map={'rectangular': 1, 'sinusoidal': 2})
    
    direction = vxvisual.IntParameter('direction', static=True,
                                      value_map={'vertical': 1, 'horizontal': 2})
    
    linear_velocity = vxvisual.FloatParameter('linear_velocity', static=True, 
                                              default=10, limits=(-80, 80), step_size=5)
    
    spatial_period = vxvisual.FloatParameter('spatial_period', static=True, 
                                             default=10, limits=(-100, 100), step_size=5)
```
Note, that the `time` parameter has no default value or range. This is because it is marked as `internal=True`, meaning it may not be changed externally. 
Only the visual itself may manipulate the `time` in this case.

### On a spherical surface (here using the 4-way projection optics)

Generating a moving grating stimulus on a spherical surface is almost identical to the planar case outlines above. 

There are two major differences. 
The first is, that the visual needs to subclass the `SphericalVisual` class, instead of `PlanarVisual`.
The second is, that the model here needs to be in 3D, because the visual stimulus is created on a spherical 3D surface.

A working example of a moving grating stimulus for a spherical display situation may look as follows:
```python
from vispy import gloo

import vxpy.core.visual as vxvisual
from vxpy.utils import sphere


class RotatingSphericalGrating(vxvisual.SphericalVisual):
    """Black und white contrast grating stimulus on a sphere
    """
    # (optional) Add a short description
    description = 'A rotating spherical grating stimulus'

    # Define parameters
    time = vxvisual.FloatParameter('time', internal=True)
    angular_velocity = vxvisual.FloatParameter('angular_velocity', static=True)
    angular_period = vxvisual.FloatParameter('angular_period', static=True)

    # Paths to shaders
    VERT_PATH = './spherical_grating.vert'
    FRAG_PATH = './spherical_grating.frag'

    def __init__(self, *args, **kwargs):
        vxvisual.SphericalVisual.__init__(self, *args, **kwargs)

        # Set up 3d model of sphere
        self.sphere = sphere.UVSphere()
        self.index_buffer = gloo.IndexBuffer(self.sphere.indices)
        self.position_buffer = gloo.VertexBuffer(self.sphere.a_position)
        self.azimuth_buffer = gloo.VertexBuffer(self.sphere.azimuth_degree)
        self.elevation_buffer = gloo.VertexBuffer(self.sphere.elevation_degree)

        # Set up program
        self.grating = gloo.Program(self.load_vertex_shader(self.VERT_PATH), self.load_shader(self.FRAG_PATH))

        # Set positions with buffers
        self.grating['a_position'] = self.position_buffer
        self.grating['a_azimuth'] = self.azimuth_buffer
        self.grating['a_elevation'] = self.elevation_buffer
        
        # Connect parameters (this makes them be automatically updated in the connected programs)
        self.time.connect(self.grating)
        self.angular_velocity.connect(self.grating)
        self.angular_period.connect(self.grating)

    def initialize(self, **params):
        # Reset u_time to 0 on each visual initialization
        self.time.data = 0.0

    def render(self, dt):
        # Add elapsed time to u_time
        self.time.data += dt

        # Apply default transforms to the program for mapping according to hardware calibration
        self.apply_transform(self.grating)

        # Draw the actual visual stimulus using the indices of the  triangular faces
        self.grating.draw('triangles', self.index_buffer)
```


## Creating new base visuals (advanced)

Subclasses of `AbstractVisual` (base visuals) should define a [visual mapping](create_visual_base_advanced.md). 
They represent a transformation of a 2d or 3d model based on a set of parameters meant to translate the model to fit a physical display situation. 

