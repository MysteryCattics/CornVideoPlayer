import json
import os
import sys
from pathlib import Path
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QGridLayout, QWidget, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal

# Путь к папке пользователя
USER_DATA_DIR = Path.home() / ".cornvideoplayer"
_THEME_FILE = USER_DATA_DIR / "settings" / "theme.json"

class ThemeManager:
    """Менеджер цветовых тем"""
    
    THEME_COLORS = {
        "orange": ("🌕 Оранжевая", "#ff9800", "Оранжевая тема (по умолчанию)"),
        "red": ("🔴 Красная", "#f44336", "Энергичная красная тема"),
        "green": ("🟢 Зелёная", "#4CAF50", "Спокойная зелёная тема"),
        "blue": ("🔵 Синяя", "#2196F3", "Холодная синяя тема"),
        "purple": ("🟣 Фиолетовая", "#9C27B0", "Креативная фиолетовая тема"),
        "teal": ("💎 Бирюзовая", "#009688", "Современная бирюзовая тема"),
        "pink": ("🌸 Розовая", "#E91E63", "Нежная розовая тема"),
        "amber": ("⭐ Янтарная", "#FFC107", "Тёплая янтарная тема"),
    }
    
    @staticmethod
    def get_current_theme():
        try:
            if _THEME_FILE.exists():
                with open(_THEME_FILE, "r", encoding='utf-8') as f:
                    settings = json.load(f)
                    theme = settings.get("theme", "orange")
                    if theme not in ThemeManager.THEME_COLORS:
                        return "orange"
                    return theme
        except:
            pass
        return "orange"

    @staticmethod
    def save_theme(theme_name):
        _THEME_FILE.parent.mkdir(parents=True, exist_ok=True)
        settings = {"theme": theme_name}
        with open(_THEME_FILE, "w", encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
    
    @staticmethod
    def apply_theme(app, theme_name="orange"):
        """Применить цветовую тему"""
        if theme_name not in ThemeManager.THEME_COLORS:
            theme_name = "orange"
        
        color = ThemeManager.THEME_COLORS[theme_name][1]
        
        # Устанавливаем палитру
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(18, 18, 18))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(42, 42, 42))
        palette.setColor(QPalette.ColorRole.Text, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.Button, QColor(42, 42, 42))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(color))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Link, QColor(color))
        
        app.setPalette(palette)
        
        # Стили для всех элементов
        style = f"""
            QMainWindow, QDialog, QWidget {{
                background-color: #121212;
                color: #f0f0f0;
                border: none;
                font-size: 13px;
            }}
            
            QPushButton {{
                background-color: #2a2a2a;
                color: #f0f0f0;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                min-height: 28px;
                font-size: 13px;
            }}
            
            QPushButton:hover {{
                background-color: #353535;
                border-color: #555555;
            }}
            
            QPushButton:pressed {{
                background-color: #1e1e1e;
                border-color: #333333;
            }}
            
            .accent-button {{
                background-color: #2a2a2a;
                color: {color};
                border: 1px solid #444444;
                border-radius: 6px;
            }}
            
            .accent-button:hover {{
                background-color: #353535;
                border-color: #555555;
                color: {ThemeManager._lighten_color(color)};
            }}
            
            .accent-button:pressed {{
                background-color: #1e1e1e;
                border-color: #333333;
            }}

            .filled-accent-button {{
                background-color: {color};
                color: #000000;
                border: 1px solid #444444;
                border-radius: 5px;
                font-weight: bold;
            }}

            .filled-accent-button:hover {{
                background-color: {ThemeManager._lighten_color(color)};
                border-color: #555555;
                color: #000000;
            }}

            .filled-accent-button:pressed {{
                background-color: {ThemeManager._darken_color(color)};
                border-color: #333333;
                color: #000000;
            }}
            
            QLabel {{
                color: #f0f0f0;
                background-color: transparent;
                font-size: 13px;
            }}
            
            .accent-label {{
                color: {color};
                font-weight: bold;
            }}

            #mainTitleLabel {{
                font-size: 24px;
                font-weight: bold;
                color: {color};
                margin-bottom: 10px;
                padding: 10px;
                background-color: #1e1e1e;
                border-radius: 8px;
                border: 1px solid #333;
            }}

            #subtitleLabel {{
                font-size: 14px;
                color: #bbbbbb;
                margin-bottom: 15px;
            }}

            #playlistLabel {{
                font-size: 16px;
                font-weight: bold;
                color: {color};
                margin-bottom: 8px;
                padding: 8px;
                background-color: #1e1e1e;
                border-radius: 6px;
                border: 1px solid #333;
            }}

            #statusLabel {{
                color: #888888;
                font-size: 11px;
                margin-top: 10px;
                padding: 4px;
                background-color: #1e1e1e;
                border-radius: 4px;
                border: 1px solid #333;
            }}

            #playerTitleLabel {{
                color: {color};
                font-weight: bold;
                font-size: 14px;
                padding: 5px;
            }}

            #playerListHeader {{
                color: {color};
                font-weight: bold;
                font-size: 14px;
                padding: 5px;
                border-bottom: 1px solid #444;
                margin-bottom: 5px;
            }}
            
            QListWidget {{
                background-color: #1e1e1e;
                color: #f0f0f0;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 2px;
                outline: none;
                font-size: 13px;
            }}
            
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid #2a2a2a;
                background-color: transparent;
                font-size: 13px;
                border-radius: 4px;
                margin: 1px;
            }}
            
            QListWidget::item:selected {{
                background-color: {color};
                color: #000000;
                border-radius: 6px;
                font-weight: bold;
            }}
            
            QListWidget::item:hover {{
                background-color: #2a2a2a;
                border-radius: 6px;
            }}
            
            QLineEdit {{
                background-color: #1e1e1e;
                color: #f0f0f0;
                border: 2px solid #555;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                selection-background-color: {color};
                selection-color: #000000;
            }}
            
            QLineEdit:focus {{
                border: 2px solid {color};
                background-color: #252525;
            }}
            
            QSlider::groove:horizontal {{
                height: 6px;
                background: #333;
                border-radius: 3px;
                margin: 0px;
            }}
            
            QSlider::sub-page:horizontal {{
                background: {color};
                border-radius: 3px;
            }}
            
            QSlider::add-page:horizontal {{
                background: #444;
                border-radius: 3px;
            }}
            
            QSlider::handle:horizontal {{
                background: #ffffff;
                width: 18px;
                height: 18px;
                margin: -6px 0;
                border-radius: 9px;
                border: 2px solid {color};
            }}
            
            QSlider::handle:horizontal:hover {{
                background: {ThemeManager._lighten_color(color)};
                width: 20px;
                height: 20px;
                margin: -7px 0;
                border-radius: 10px;
                border: 2px solid {color};
            }}
            
            QSlider::handle:horizontal:pressed {{
                background: {ThemeManager._darken_color(color)};
                border: 2px solid {ThemeManager._darken_color(color)};
            }}

            QSlider::groove:vertical {{
                width: 6px;
                background: #333;
                border-radius: 3px;
                margin: 0px;
            }}
            
            QSlider::sub-page:vertical {{
                background: {color};
                border-radius: 3px;
            }}
            
            QSlider::add-page:vertical {{
                background: #444;
                border-radius: 3px;
            }}
            
            QSlider::handle:vertical {{
                background: #ffffff;
                width: 18px;
                height: 18px;
                margin: 0 -6px;
                border-radius: 9px;
                border: 2px solid {color};
            }}
            
            QSlider::handle:vertical:hover {{
                background: {ThemeManager._lighten_color(color)};
                width: 20px;
                height: 20px;
                margin: 0 -7px;
                border-radius: 10px;
                border: 2px solid {color};
            }}
            
            QSlider::handle:vertical:pressed {{
                background: {ThemeManager._darken_color(color)};
                border: 2px solid {ThemeManager._darken_color(color)};
            }}
            
            QVideoWidget {{
                background-color: #000000;
            }}
            
            QMessageBox {{
                background-color: #1e1e1e;
            }}
            
            QMessageBox QLabel {{
                color: #f0f0f0;
            }}
            
            QMessageBox QPushButton {{
                min-width: 80px;
            }}
            
            QToolTip {{
                background-color: #252525;
                color: #f0f0f0;
                border: 1px solid {color};
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
            }}
        """
        
        app.setStyleSheet(style)
    
    @staticmethod
    def _lighten_color(color_hex):
        color = QColor(color_hex)
        return color.lighter(120).name()
    
    @staticmethod
    def _darken_color(color_hex):
        color = QColor(color_hex)
        return color.darker(120).name()


