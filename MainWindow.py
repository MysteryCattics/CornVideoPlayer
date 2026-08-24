import sys
import os
import tempfile
import json
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QStackedWidget, QMessageBox, QMainWindow
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from PlaylistPlayer import PlaylistPlayer
from MainPage import MainPage
from ThemeManager import ThemeManager
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent  # добавь это после импортов

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CORN SECURE VIDEO PLAYER")
        self.setGeometry(100, 100, 900, 600)
        self.setMinimumSize(700, 600)
        self.setWindowIcon(QIcon(str(BASE_DIR / "Logo.ico")))
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.stacked_widget = QStackedWidget()
        
        self.main_page = MainPage()
        self.main_page.play_file_selected.connect(self.play_single_file)
        self.main_page.play_folder_selected.connect(self.play_folder_files)
        self.main_page.playlist_selected.connect(self.open_playlist_player)
        self.main_page.theme_changed.connect(self.on_theme_changed)
        
        self.stacked_widget.addWidget(self.main_page)
        
        layout = QVBoxLayout(self.central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stacked_widget)
    
    def on_theme_changed(self, theme_name):
        ThemeManager.apply_theme(QApplication.instance(), theme_name)
        self.update()
        for widget in self.findChildren(QWidget):
            widget.update()

    def play_single_file(self, file_path):
        player = PlaylistPlayer([file_path], os.path.basename(file_path))
        index = self.stacked_widget.addWidget(player)
        self.stacked_widget.setCurrentIndex(index)
        player.back_to_main.connect(self.show_main_page)

    def play_folder_files(self, files_list):
        if not files_list:
            QMessageBox.warning(self, "Внимание", "Нет файлов для воспроизведения!")
            return
        
        player = PlaylistPlayer(files_list, f"{len(files_list)} файлов")
        index = self.stacked_widget.addWidget(player)
        self.stacked_widget.setCurrentIndex(index)
        player.back_to_main.connect(self.show_main_page)

    def open_playlist_player(self, playlist_name):
        db = self.main_page.read_internal_db()
        raw_files = db.get(playlist_name, [])
        
        # поддержка старого формата (просто строки) и нового (объекты)
        entries = []
        for item in raw_files:
            if isinstance(item, str):
                entries.append({"path": item, "password": ""})
            else:
                entries.append(item)
        
        valid_entries = [e for e in entries if os.path.exists(e["path"])]
        
        if valid_entries:
            player = PlaylistPlayer(valid_entries, f"Плейлист: {playlist_name}")
            index = self.stacked_widget.addWidget(player)
            self.stacked_widget.setCurrentIndex(index)
            player.back_to_main.connect(self.show_main_page)
        else:
            QMessageBox.warning(self, "Внимание", "Файлы плейлиста не найдены на диске!")
    
    def show_main_page(self):
        while self.stacked_widget.count() > 1:
            widget = self.stacked_widget.widget(1)
            self.stacked_widget.removeWidget(widget)
            widget.deleteLater()
        
        self.stacked_widget.setCurrentIndex(0)
    
    def handle_command_line_arguments(self, args=None):
        """Обработка аргументов командной строки."""
        if args is None:
            args = sys.argv[1:]

        if not args:
            return

        # Обрабатываем первый переданный путь.
        path = os.path.abspath(os.path.expanduser(args[0]))

        if not os.path.exists(path):
            QMessageBox.warning(
                self,
                "Внимание",
                f"Указанный путь не существует:\n{path}"
            )
            return

        if os.path.isfile(path):
            self.play_single_file(path)

        elif os.path.isdir(path):
            files = self.get_crn_files_from_folder(path)
            if files:
                self.play_folder_files(files)
            else:
                QMessageBox.warning(
                    self,
                    "Внимание",
                    "В указанной папке не найдено .crn файлов!"
                )

    def get_crn_files_from_folder(self, folder_path):
        """Получить все .crn файлы из папки."""
        crn_files = []
        try:
            for file in os.listdir(folder_path):
                if file.lower().endswith(".crn"):
                    full_path = os.path.join(folder_path, file)
                    if os.path.isfile(full_path):
                        crn_files.append(full_path)
            crn_files.sort()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось прочитать папку: {str(e)}"
            )
        return crn_files

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            current_widget = self.stacked_widget.currentWidget()
            if isinstance(current_widget, PlaylistPlayer):
                current_widget.back_to_main_page()
            else:
                self.close()
        else:
            super().keyPressEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    current_theme = ThemeManager.get_current_theme()
    ThemeManager.apply_theme(app, current_theme)

    mw = MainWindow()
    mw.show()
    mw.handle_command_line_arguments()
    sys.exit(app.exec())