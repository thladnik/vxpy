# Creating a visual base class (advanced)

Visual base classes, are classes which directly subclass `vxpy.core.visual.AbstractVisual` (like `PlanarVisual` or `SphericalVisual`). 
They are intended to simplify the creation of new visual stimuli by taking care of transformations into real-world coordinates based on setup-specific calibrations. 
They present a way of taking care of most of the more involved OpenGL programming logic or geometric transformations in the background, so that also users with basic programming skills may design their own visual stimuli.

TODO: add example of how to implement cylindrical visual