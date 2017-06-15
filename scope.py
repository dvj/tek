#! /usr/bin/env python
import argparse
import socket

import sys
from functools import partial

import datetime
from PyQt5 import QtGui
from PyQt5.QtCore import QObject, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QGridLayout, QWidget

from teksocket import TekSocket
import numpy as np
import pyqtgraph as pg


class Scope(QMainWindow):
    def __init__(self, host, port):
        super(QMainWindow, self).__init__()

        self.host = host
        self.port = port
        self.tek = None

        self.grid = QGridLayout()
        self.grid.setSpacing(0)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.plot_widget = pg.GraphicsLayoutWidget()
        self.grid.addWidget(self.plot_widget)

        win = QWidget()
        win.setLayout(self.grid)
        self.setCentralWidget(win)
        self.toolbar = self.addToolBar('Exit')

        action = QtGui.QAction('Refresh', self)
        action.setShortcut(' ')
        action.triggered.connect(self.get_data_all_channels)
        self.toolbar.addAction(action)
        self.statusBar().showMessage("Not Connected")

        self.main_plot = self.plot_widget.addPlot(title='')
        self.main_plot.showAxis('bottom', True)
        self.main_plot.setMouseEnabled(x=True, y=False)
        self.main_plot.enableAutoRange(x=True, y=True)
        self.data_plots = dict()
        self.channels = {'Ch1': {'color': (255, 255, 0)},
                         'Ch2': {'color': (0, 0, 255)},
                         'Ch3': {'color': (255, 50, 50)},
                         'Ch4': {'color': (50, 255, 50)}}
        for i in self.channels.keys():
            action = QtGui.QAction('{}'.format(i), self)
            action.setShortcut('{}'.format(i))
            action.triggered.connect(partial(self.set_data_channel, i))
            action.setCheckable(True)
            action.setChecked(False)
            self.toolbar.addAction(action)
        self.enabled_channels = list()

    def showEvent(self, event):
        super(QMainWindow, self).showEvent(event)
        QTimer().singleShot(0, self.connect)

    def connect(self):
        sb = self.statusBar()
        sb.showMessage("Connecting to {}:{}...".format(self.host, self.port))
        try:
            self.tek = TekSocket(self.host, self.port)
            self.tek.init_data()
            sb.showMessage("Connected to {}:{}".format(self.host, self.port))
        except socket.timeout as e:
            sb.showMessage("Couldn't connect to {}:{} - {}".format(self.host, self.port, e.message))

    def get_data(self, channel):
        self.main_plot.setTitle(datetime.datetime.now())
        try:
            data = self.tek.get_data(channel)
        except socket.timeout:
            return
        data = np.frombuffer(data, dtype=np.int16).newbyteorder()  # convert from MSB to LSB
        total_time = self.tek.t_scale * data.size
        t_stop = self.tek.t_start + total_time
        scaled_time = np.linspace(self.tek.t_start, t_stop, num=data.size, endpoint=False)
        double_data = np.array(data, dtype='double')
        scaled_data = (double_data - self.tek.v_pos) * self.tek.v_scale + self.tek.v_off
        if channel not in self.data_plots:
            self.data_plots[channel] = self.main_plot.plot(pen=self.channels[channel],
                                                           clipToView=True, autoDownsample=True)
        self.data_plots[channel].setData(x=scaled_time, y=scaled_data)

    def get_data_all_channels(self):
        for channel in self.enabled_channels:
            self.get_data(channel)

    def set_data_channel(self, channel_num):
        s = QObject.sender(self)
        s.setChecked(s.isChecked())
        if s.isChecked():
            self.enabled_channels.append(channel_num)
            self.get_data(channel_num)
        else:
            self.enabled_channels.remove(channel_num)
            try:
                self.main_plot.removeItem(self.data_plots[channel_num])
                self.data_plots.pop(channel_num)
            except KeyError:
                pass


def parse_args():
    parser = argparse.ArgumentParser(description='Graph',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--version', '-v', action='version', version='%(prog)s 1.0.0')
    parser.add_argument('host')
    parser.add_argument('--port', default=4000)
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    app = QApplication(sys.argv)
    scope = Scope(args.host, args.port)
    scope.show()
    code = app.exec_()
    sys.exit(code)
