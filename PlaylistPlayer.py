import os
import tempfile
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QLabel, QPushButton,
    QSlider, QInputDialog, QMessageBox, QListWidget, QListWidgetItem, QSplitter, QLineEdit, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtGui import QPixmap
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from CustomSlider import CustomSlider

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
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    tmp.write(data)
    tmp.flush()
    tmp.close()
    return tmp.name

class VideoFile:
    def __init__(self, original_path, display_name, password="", temp_path=None):
        self.original_path = original_path
        self.display_name = display_name
        self.password = password  # <-- добавить
        self.temp_path = temp_path

    @property
    def play_path(self):
        return self.temp_path if self.temp_path else self.original_path

class PlaylistPlayer(QWidget):
    back_to_main = pyqtSignal()

    def __init__(self, files, title=""):
        super().__init__()
        self.title = title
        self.slider_is_pressed = False
        
        self.video_files = self.process_files(files)
        self.current_index = 0

        self.init_ui()
        self.load_video(self.current_index)

    def process_files(self, files):
        video_files = []
        for item in files:
            if isinstance(item, str):
                path, password = item, ""
            else:
                path, password = item["path"], item.get("password", "")
            display_name = os.path.basename(path)
            video_files.append(VideoFile(path, display_name, password=password))
        return video_files

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        top_panel = QHBoxLayout()
        top_panel.setContentsMargins(10, 5, 10, 5)
        
        self.home_btn = QPushButton("🏠")
        self.home_btn.setFixedSize(35, 30)
        self.home_btn.setToolTip("Вернуться на главную")
        self.home_btn.setProperty("class", "filled-accent-button")
        self.home_btn.clicked.connect(self.back_to_main_page)
        top_panel.addWidget(self.home_btn)
        
        self.title_label = QLabel(f"🎬 {self.title}")
        self.title_label.setObjectName("playerTitleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_panel.addWidget(self.title_label, 1)
        
        left_layout.addLayout(top_panel)

        self.video_stack = QStackedWidget()
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: #000000;")
        self.video_stack.addWidget(self.video_widget)

        self.black_screen_widget = QWidget()
        self.black_screen_widget.setStyleSheet("background-color: #000000;")
        black_screen_layout = QVBoxLayout(self.black_screen_widget)
        black_screen_layout.setContentsMargins(0,0,0,0)
        
        try:
            self.logo_label = QLabel()
            pixmap = QPixmap("Logo.png")
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    300, 200, 
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.logo_label.setPixmap(scaled_pixmap)
            else:
                self.logo_label.setText("LOGO")
                self.logo_label.setStyleSheet("color: white; font-size: 36px; font-weight: bold;")
        except:
            self.logo_label = QLabel("CORN PLAYER")
            self.logo_label.setStyleSheet("color: white; font-size: 36px; font-weight: bold;")
        
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        black_screen_layout.addWidget(self.logo_label)
        
        self.video_stack.addWidget(self.black_screen_widget)
        self.video_stack.setCurrentWidget(self.video_widget)

        left_layout.addWidget(self.video_stack, 1)

        control_panel = QWidget()
        control_panel.setFixedHeight(100)
        control_panel_layout = QVBoxLayout(control_panel)
        control_panel_layout.setContentsMargins(10, 5, 10, 10)
        control_panel_layout.setSpacing(5)

        time_layout = QHBoxLayout()
        time_layout.setContentsMargins(0, 0, 0, 0)
        self.current_time_label = QLabel("00:00")
        self.current_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_time_label.setFixedWidth(50)
        time_layout.addWidget(self.current_time_label)

        self.position_slider = CustomSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderPressed.connect(self.slider_pressed)
        self.position_slider.sliderReleased.connect(self.slider_released)
        self.position_slider.sliderMoved.connect(self.slider_moved)
        time_layout.addWidget(self.position_slider, 1)

        self.total_time_label = QLabel("00:00")
        self.total_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_time_label.setFixedWidth(50)
        time_layout.addWidget(self.total_time_label)
        
        control_panel_layout.addLayout(time_layout)

        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(10)

        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setFixedSize(45, 35)
        self.prev_btn.clicked.connect(self.prev_video)
        
        self.bw_btn = QPushButton("⏪")
        self.bw_btn.setFixedSize(45, 35)
        self.bw_btn.clicked.connect(lambda: self.skip(-10))
        
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(50, 40)
        self.play_btn.setProperty("class", "filled-accent-button")
        self.play_btn.clicked.connect(self.toggle_play)
        
        self.fw_btn = QPushButton("⏩")
        self.fw_btn.setFixedSize(45, 35)
        self.fw_btn.clicked.connect(lambda: self.skip(10))
        
        self.next_btn = QPushButton("⏭")
        self.next_btn.setFixedSize(45, 35)
        self.next_btn.clicked.connect(self.next_video)

        buttons_layout.addStretch(1)
        for b in [self.prev_btn, self.bw_btn, self.play_btn, self.fw_btn, self.next_btn]:
            buttons_layout.addWidget(b)
        buttons_layout.addStretch(1)

        volume_layout = QHBoxLayout()
        volume_layout.setContentsMargins(0, 0, 0, 0)
        volume_layout.setSpacing(5)
        
        self.volume_icon = QLabel("🔊")
        self.volume_icon.setFixedSize(25, 25)
        self.volume_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        volume_layout.addWidget(self.volume_icon)

        self.volume_slider = CustomSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.valueChanged.connect(self.set_volume)
        volume_layout.addWidget(self.volume_slider)

        self.volume_label = QLabel("50%")
        self.volume_label.setFixedWidth(35)
        volume_layout.addWidget(self.volume_label)
        
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.addLayout(buttons_layout, 2)
        bottom_row.addStretch(1)
        bottom_row.addLayout(volume_layout, 1)
        
        control_panel_layout.addLayout(bottom_row)
        left_layout.addWidget(control_panel)

        splitter.addWidget(left_widget)

        # Правая часть: список файлов
        right_widget = QWidget()
        right_widget.setMaximumWidth(300)
        right_widget.setMinimumWidth(200)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 5, 5, 5)
        
        list_header = QLabel("📁 Список файлов")
        list_header.setObjectName("playerListHeader")
        right_layout.addWidget(list_header)
        
        self.file_list = QListWidget()
        
        for i, video_file in enumerate(self.video_files):
            icon = "🔒 " if video_file.original_path.lower().endswith(".crn") else "🎬 "
            item_text = f"{i+1}. {icon}{video_file.display_name}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.file_list.addItem(item)
        
        self.file_list.itemClicked.connect(self.on_file_selected)
        right_layout.addWidget(self.file_list, 1)
        
        status_label = QLabel(f"Всего файлов: {len(self.video_files)}")
        status_label.setStyleSheet("""
            color: #888;
            font-size: 11px;
            padding: 3px;
        """)
        right_layout.addWidget(status_label)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([700, 300])
        main_layout.addWidget(splitter)

        # Единственная корректная инициализация плеера и подключение сигналов
        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video_widget)
        self.audio.setVolume(0.5)

        self.player.positionChanged.connect(self.on_position_changed)
        self.player.durationChanged.connect(self.on_duration_changed)
        self.player.playbackStateChanged.connect(self.on_playback_state_changed)

    def load_video(self, index):
        if index < 0 or index >= len(self.video_files):
            return
        self.current_index = index
        
        self.file_list.setCurrentRow(index)
        if self.file_list.currentItem():
            self.file_list.scrollToItem(self.file_list.currentItem())
        
        video_file = self.video_files[index]
        
        if video_file.original_path.lower().endswith(".crn") and not video_file.temp_path:
            # если пароль уже известен — не спрашивать
            if video_file.password:
                password = video_file.password
            else:
                password, ok = QInputDialog.getText(
                    self, "Пароль",
                    f"Введите пароль для {video_file.display_name}:",
                    QLineEdit.EchoMode.Password
                )
                if not ok:
                    return
            try:
                data = decrypt_crn(video_file.original_path, password)
                temp_path = create_ram_video(data)
                video_file.temp_path = temp_path
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))
                return
        
        self.player.setSource(QUrl.fromLocalFile(video_file.play_path))
        self.player.play()

    def next_video(self):
        self.load_video((self.current_index + 1) % len(self.video_files))

    def prev_video(self):
        self.load_video((self.current_index - 1) % len(self.video_files))

    def skip(self, seconds):
        self.player.setPosition(self.player.position() + seconds * 1000)

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def set_volume(self, value):
        self.audio.setVolume(value / 100)
        self.volume_label.setText(f"{value}%")

    def slider_pressed(self):
        self.slider_is_pressed = True

    def slider_released(self):
        self.slider_is_pressed = False
        self.player.setPosition(self.position_slider.value())

    def slider_moved(self, value_ms):
        pos_sec = value_ms // 1000
        self.current_time_label.setText(f"{pos_sec // 60:02d}:{pos_sec % 60:02d}")

    def on_duration_changed(self, duration_ms):
        self.position_slider.setRange(0, duration_ms)
        dur_sec = max(0, duration_ms // 1000)
        self.total_time_label.setText(f"{dur_sec // 60:02d}:{dur_sec % 60:02d}")

    def on_position_changed(self, position_ms):
        if not self.slider_is_pressed:
            self.position_slider.setValue(position_ms)
            pos_sec = position_ms // 1000
            self.current_time_label.setText(f"{pos_sec // 60:02d}:{pos_sec % 60:02d}")
    
    def on_file_selected(self, item):
        index = item.data(Qt.ItemDataRole.UserRole)
        if index != self.current_index:
            self.load_video(index)
    
    def on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.video_stack.setCurrentWidget(self.video_widget)
        else:
            self.video_stack.setCurrentWidget(self.black_screen_widget)
    
    def back_to_main_page(self):
        for video_file in self.video_files:
            if video_file.temp_path and os.path.exists(video_file.temp_path):
                try:
                    os.unlink(video_file.temp_path)
                except:
                    pass
        
        self.player.stop()
        self.back_to_main.emit()