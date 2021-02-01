from PyQt5 import QtWidgets


class ModuleWidget(QtWidgets.QWidget):

    def __init__(self, module_name, *_args, **_kwargs):
        QtWidgets.QWidget.__init__(self, *_args, **_kwargs)

        self.module_name = module_name

    def get_setting(self, option_name):
        global current_config
        return current_config.getParsed(self.module_name, option_name)

    def update_setting(self, option, value):
        global current_config
        current_config.setParsed(self.module_name, option, value)

    def closed_main_window(self):
        """Method called by default in MainWindow on closeEvent"""
        pass

    def load_settings_from_config(self):
        """Method called by default in MainWindow when selecting new configuration"""
        pass
