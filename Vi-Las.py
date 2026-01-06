import sys
import os
import cv2
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QFrame,
    QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem,
    QSizePolicy, QPushButton, QSlider, QRadioButton, 
    QLineEdit, QButtonGroup, QFileDialog, QStyle
)
from PySide6.QtCore import QSize, Qt, QThread, QObject, Signal, Slot
from PySide6.QtGui import QPixmap, QImage, QDragEnterEvent, QDropEvent, QIcon, QColor

# --- Constants ---
SELECTED_BG_COLOR = QColor("#4CAF50")

# --- Video Processing Worker ---
class VideoProcessor(QObject):
    progress = Signal(dict)
    finished = Signal()
    error = Signal(str)
    def __init__(self, video_path, frame_count_to_get):
        super().__init__()
        self.video_path, self.frame_count_to_get, self.is_running = video_path, frame_count_to_get, True
    @Slot()
    def run(self):
        try:
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened(): raise Exception("無法開啟影片")
            original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            aspect_ratio = original_height / original_width if original_width > 0 else 1.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); start_frame = max(0, total_frames - self.frame_count_to_get)
            for i in range(start_frame, total_frames):
                if not self.is_running: break
                cap.set(cv2.CAP_PROP_POS_FRAMES, i); ret, frame = cap.read()
                if not ret: continue
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB); h, w, ch = frame_rgb.shape
                qt_image = QImage(frame_rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
                self.progress.emit({"image": qt_image.copy(), "frame_num": i + 1, "aspect_ratio": aspect_ratio})
            self.finished.emit()
        except Exception as e: self.error.emit(str(e))
        finally:
            if 'cap' in locals() and cap.isOpened(): cap.release()
    def stop(self): self.is_running = False

# --- Main Application Window ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.setWindowTitle("Vi-Las 1.0"); self.setGeometry(100, 100, 1350, 800); self.setAcceptDrops(True)
        self.setup_ui()
        self.thread, self.worker, self.last_video_path = None, None, None
        self.all_thumbnail_data = []

    def setup_ui(self):
        self.setStyleSheet(f""" QMainWindow, QWidget {{ background-color: #000000; color: #FFFFFF; }} QListWidget {{ border: 1px solid #333; }} QListWidget::item {{ padding: 5px; border-radius: 3px; }} QListWidget::item:selected {{ background-color: {SELECTED_BG_COLOR.name()}; }} QPushButton {{ background-color: #333333; border: 1px solid #555555; padding: 5px; }} QPushButton:hover {{ background-color: #555555; }} QSlider::groove:horizontal {{ height: 8px; background: #333333; }} QSlider::handle:horizontal {{ background: #FFFFFF; border: 1px solid #555555; width: 18px; margin: -2px 0; }} QLineEdit {{ border: 1px solid #555555; background-color: #333333; padding: 5px; }} QRadioButton::indicator {{ width: 13px; height: 13px; border-radius: 7px; }} QRadioButton::indicator:unchecked {{ background-color: #000000; border: 1px solid #FFFFFF; }} QRadioButton::indicator:checked {{ background-color: #FFFFFF; border: 1px solid #000000; }} """)
        central_widget = QWidget(); self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        top_bar_label = QLabel()
        top_bar_label.setTextFormat(Qt.TextFormat.RichText)
        top_bar_label.setOpenExternalLinks(True)
        top_bar_label.setText('<a href="https://linktr.ee/tori.kira" style="color: #FFFFFF; text-decoration: none;">https://linktr.ee/tori.kira</a>')
        top_bar_label.setFixedHeight(25)
        top_bar_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top_bar_label.setStyleSheet("border-bottom: 1px solid #333; padding-right: 12px;")
        main_layout.addWidget(top_bar_label)

        content_panel = QFrame(); main_layout.addWidget(content_panel, 1)
        control_panel = QFrame(); control_panel.setFixedHeight(45); control_panel.setStyleSheet("padding-top: 5px;"); main_layout.addWidget(control_panel)
        content_layout = QHBoxLayout(content_panel); content_layout.setContentsMargins(10, 10, 10, 10)
        self.list_widget = QListWidget(); self.list_widget.setViewMode(QListWidget.ViewMode.IconMode); self.list_widget.setResizeMode(QListWidget.ResizeMode.Adjust); self.list_widget.setMovement(QListWidget.Movement.Static); self.list_widget.setFlow(QListWidget.Flow.LeftToRight); self.list_widget.setWrapping(True);
        self.list_widget.setSpacing(10)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        content_layout.addWidget(self.list_widget, 7)
        self.preview_label = QLabel("拖曳影片檔案至此以開始"); self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter); self.preview_label.setMinimumWidth(500); self.preview_label.setStyleSheet("border-left: 1px solid #333;"); content_layout.addWidget(self.preview_label, 3)
        self.preview_label = QLabel("拖曳影片檔案至此以開始(全域皆可)\n輸出圖檔會以幀數自動命名\n若有問題可從右上連結詢問"); self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter); self.preview_label.setMinimumWidth(500); self.preview_label.setStyleSheet("border-left: 1px solid #333;"); content_layout.addWidget(self.preview_label, 3)
        control_layout = QHBoxLayout(control_panel); control_layout.setContentsMargins(10,0,10,0)
        self.status_label = QLabel("準備就緒"); control_layout.addWidget(self.status_label)
        self.selection_label = QLabel("已選取 0 張"); control_layout.addWidget(self.selection_label)
        control_layout.addStretch(1)
        frame_count_layout = QHBoxLayout(); control_layout.addLayout(frame_count_layout)
        frame_count_layout.addWidget(QLabel("擷取倒數")); self.frame_count_input = QLineEdit("30"); self.frame_count_input.setFixedWidth(40); frame_count_layout.addWidget(self.frame_count_input); frame_count_layout.addWidget(QLabel("幀"))
        self.refresh_btn = QPushButton("刷新"); self.refresh_btn.clicked.connect(self.refresh_frames); frame_count_layout.addWidget(self.refresh_btn)
        self.sort_asc_radio = QRadioButton("順向"); self.sort_desc_radio = QRadioButton("逆向"); self.sort_desc_radio.setChecked(True)
        self.sort_btn_group = QButtonGroup(); self.sort_btn_group.addButton(self.sort_asc_radio, 1); self.sort_btn_group.addButton(self.sort_desc_radio, 2)
        control_layout.addWidget(self.sort_asc_radio); control_layout.addWidget(self.sort_desc_radio)
        self.sort_btn_group.buttonClicked.connect(self.refresh_grid_display)
        control_layout.addWidget(QLabel("每列張數")); self.column_slider = QSlider(Qt.Orientation.Horizontal); self.column_slider.setRange(1, 6); self.column_slider.setValue(2); self.column_slider.setFixedWidth(100); self.column_slider.valueChanged.connect(self.refresh_grid_display); control_layout.addWidget(self.column_slider)
        self.deselect_btn = QPushButton("取消全選"); self.deselect_btn.clicked.connect(self.deselect_all); control_layout.addWidget(self.deselect_btn)
        self.export_btn = QPushButton("儲存選取"); self.export_btn.clicked.connect(self.export_selected); control_layout.addWidget(self.export_btn)
        self.statusBar().hide()

    @Slot(QListWidgetItem)
    def on_item_clicked(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        self.update_preview_image(data["image"])
        self.update_selection_count()

    def update_preview_image(self, image):
        pixmap = QPixmap.fromImage(image).scaled(self.preview_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.preview_label.setPixmap(pixmap)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
    def dropEvent(self, event: QDropEvent):
        if urls := event.mimeData().urls():
            self.last_video_path = urls[0].toLocalFile(); self.process_file(self.last_video_path)
    
    @Slot()
    def refresh_frames(self):
        if self.last_video_path: self.process_file(self.last_video_path)
        else: self.status_label.setText("錯誤: 請先拖曳一個影片檔案")

    def process_file(self, file_path):
        if self.thread and self.thread.isRunning(): self.worker.stop(); self.thread.quit(); self.thread.wait()
        self.list_widget.clear(); self.all_thumbnail_data = []
        self.status_label.setText("處理中..."); self.preview_label.setText("處理中...")
        try: frame_count = int(self.frame_count_input.text())
        except ValueError: self.status_label.setText("錯誤: 幀數必須是數字"); return
        self.thread = QThread(); self.worker = VideoProcessor(file_path, frame_count); self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run); self.worker.finished.connect(self.on_processing_finished); self.worker.error.connect(self.on_processing_error); self.worker.progress.connect(self.add_thumbnail)
        self.thread.start()

    @Slot(dict)
    def add_thumbnail(self, data): self.all_thumbnail_data.append(data)
    @Slot()
    def on_processing_finished(self):
        self.status_label.setText("處理完成"); self.thread.quit(); self.refresh_grid_display()

    @Slot()
    def refresh_grid_display(self, button_or_value=None):
        current_selection = {item.data(Qt.ItemDataRole.UserRole)["frame_num"] for item in self.list_widget.selectedItems()}
        self.list_widget.clear()
        
        is_desc = self.sort_desc_radio.isChecked()
        sorted_data = sorted(self.all_thumbnail_data, key=lambda x: x['frame_num'], reverse=is_desc)
        
        num_columns = self.column_slider.value()
        viewport_width = self.list_widget.viewport().width()
        if viewport_width <= 0: return

        spacing = self.list_widget.spacing()
        
        # Correct calculation: Total width is (N * grid_width) + ((N-1) * spacing).
        # We calculate the grid_width that should fit within the viewport.
        # We subtract 1px as a safety margin to prevent wrapping due to rounding.
        if num_columns > 0:
            grid_width = (viewport_width - (num_columns - 1) * spacing) / num_columns - 1
        else:
            grid_width = 0

        # User request: shrink image to 95% of the cell width
        icon_width = grid_width * 0.95

        avg_aspect_ratio = 1.0
        if self.all_thumbnail_data:
            avg_aspect_ratio = sum(d['aspect_ratio'] for d in self.all_thumbnail_data) / len(self.all_thumbnail_data)
        
        icon_height = int(icon_width * avg_aspect_ratio)

        self.list_widget.setIconSize(QSize(icon_width, icon_height))
        self.list_widget.setGridSize(QSize(grid_width, icon_height + 30))

        for data in sorted_data:
            pixmap = QPixmap.fromImage(data["image"])
            icon = QIcon(pixmap)
            item_text = f"#{data['frame_num']}"
            item = QListWidgetItem(icon, item_text)
            
            item.setData(Qt.ItemDataRole.UserRole, data)
            item.setFlags(item.flags() | Qt.ItemIsSelectable)
            
            if data["frame_num"] in current_selection:
                item.setSelected(True)
            
            self.list_widget.addItem(item)
        self.update_selection_count()

    @Slot()
    def update_selection_count(self):
        count = len(self.list_widget.selectedItems())
        self.selection_label.setText(f"已選取 {count} 張")

    @Slot()
    def deselect_all(self):
        self.list_widget.clearSelection()
    
    @Slot(str)
    def on_processing_error(self, error_msg): self.status_label.setText(f"錯誤: {error_msg}"); self.thread.quit()
    
    def export_selected(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items: self.status_label.setText("錯誤: 未選取任何圖片"); return
        if not (output_dir := QFileDialog.getExistingDirectory(self, "請選擇儲存位置")): return
        count = 0
        try:
            for item in selected_items:
                data = item.data(Qt.ItemDataRole.UserRole)
                data["image"].save(os.path.join(output_dir, f"frame_{data['frame_num']}.jpg"), "JPEG"); count += 1
            self.status_label.setText(f"成功儲存 {count} 張圖片！")
        except Exception as e: self.status_label.setText(f"儲存失敗: {e}")
            
    def closeEvent(self, event):
        if self.thread and self.thread.isRunning(): self.worker.stop(); self.thread.quit(); self.thread.wait()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())