class ThemeDialog(QDialog):
    theme_selected = pyqtSignal(str)
    
    def __init__(self, current_theme="orange"):
        super().__init__()
        self.current_theme = current_theme
        self.setWindowTitle("Выбор цветовой темы")
        self.setFixedSize(550, 450)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
            }
        """)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        accent_color = ThemeManager.THEME_COLORS.get(self.current_theme, ("","", "#ff9800"))[1]
        
        title = QLabel("🎨 Выбор цветовой темы")
        title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {accent_color};
            margin-bottom: 10px;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        desc = QLabel("Выберите цветовую схему для приложения:")
        desc.setStyleSheet("color: #bbbbbb; font-size: 13px;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
        """)
        
        colors_widget = QWidget()
        colors_layout = QGridLayout(colors_widget)
        colors_layout.setSpacing(15)
        colors_layout.setContentsMargins(5, 5, 5, 5)
        
        themes = list(ThemeManager.THEME_COLORS.items())
        
        for i, (theme_id, (theme_name, color_code, theme_desc)) in enumerate(themes):
            row = i // 2
            col = i % 2
            
            theme_card = self.create_theme_card(theme_id, theme_name, color_code, theme_desc)
            colors_layout.addWidget(theme_card, row, col)
        
        scroll.setWidget(colors_widget)
        layout.addWidget(scroll, 1)
        
        buttons_layout = QHBoxLayout()
        
        self.current_theme_label = QLabel(f"Текущая тема: {ThemeManager.THEME_COLORS.get(self.current_theme, ('Неизвестная',))[0]}")
        self.current_theme_label.setStyleSheet("color: #888; font-size: 12px;")
        buttons_layout.addWidget(self.current_theme_label)
        
        buttons_layout.addStretch()
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setFixedSize(100, 35)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
    
    def create_theme_card(self, theme_id, theme_name, color_code, theme_desc):
        card = QWidget()
        card.setFixedHeight(100)
        
        if theme_id == self.current_theme:
            card.setStyleSheet(f"""
                QWidget {{
                    background-color: {color_code}20;
                    border: 2px solid {color_code};
                    border-radius: 10px;
                    padding: 10px;
                }}
            """)
        else:
            card.setStyleSheet("""
                QWidget {
                    background-color: #1e1e1e;
                    border: 1px solid #333;
                    border-radius: 10px;
                    padding: 10px;
                }
                QWidget:hover {
                    background-color: #252525;
                    border: 1px solid #444;
                }
            """)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 10, 10, 10)
        
        color_circle = QLabel("●")
        color_circle.setFixedSize(40, 40)
        color_circle.setStyleSheet(f"""
            background-color: {color_code};
            color: white;
            border-radius: 20px;
            font-size: 24px;
            padding: 5px;
            border: 2px solid {color_code}80;
        """)
        color_circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        title_label = QLabel(theme_name)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #ffffff;")
        
        desc_label = QLabel(theme_desc)
        desc_label.setStyleSheet("color: #888; font-size: 11px;")
        desc_label.setWordWrap(True)
        
        info_layout.addWidget(title_label)
        info_layout.addWidget(desc_label)
        info_layout.addStretch()
        
        select_btn = QPushButton("Выбрать" if theme_id != self.current_theme else "✓ Выбрана")
        select_btn.setFixedSize(90, 30)
        select_btn.setProperty("theme", theme_id)
        select_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        if theme_id == self.current_theme:
            select_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #2a2a2a;
                    color: {color_code};
                    border: 1px solid #444444;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                }}
            """)
            select_btn.setEnabled(False)
        else:
            select_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #2a2a2a;
                    color: #f0f0f0;
                    border: 1px solid #444444;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #353535;
                    border-color: #555555;
                    color: {color_code};
                }}
                QPushButton:pressed {{
                    background-color: #1e1e1e;
                    border-color: #333333;
                }}
            """)
            select_btn.clicked.connect(self.on_theme_selected)
        
        card_layout.addWidget(color_circle)
        card_layout.addLayout(info_layout, 1)
        card_layout.addWidget(select_btn)
        
        return card
    
    def on_theme_selected(self):
        btn = self.sender()
        theme_id = btn.property("theme")
        self.theme_selected.emit(theme_id)
        self.accept()