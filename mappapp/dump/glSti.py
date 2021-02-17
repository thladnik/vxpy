import functools
from glumpy import app, gl
from IPython import embed


class _defaultize:
    def __init__(self, func, default_func=None):
        functools.update_wrapper(self, func)
        self._func = func
        self._defaultFunc = default_func

    def __call__(self, *args, **kwargs):
        if len(args) + len(kwargs) > 0:
            return self._func(*args, **kwargs)
        else:
            if self._defaultFunc:
                return self._defaultFunc(*args, **kwargs)
            else:
                assert "No default function available"


def fill_default(default_func=None):
    def wrapper(function):
        return _defaultize(function, default_func=default_func)

    return wrapper


class glSti():
    def __init__(self):
        # self.__window = app.Window
        # self.__backend = app.use
        self.__ondraw_init()
        self.__onresize_init()
        self.__oninit_init()
        # self.fragment_shader = None
        # self.vertex_shader = None
        # self.UserBuffer = None
        # self.Program = None

    # def run(self):
    #     self.backend = self.__backend()
    #     self.window = self.__window()



    def __ondraw_init(self):
        @app.window.event.EventDispatcher.event
        def on_draw(dt):
            pass

        self.on_draw = on_draw

    def __onresize_init(self):
        @app.window.event.EventDispatcher.event
        def on_resize(width, height):
            pass

        self.on_resize = on_resize

    def __oninit_init(self):
        @app.window.event.EventDispatcher.event
        def on_init(height):
            gl.glEnable(gl.GL_DEPTH_TEST)

        self.on_init = on_init

    def set_ondraw(self,func):
        self.on_draw = app.window.event.EventDispatcher.event(func)

    def set_onresize(self,func):
        @app.window.event.EventDispatcher.event
        def wrapper(*args,**kwargs):
            return func(*args,**kwargs)
        self.on_resize = wrapper


    def set_oninit(self,func):
        @app.window.event.EventDispatcher.event
        def wrapper(*args,**kwargs):
            return func(*args,**kwargs)
        self.on_init = wrapper

    def __init_init(self):
        def program_init():
            pass

        self.program_init = program_init
