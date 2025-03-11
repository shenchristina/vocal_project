
import sys
import shlex
import demucs.separate #library used for source seperation

# #cite for source spereation tool (demucs) Demucs
# #Défossez, A. (2021). Hybrid Spectrogram and Waveform Source Separation [Computer software]. Retrieved from https://github.com/facebookresearch/demucs

from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QFileDialog
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtCore import Qt

#cite for pyqt6
#Riverbank Computing. (2021). PyQt6: Python bindings for Qt 6. Retrieved from https://riverbankcomputing.com/software/pyqt/intro


class DragDropWindow(QWidget):
    def __init__(self):
        '''initializes drag and drop window (label and button)'''
       
        super().__init__()
        self.setWindowTitle("Drop Window") #set title
        self.setGeometry(100, 100, 400, 200) #set size and position

        #instert prompt for user 
        self.label = QLabel("Drag and drop the song you want to sing!", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter) #align text

        #manually browse button 
        self.button = QPushButton("Browse Files", self)
        self.button.clicked.connect(self.browse_file)

        layout = QVBoxLayout() #vertical layout
        layout.addWidget(self.label) #label for layout 
        layout.addWidget(self.button) # add button
        self.setLayout(layout) #set layout 

        # Enable drag-and-drop
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        '''Handles when file is dragged to the window'''
        if event.mimeData().hasUrls(): # check for file URL 
            event.acceptProposedAction() # accept file if it has file URL

    def dropEvent(self, event: QDropEvent):
        """Handles file drop event"""
        files = [url.toLocalFile() for url in event.mimeData().urls()] #get the local file path
        if files:
            file_path = files[0]  # Get the first dropped file (assuming single file is given)
            self.label.setText(f"File Selected: {file_path}") # label with new path
            self.separate_audio(file_path) #process the file with source seperation 

    def browse_file(self):
        """Opens file dialog for selecting an audio file"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Audio File", "", "Audio Files (*.wav *.mp3 *.flac)")
        if file_path:
            self.label.setText(f"File Selected: {file_path}")
            self.separate_audio(file_path)

    def separate_audio(self, input_file):
        """Runs Demucs to separate vocals"""
        
        #create command-line arguments for Demcus 
        args = f'--mp3 --two-stems vocals -n mdx_extra "{input_file}"'
        
        # Execute Demucs with the constructed arguments 
        demucs.separate.main(shlex.split(args))

        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DragDropWindow()
    window.show()
    sys.exit(app.exec())



#pip install PyQt6
#brew install sound-touch 
#python3 -m pip install -U demucs
#brew install ffmpeg  


