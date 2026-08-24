# widgets.py
from PyQt6.QtWidgets import QSlider
from PyQt6.QtCore import Qt

class CustomSlider(QSlider):
    """Кастомный слайдер с компактными ручками"""
    def __init__(self, orientation=Qt.Orientation.Horizontal, parent=None):
        super().__init__(orientation, parent)