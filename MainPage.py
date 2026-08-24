import os
import sys
import json
import zipfile
import shutil
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QInputDialog, QListWidget, QListWidgetItem,
    QMessageBox, QFrame, QGridLayout, QDialog, QLineEdit,
    QTableWidget, QTableWidgetItem, QCheckBox, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal

# Директории пользователя
USER_DATA_DIR = Path.home() / ".cornvideoplayer"
DATA_FILE = USER_DATA_DIR / "settings" / "playlists_data.json"
PLAYLISTS_DIR = USER_DATA_DIR / "playlists"

class CreatePlaylistDialog(QDialog):
    """Диалог создания плейлиста с возможностью ввода путей, паролей и экспорта в ZIP"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создание плейлиста")
        self.resize(650, 480)
        self.playlist_saved_data = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Название плейлиста
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Название плейлиста:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Мой плейлист")
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # Панель добавления пути
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Впишите полный путь к файлу...")
        self.btn_add_path = QPushButton("➕ Добавить путь")
        self.btn_add_path.clicked.connect(self.add_path_from_edit)
        self.btn_browse = QPushButton("📁 Обзор...")
        self.btn_browse.clicked.connect(self.browse_files)

        path_layout.addWidget(self.path_edit, 1)
        path_layout.addWidget(self.btn_add_path)
        path_layout.addWidget(self.btn_browse)
        layout.addLayout(path_layout)

        # Таблица записей
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Путь к файлу", "Пароль (опционально)"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(1, 180)
        layout.addWidget(self.table)

        # Кнопка удаления элемента
        btn_remove = QPushButton("🗑 Удалить выбранный файл")
        btn_remove.clicked.connect(self.remove_selected)
        layout.addWidget(btn_remove)

        # Опции экспорта
        export_group = QHBoxLayout()
        self.chk_include_passwords = QCheckBox("Сохранять пароли в ZIP при экспорте")
        self.chk_include_passwords.setChecked(True)
        self.btn_export_zip = QPushButton("📦 Экспортировать в ZIP")
        self.btn_export_zip.clicked.connect(self.export_to_zip)

        export_group.addWidget(self.chk_include_passwords)
        export_group.addStretch()
        export_group.addWidget(self.btn_export_zip)
        layout.addLayout(export_group)

        # Кнопки сохранения/отмены
        bottom_buttons = QHBoxLayout()
        self.btn_save = QPushButton("💾 Сохранить в память")
        self.btn_save.setProperty("class", "filled-accent-button")
        self.btn_save.clicked.connect(self.save_playlist)
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)

        bottom_buttons.addStretch()
        bottom_buttons.addWidget(self.btn_cancel)
        bottom_buttons.addWidget(self.btn_save)
        layout.addLayout(bottom_buttons)

    def add_path_from_edit(self):
        path = self.path_edit.text().strip()
        if path:
            self.add_entry_to_table(path)
            self.path_edit.clear()

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Выберите видеофайлы", "", "Видео (*.crn *.mp4 *.avi *.mkv)"
        )
        for f in files:
            self.add_entry_to_table(f)

    def add_entry_to_table(self, file_path):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(file_path))
        self.table.setItem(row, 1, QTableWidgetItem(""))

    def remove_selected(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)

    def get_entries(self):
        entries = []
        for row in range(self.table.rowCount()):
            path_item = self.table.item(row, 0)
            pass_item = self.table.item(row, 1)
            path = path_item.text().strip() if path_item else ""
            pwd = pass_item.text().strip() if pass_item else ""
            if path:
                entries.append({"path": path, "password": pwd})
        return entries

    def export_to_zip(self):
        playlist_name = self.name_edit.text().strip() or "playlist"
        entries = self.get_entries()

        if not entries:
            QMessageBox.warning(self, "Внимание", "Добавьте хотя бы один файл!")
            return

        zip_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить ZIP архив", f"{playlist_name}.zip", "ZIP Archives (*.zip)"
        )
        if not zip_path:
            return

        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                manifest_files = []

                for item in entries:
                    src_path = item["path"]
                    if os.path.exists(src_path):
                        arc_name = os.path.basename(src_path)
                        zip_file.write(src_path, arcname=arc_name)

                        entry_data = {"filename": arc_name}
                        if self.chk_include_passwords.isChecked() and item["password"]:
                            entry_data["password"] = item["password"]

                        manifest_files.append(entry_data)

                manifest = {
                    "name": playlist_name,
                    "files": manifest_files
                }
                zip_file.writestr("playlist.json", json.dumps(manifest, ensure_ascii=False, indent=2))

            QMessageBox.information(self, "Успех", f"Плейлист экспортирован в:\n{zip_path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать ZIP: {str(e)}")

    def save_playlist(self):
        if self.path_edit.text().strip():
            self.add_path_from_edit()

        name = self.name_edit.text().strip()
        entries = self.get_entries()

        if not name:
            QMessageBox.warning(self, "Ошибка", "Укажите название плейлиста!")
            return
        if not entries:
            QMessageBox.warning(self, "Ошибка", "Добавьте хотя бы один файл в таблицу!")
            return

        self.playlist_saved_data = {
            "name": name,
            "entries": entries
        }
        self.accept()


class MainPage(QWidget):
    play_file_selected = pyqtSignal(str)
    play_folder_selected = pyqtSignal(list)
    playlist_selected = pyqtSignal(str)
    theme_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("mainPage")
        self.setAcceptDrops(True)
        self.init_ui()
        self.load_playlists()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        files = []
        for url in urls:
            path = url.toLocalFile()
            if os.path.isfile(path) and path.lower().endswith((".crn", ".mp4", ".avi", ".mkv")):
                files.append(path)
        if files:
            self.status_label.setText(f"Добавлено {len(files)} файлов через drag & drop")
            if len(files) == 1:
                self.play_file_selected.emit(files[0])
            else:
                self.play_folder_selected.emit(files)

    def open_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Выберите видеофайл", "", "Видео (*.crn *.mp4 *.avi *.mkv)"
        )
        if file:
            self.status_label.setText(f"Выбран файл: {os.path.basename(file)}")
            self.play_file_selected.emit(file)

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку с видео", "")
        if folder:
            files = []
            for f in sorted(os.listdir(folder)):
                full_path = os.path.join(folder, f)
                if os.path.isfile(full_path) and f.lower().endswith((".crn", ".mp4", ".avi", ".mkv")):
                    files.append(full_path)
            if files:
                self.status_label.setText(f"Выбрана папка: {os.path.basename(folder)} ({len(files)} файлов)")
                self.play_folder_selected.emit(files)

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        title = QLabel("🌽 CORN SECURE PLAYER")
        title.setObjectName("mainTitleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Защищенный видеоплеер с шифрованием")
        subtitle.setObjectName("subtitleLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        btn_layout = QGridLayout()
        btn_layout.setSpacing(10)

        self.btn_open_file = QPushButton("📁 Выбрать видеофайл")
        self.btn_open_file.setProperty("class", "accent-button")
        self.btn_open_file.clicked.connect(self.open_file)
        self.btn_open_file.setFixedHeight(35)
        btn_layout.addWidget(self.btn_open_file, 0, 0)

        self.btn_open_folder = QPushButton("📂 Воспроизвести папку")
        self.btn_open_folder.setProperty("class", "accent-button")
        self.btn_open_folder.clicked.connect(self.open_folder)
        self.btn_open_folder.setFixedHeight(35)
        btn_layout.addWidget(self.btn_open_folder, 0, 1)

        self.btn_create_playlist = QPushButton("🎵 Создать новый плейлист")
        self.btn_create_playlist.setProperty("class", "accent-button")
        self.btn_create_playlist.clicked.connect(self.create_playlist)
        self.btn_create_playlist.setFixedHeight(35)
        btn_layout.addWidget(self.btn_create_playlist, 1, 0)

        self.btn_import_playlist = QPushButton("📋 Импортировать плейлист")
        self.btn_import_playlist.setProperty("class", "accent-button")
        self.btn_import_playlist.clicked.connect(self.import_playlist)
        self.btn_import_playlist.setFixedHeight(35)
        btn_layout.addWidget(self.btn_import_playlist, 1, 1)

        self.btn_change_theme = QPushButton("🎨 Сменить тему")
        self.btn_change_theme.setProperty("class", "accent-button")
        self.btn_change_theme.clicked.connect(self.change_theme)
        self.btn_change_theme.setFixedHeight(35)
        btn_layout.addWidget(self.btn_change_theme, 2, 0)

        self.btn_about = QPushButton("ℹ️ О программе")
        self.btn_about.setProperty("class", "accent-button")
        self.btn_about.clicked.connect(self.show_about)
        self.btn_about.setFixedHeight(35)
        btn_layout.addWidget(self.btn_about, 2, 1)

        # Кнопка полной очистки данных
        self.btn_wipe_data = QPushButton("💥 Сброс всех данных")
        self.btn_wipe_data.setProperty("class", "accent-button")
        self.btn_wipe_data.clicked.connect(self.wipe_all_data)
        self.btn_wipe_data.setFixedHeight(35)
        btn_layout.addWidget(self.btn_wipe_data, 3, 0, 1, 2)

        layout.addLayout(btn_layout)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #333; margin: 15px 0; height: 1px;")
        layout.addWidget(separator)

        playlist_label = QLabel("🎵 Ваши плейлисты (во внутренней памяти):")
        playlist_label.setObjectName("playlistLabel")
        layout.addWidget(playlist_label)

        self.playlist_list = QListWidget()
        self.playlist_list.setObjectName("playlistList")
        self.playlist_list.itemDoubleClicked.connect(self.open_playlist)
        self.playlist_list.setMaximumHeight(180)
        layout.addWidget(self.playlist_list, 1)

        playlist_btn_layout = QHBoxLayout()
        playlist_btn_layout.setSpacing(8)

        self.btn_delete_playlist = QPushButton("🗑️ Удалить плейлист")
        self.btn_delete_playlist.clicked.connect(self.delete_playlist)
        self.btn_delete_playlist.setFixedHeight(30)
        self.btn_delete_playlist.setProperty("class", "accent-button")
        playlist_btn_layout.addWidget(self.btn_delete_playlist)

        self.btn_export_playlist = QPushButton("📤 Экспортировать в JSON")
        self.btn_export_playlist.clicked.connect(self.export_playlist)
        self.btn_export_playlist.setFixedHeight(30)
        self.btn_export_playlist.setProperty("class", "accent-button")
        playlist_btn_layout.addWidget(self.btn_export_playlist)

        layout.addLayout(playlist_btn_layout)

        self.status_label = QLabel("Готов к работе")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        layout.addStretch(1)
        self.setLayout(layout)

    # --- Внутренняя память для плейлистов ---
    def read_internal_db(self):
        if DATA_FILE.exists():
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Ошибка чтения БД: {e}")
                return {}
        return {}

    def write_internal_db(self, data):
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_playlists(self):
        self.playlist_list.clear()
        db = self.read_internal_db()
        for name in sorted(db.keys()):
            self.playlist_list.addItem(QListWidgetItem(name))

    def create_playlist(self):
        dlg = CreatePlaylistDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.playlist_saved_data:
            p_data = dlg.playlist_saved_data
            db = self.read_internal_db()
            db[p_data["name"]] = [
                {"path": e["path"], "password": e["password"]}
                for e in p_data["entries"]
            ]
            self.write_internal_db(db)
            self.load_playlists()
            self.status_label.setText(f"Сохранен плейлист: {p_data['name']}")
            
    def import_playlist(self):
        zip_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите ZIP-архив плейлиста", "", "ZIP Архивы (*.zip)"
        )
        if not zip_path:
            return

        try:
            playlist_name = os.path.splitext(os.path.basename(zip_path))[0]
            extract_dir = PLAYLISTS_DIR / playlist_name
            extract_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                zip_ref.extractall(extract_dir)

                passwords = {}
                if "playlist.json" in file_list:
                    with zip_ref.open("playlist.json") as f:
                        manifest = json.load(f)
                        for entry in manifest.get("files", []):
                            fname = entry.get("filename", "")
                            pwd = entry.get("password", "")
                            if fname and pwd:
                                passwords[fname] = pwd

                media_extensions = ('.crn', '.mp4', '.avi', '.mkv', '.mov', '.mp3', '.wav')
                extracted_entries = []
                for f in file_list:
                    if f.lower().endswith(media_extensions):
                        full_path = str((extract_dir / os.path.basename(f)).resolve())
                        fname = os.path.basename(f)
                        entry = {"path": full_path, "password": passwords.get(fname, "")}
                        extracted_entries.append(entry)

                if not extracted_entries:
                    QMessageBox.warning(self, "Ошибка", "В архиве не найдено подходящих медиафайлов!")
                    return

                playlist_data = {playlist_name: extracted_entries}

            current_db = self.read_internal_db()
            current_db.update(playlist_data)
            self.write_internal_db(current_db)

            self.load_playlists()
            self.status_label.setText(f"Импортирован плейлист: {playlist_name}")
            QMessageBox.information(self, "Успех", f"Плейлист «{playlist_name}» импортирован!")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось извлечь архив:\n{str(e)}")

    def export_playlist(self):
        current_item = self.playlist_list.currentItem()
        if current_item:
            playlist_name = current_item.text()
            db = self.read_internal_db()
            files = db.get(playlist_name, [])

            file, _ = QFileDialog.getSaveFileName(
                self, "Экспортировать плейлист", f"{playlist_name}.json", "JSON Files (*.json)"
            )
            if file:
                try:
                    export_data = {"name": playlist_name, "files": files}
                    with open(file, 'w', encoding='utf-8') as f:
                        json.dump(export_data, f, ensure_ascii=False, indent=2)
                    self.status_label.setText(f"Плейлист экспортирован в: {os.path.basename(file)}")
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта: {str(e)}")

    def open_playlist(self, item):
        if item:
            self.status_label.setText(f"Открывается плейлист: {item.text()}")
            self.playlist_selected.emit(item.text())
            print(f"open_playlist вызван: {item.text()}")

    def delete_playlist(self):
        current_item = self.playlist_list.currentItem()
        if current_item:
            playlist_name = current_item.text()
            reply = QMessageBox.question(
                self, "Подтверждение", f"Удалить плейлист '{playlist_name}' из памяти?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                db = self.read_internal_db()
                if playlist_name in db:
                    del db[playlist_name]
                    self.write_internal_db(db)
                    self.load_playlists()
                    self.status_label.setText(f"Удален плейлист: {playlist_name}")

    def wipe_all_data(self):
        """Полная очистка всей пользовательской папки (настройки, темы, плейлисты)"""
        reply = QMessageBox.warning(
            self,
            "Подтверждение сброса",
            "Вы действительно хотите полностью удалить все данные (плейлисты, настройки, темы и импортированные файлы)?\nЭто действие нельзя отменить!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if USER_DATA_DIR.exists():
                    shutil.rmtree(USER_DATA_DIR)
                USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
                
                # Сброс темы до темы по умолчанию
                self.on_theme_changed("orange")
                self.load_playlists()
                self.status_label.setText("Все данные успешно удалены")
                QMessageBox.information(self, "Успех", "Все пользовательские данные успешно удалены!")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить данные:\n{str(e)}")

    def change_theme(self):
        from ThemeManager import ThemeManager, ThemeDialog
        current_theme = ThemeManager.get_current_theme()
        dialog = ThemeDialog(current_theme)
        dialog.theme_selected.connect(self.on_theme_changed)
        dialog.exec()

    def on_theme_changed(self, theme_name):
        from ThemeManager import ThemeManager
        ThemeManager.save_theme(theme_name)
        self.theme_changed.emit(theme_name)

    def show_about(self):
        about_text = """
        <h2>CORN SECURE PLAYER</h2>
        <p>Защищенный видеоплеер с шифрованием</p>
        <p>Версия: 1.1.0</p>
        """
        msg = QMessageBox()
        msg.setWindowTitle("О программе")
        msg.setText(about_text)
        msg.exec()