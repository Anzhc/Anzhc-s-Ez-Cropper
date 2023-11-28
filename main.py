from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QFileDialog, 
                              QLineEdit, QGridLayout, QScrollArea)
from PySide6.QtGui import QPixmap, QImage, QImageReader, QPainter, QPen
from PySide6.QtCore import Qt, QEvent, QRect
from PIL import Image
import os

class ImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.last_mouse_pos = None
        self.resolutions = [512, 640, 768]  # Default values
        self.aspect_ratios = [(1, 1), (2, 3), (3, 2)]  # Default values
        self.setMouseTracking(True)  # Enable mouse tracking

    def mouseMoveEvent(self, event):
        self.last_mouse_pos = event.pos()
        self.update()  # Trigger a repaint

    def update_mouse_pos(self, pos, resolutions, aspect_ratios):
        self.last_mouse_pos = pos
        self.resolutions = resolutions
        self.aspect_ratios = aspect_ratios
        self.update()  # Request a repaint to update the crop area rectangles


    def paintEvent(self, event):
        super().paintEvent(event)  # Call the base class paint event to ensure the image is drawn
        if self.last_mouse_pos:
            painter = QPainter(self)
            
            # Set the pen color and width
            pen = QPen(Qt.red)  # Set color to red
            pen.setWidth(2)  # Set width to 2 pixels
            painter.setPen(pen)
            
            for resolution in self.resolutions:
                for ratio in self.aspect_ratios:
                    width_ratio, height_ratio = ratio
                    if width_ratio < height_ratio:
                        crop_width = resolution
                        crop_height = int(resolution * (height_ratio / width_ratio))
                    else:
                        crop_height = resolution
                        crop_width = int(resolution * (width_ratio / height_ratio))
                    
                    left = self.last_mouse_pos.x() - crop_width // 2
                    top = self.last_mouse_pos.y() - crop_height // 2
                    
                    rect = QRect(left, top, crop_width, crop_height)
                    painter.drawRect(rect)

            painter.end()

    def update_crop_settings(self, resolutions, aspect_ratios):
        self.resolutions = resolutions
        self.aspect_ratios = aspect_ratios

class ImageCropper(QWidget):
    def __init__(self):
        super().__init__()
        self.last_mouse_pos = None
        self.image_label = ImageLabel(self)
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setWidgetResizable(True)
        self.image_label.installEventFilter(self)  # Move this line here
        self.init_ui()

    def init_ui(self):
        self.load_folder_btn = QPushButton('Load Folder', self)
        self.load_folder_btn.clicked.connect(self.load_folder)

        self.skip_image_btn = QPushButton('Skip Image', self)
        self.skip_image_btn.clicked.connect(self.skip_image)

        self.resolution_input = QLineEdit("512,640,768", self)
        self.aspect_ratio_input = QLineEdit("1:1,2:3,3:2", self)

        layout = QGridLayout()
        layout.addWidget(self.load_folder_btn, 0, 0)
        layout.addWidget(self.scroll_area, 1, 0)
        layout.addWidget(self.skip_image_btn, 2, 0)
        layout.addWidget(self.resolution_input, 0, 1)
        layout.addWidget(self.aspect_ratio_input, 1, 1)
        self.setLayout(layout)

        self.apply_stylesheet()
        self.setWindowTitle('Image Cropper')
        self.show()

    def load_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, 'Select Image Folder')
        if folder_path:
            self.images = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            self.image_index = 0
            self.load_image(folder_path)

    def load_image(self, folder_path):
        self.current_image_path = os.path.join(folder_path, self.images[self.image_index])
        pixmap = QPixmap(self.current_image_path)
        self.image_label.setPixmap(pixmap)
        self.image_label.setFixedSize(pixmap.size())

    def skip_image(self):
        self.image_index += 1
        if self.image_index < len(self.images):
            folder_path = os.path.dirname(self.current_image_path)
            self.load_image(folder_path)
        else:
            self.image_label.clear()

    def eventFilter(self, source, event):
        if source is self.image_label:
            if event.type() == QEvent.MouseMove:
                resolutions = [int(res) for res in self.resolution_input.text().split(',')]
                aspect_ratios = [tuple(map(int, ratio.split(':'))) for ratio in self.aspect_ratio_input.text().split(',')]
                self.image_label.update_crop_settings(resolutions, aspect_ratios)
            elif event.type() == QEvent.MouseButtonPress:
                self.crop_image(event.pos())
                return True
        return super().eventFilter(source, event)

    def crop_image(self, pos):
        folder_path = os.path.dirname(self.current_image_path)
        crop_folder = os.path.join(folder_path, 'crops')
        os.makedirs(crop_folder, exist_ok=True)

        image = Image.open(self.current_image_path)

        resolutions = [int(res) for res in self.resolution_input.text().split(',')]  # Convert resolution inputs to integers
        aspect_ratios = [tuple(map(int, ratio.split(':'))) for ratio in self.aspect_ratio_input.text().split(',')]  # Parse aspect ratios

        for resolution in resolutions:
            resolution_folder = os.path.join(crop_folder, f"{resolution}px")
            os.makedirs(resolution_folder, exist_ok=True)  # Create resolution-specific sub-folder

            for ratio in aspect_ratios:
                width_ratio, height_ratio = ratio
                # Determine the smaller dimension based on the aspect ratio
                if width_ratio < height_ratio:
                    crop_width = resolution
                    crop_height = int(resolution * (height_ratio / width_ratio))
                else:
                    crop_height = resolution
                    crop_width = int(resolution * (width_ratio / height_ratio))

                # Ensure the crop dimensions do not exceed the image boundaries
                left = max(pos.x() - crop_width // 2, 0)
                top = max(pos.y() - crop_height // 2, 0)
                right = min(pos.x() + crop_width // 2, image.width)
                bottom = min(pos.y() + crop_height // 2, image.height)

                # Perform the cropping
                cropped_image = image.crop((left, top, right, bottom))

                # Save the cropped image
                crop_name = f"{os.path.basename(self.current_image_path).split('.')[0]}_crop_{crop_width}x{crop_height}.png"
                crop_path = os.path.join(resolution_folder, crop_name)  # Save to the resolution-specific sub-folder
                crop_counter = 1
                while os.path.exists(crop_path):
                    crop_name = f"{os.path.basename(self.current_image_path).split('.')[0]}_crop_{crop_width}x{crop_height}_{crop_counter}.png"
                    crop_path = os.path.join(resolution_folder, crop_name)  # Save to the resolution-specific sub-folder
                    crop_counter += 1

                cropped_image.save(crop_path)

    def apply_stylesheet(self):
        with open("style.css", "r") as f:
            stylesheet = f.read()
        self.setStyleSheet(stylesheet)

if __name__ == '__main__':
    app = QApplication([])
    ex = ImageCropper()
    app.exec()
