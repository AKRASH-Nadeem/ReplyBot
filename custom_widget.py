from PyQt5 import QtCore, QtGui, QtWidgets

class Labels_Widget(QtWidgets.QWidget):
    def __init__(self,key,value):
        super().__init__()
        self.key = key
        self.value = value
        self.setupUi()
    def setupUi(self):
        self.layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel(self.key)
        label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum,QtWidgets.QSizePolicy.Policy.Preferred)
        label2 = QtWidgets.QLabel(str(self.value))
        label2.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.layout.addWidget(label)
        self.layout.addWidget(label2)
        self.setLayout(self.layout)