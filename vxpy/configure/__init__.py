from PySide6 import QtWidgets

from vxpy.configure import acc
from vxpy.configure.main import StartupConfiguration


def main():
    acc.app = QtWidgets.QApplication([])
    acc.main = StartupConfiguration()
    acc.main.setup_ui()
    acc.app.exec()