import sys
import os
import tempfile
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QSlider, QLabel, QFileDialog, 
    QInputDialog, QLineEdit, QStackedWidget, QListWidget,
    QListWidgetItem, QMessageBox, QMainWindow, QFrame,
    QGridLayout, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QUrl, QTimer, pyqtSignal, QByteArray, QBuffer
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtGui import QPixmap, QPalette, QColor, QIcon
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from PlaylistPlayer import PlaylistPlayer
from CustomSlider import CustomSlider
from MainPage import MainPage
from ThemeManager import ThemeManager

HEADER = b"CORNFORMATv1----"

def make_key(password: str, salt: bytes):
    if not password:
        password = "default_empty_password"
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200000,
        backend=default_backend()
    )
    return kdf.derive(password.encode())

def decrypt_crn(crn_path: str, password: str) -> bytes:
    with open(crn_path, "rb") as f:
        data = f.read()
    if not data.startswith(HEADER):
        raise ValueError("Неверный формат CORN")
    data = data[len(HEADER):]
    salt = data[:16]
    iv = data[16:32]
    encrypted = data[32:]
    key = make_key(password, salt)
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    return decryptor.update(encrypted) + decryptor.finalize()

def create_ram_video(data: bytes):
    if sys.platform.startswith("linux") or sys.platform == "darwin":
        try:
            tmp = tempfile.NamedTemporaryFile(
                dir="/dev/shm",
                delete=False,
                suffix=".mp4"
            )
            tmp.write(data)
            tmp.flush()
            tmp.close()
            return "file", tmp.name
        except Exception:
            pass

    tmp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".mp4"
    )
    tmp.write(data)
    tmp.flush()
    tmp.close()

    return "file", tmp.name


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CORN SECURE PLAYER")
        self.setGeometry(100, 100, 900, 550)
        self.setMinimumSize(700, 400)
        self.setWindowIcon(QIcon("Logo.ico"))
        
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
        """Обработчик смены темы"""
        ThemeManager.apply_theme(QApplication.instance(), theme_name)
        self.update()
        for widget in self.findChildren(QWidget):
            widget.update()
        
    def get_crn_files_from_folder(self, folder_path):
        """Получить все .crn файлы из папки"""
        crn_files = []
        try:
            for file in os.listdir(folder_path):
                if file.lower().endswith('.crn'):
                    full_path = os.path.join(folder_path, file)
                    if os.path.isfile(full_path):
                        crn_files.append(full_path)
            crn_files.sort()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось прочитать папку: {str(e)}")
        
        return crn_files
    
    def play_single_file(self, file_path):
        """Воспроизведение одиночного файла"""
        player = PlaylistPlayer([file_path], os.path.basename(file_path))
        index = self.stacked_widget.addWidget(player)
        self.stacked_widget.setCurrentIndex(index)
        player.back_to_main.connect(self.show_main_page)

    def play_folder_files(self, files_list):
        """Воспроизведение списка файлов"""
        if not files_list:
            QMessageBox.warning(self, "Внимание", "Нет файлов для воспроизведения!")
            return
        
        if len(files_list) == 1:
            title = os.path.basename(files_list[0])
        else:
            dirs = set(os.path.dirname(f) for f in files_list)
            if len(dirs) == 1:
                title = f"Папка: {os.path.basename(list(dirs)[0])}"
            else:
                title = f"{len(files_list)} файлов"
        
        player = PlaylistPlayer(files_list, title)
        index = self.stacked_widget.addWidget(player)
        self.stacked_widget.setCurrentIndex(index)
        player.back_to_main.connect(self.show_main_page)

    def open_playlist_player(self, playlist_name):
        """Открытие плейлиста"""
        playlist_file = f"playlists/{playlist_name}.json"
        if os.path.exists(playlist_file):
            try:
                with open(playlist_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                video_files = data.get('files', [])
                valid_files = [f for f in video_files if os.path.exists(f)]
                
                if valid_files:
                    player = PlaylistPlayer(valid_files, f"Плейлист: {playlist_name}")
                    index = self.stacked_widget.addWidget(player)
                    self.stacked_widget.setCurrentIndex(index)
                    player.back_to_main.connect(self.show_main_page)
                else:
                    QMessageBox.warning(self, "Внимание", "Файлы из плейлиста не найдены!")
                    
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки плейлиста: {str(e)}")
    
    def show_main_page(self):
        """Показать главную страницу"""
        while self.stacked_widget.count() > 1:
            widget = self.stacked_widget.widget(1)
            self.stacked_widget.removeWidget(widget)
            widget.deleteLater()
        
        self.stacked_widget.setCurrentIndex(0)
    
    def keyPressEvent(self, event):
        """Глобальные горячие клавиши"""
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
    
    # Применяем сохранённую тему при запуске
    current_theme = ThemeManager.get_current_theme()
    ThemeManager.apply_theme(app, current_theme)

    mw = MainWindow()
    mw.show()

    if len(sys.argv) > 1:
        path = sys.argv[1]
        if os.path.exists(path):
            ext = os.path.splitext(path)[1].lower()
            if os.path.isfile(path):
                mw.play_single_file(path)
            elif os.path.isdir(path):
                files = mw.get_crn_files_from_folder(path)
                if files:
                    mw.play_folder_files(files)
                else:
                    QMessageBox.warning(mw, "Внимание", "В указанной папке не найдено .crn файлов!")
                    
    sys.exit(app.exec())