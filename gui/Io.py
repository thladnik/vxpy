"""
MappApp ./gui/Io.py - Custom addons which handle UI and visualization of IO.
Copyright (C) 2020 Tim Hladnik

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
from PyQt5 import QtCore, QtWidgets
import pyqtgraph as pg

import Config
import Def
import IPC
import routines.io.Core

class IoWidget(QtWidgets.QWidget):
    def __init__(self, parent, **kwargs):
        ### Set module always to active
        self.moduleIsActive = True
        QtWidgets.QWidget.__init__(self, parent, **kwargs)
        self.setLayout(QtWidgets.QGridLayout())

        self.graphicsWidget = IoWidget.GraphicsWidget(parent=self)
        self.layout().addWidget(self.graphicsWidget, 0, 0)

        ### Build up data structure
        self.data = dict()
        for routine_name in Config.Io[Def.IoCfg.routines]:
            if not(bool(routine_name)):
                continue

            routine = getattr(routines.io.Core, routine_name)

            self.data[routine_name] = dict()

            for pin_descr in routine.pins:
                pin_name, pnum, ptype = pin_descr.split(':')

                self.data[routine_name][pin_name] = dict(datat=list(), datay=list(), last_idx=0)

        ### Start timer
        self._tmr_update = QtCore.QTimer()
        self._tmr_update.setInterval(100)
        self._tmr_update.timeout.connect(self.updateData)
        self._tmr_update.start()

    def updateData(self):
        pin_data = None

        idx_range = 1000

        for routine_name, pins in self.data.items():
            for pin_name, pin_data in pins.items():
                idcs, newdata = IPC.Routines.Io.readAttribute(
                    ['time', pin_name],
                    routine_name,
                    last_idx=pin_data['last_idx'])

                if newdata is None:
                    continue

                try:
                    pin_data['datat'].extend(newdata['time'])
                    pin_data['datay'].extend(newdata[pin_name])
                    pin_data['last_idx'] = idcs[-1]
                except:
                    pin_data['datat'].append(newdata['time'])
                    pin_data['datay'].append(newdata[pin_name])
                    pin_data['last_idx'] = idcs


                ### Leaving the GUI running for long periods of time causes stuttering, when the
                # lists get too long. There is a pull request for pyqtgraph (https://github.com/pyqtgraph/pyqtgraph/pull/850)
                # which implements the PlotDataItem.appendData method, but it's not been merged yet
                # Until the fix is implemented just show a realtime snippet of the IO-data
                if len(pin_data['datat']) <= idx_range:
                    self.graphicsWidget.dataItems[pin_name].setData(pin_data['datat'][:],
                                                                    pin_data['datay'][:])
                else:
                    self.graphicsWidget.dataItems[pin_name].setData(pin_data['datat'][-idx_range:],
                                                                    pin_data['datay'][-idx_range:])
                #self.graphicsWidget.dataItems[pin_name].setData(pin_data['datat'], pin_data['datay'])

        ### Move display range
        if not(pin_data is None):

            xMax = pin_data['datat'][-1]
            if len(pin_data['datat']) <= idx_range:
                xMin = 0
            else:
                xMin = pin_data['datat'][-idx_range]
            self.graphicsWidget.dataPlot.setRange(xRange=(xMin,xMax))

            ### See above
            #xMax = pin_data['datat'][-1]
            #self.graphicsWidget.dataPlot.setRange(xRange=(xMax-10,xMax))


    class GraphicsWidget(pg.GraphicsLayoutWidget):
        def __init__(self, **kwargs):
            pg.GraphicsLayoutWidget.__init__(self, **kwargs)

            ### Add plot
            self.dataPlot = self.addPlot(0, 0, 1, 10)

            self.dataItems = dict()
            ### Set up plot image item
            for i, digital_pin in enumerate(Config.Io[Def.IoCfg.pins]):
                pname, pnum, ptype = digital_pin.split(':')

                if i == 0:
                    c = '#F00'
                elif i == 1:
                    c = '#0F0'
                else:
                    c = '#00F'
                self.dataItems[pname] = pg.PlotDataItem(pen=c)
                self.dataPlot.addItem(self.dataItems[pname])

                i += 1

            #self.imagePlot.hideAxis('left')
            #self.imagePlot.hideAxis('bottom')
            #self.imagePlot.setAspectLocked(True)
            #self.imagePlot.vb.setMouseEnabled(x=False, y=False)