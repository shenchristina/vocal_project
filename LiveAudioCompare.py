import sounddevice as sd
import aubio
import numpy as np
import librosa
import soundfile as sf
import time
import sys
import shlex
import demucs.separate #library used for source seperation
import os

from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QFileDialog
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtCore import Qt


#GET READY 
print("GETTING SET UP!")
print("HOLD TIGHT :)")


class DragDropWindow(QWidget):
    def __init__(self):
        '''initializes drag and drop window (label and button)'''
       
        super().__init__()
        self.setWindowTitle("Drop Window") #set title
        self.setGeometry(500, 500, 500, 500) #set size and position

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
        script_dir = os.getcwd()
        #create command-line arguments for Demcus 
        args = f'--mp3 --two-stems vocals -n mdx_extra -o "{script_dir}"  "{input_file}"'
        
        # Execute Demucs with the constructed arguments
        print("STARTING SOURCE SEPERATION")
        demucs.separate.main(shlex.split(args))

        song_name = os.path.splitext(os.path.basename(input_file))[0]
        demucs_output_dir = os.path.join(script_dir, "mdx_extra", song_name)
        stems = ["vocals.mp3", "no_vocals.mp3"]
        
        for stem in stems:
            src = os.path.join(demucs_output_dir, stem)  # File from Demucs output folder
            dst = os.path.join(script_dir, stem)  # Move it to the script folder
            if os.path.exists(dst):  # Remove old version if it exists
                os.remove(dst)
            os.rename(src, dst)  # Move file

    # Cleanup: Remove the now-empty Demucs output folder
        os.rmdir(demucs_output_dir)
        self.close()

if __name__ == "__main__":
    answer = input("Do you want to sing a new song? (yes/no): ").strip().lower()

    if answer == "yes":
        app = QApplication(sys.argv)
        window = DragDropWindow()
        window.show()
        app.exec()  # Blocks execution until the window is closed


# Load original vocal track and extract pitch
original_audio_path = "vocals.mp3" 
y, sr = librosa.load(original_audio_path, sr=None)  # Load file at native sample rate
hop_size = 512

# Extract pitch from original vocals
f0, voiced_flag, _ = librosa.pyin(y, fmin=50, fmax=600, sr=sr, hop_length=hop_size)
f0 = np.nan_to_num(f0)  #Replace NaN with 0 for unvoiced parts

# Set up microphone input for live vocal processing
device_info = sd.query_devices(kind="input")
samplerate = int(device_info["default_samplerate"])

pitch_detector = aubio.pitch("yin", 1024, hop_size, samplerate)
pitch_detector.set_unit("Hz")
pitch_detector.set_tolerance(0.8)

# Prepare audio playback (backing track)
backing_track_path = "no_vocals.mp3"
backing_track, _ = librosa.load(backing_track_path, sr=samplerate)  # Match mic input sample rate

# Function to convert frequency to note
def frequency_to_note(frequency):
    note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    if frequency <= 0:
        return "N/A"
    midi_note = round(69 + 12 * np.log2(frequency / 440.0))
    note_index = midi_note % 12
    octave = (midi_note // 12) - 1
    return f"{note_names[note_index]}{octave}"

# Function to calculate accuracy
def calculate_accuracy(original_freq, live_freq):
    if original_freq > 0 and live_freq > 0:
        return max(0, 100 - (abs(original_freq - live_freq) / original_freq * 100))
    return 0

# Start processing live audio
def callback(indata, frames, time, status):
    global live_pitch_values, original_pitch_values, current_frame
    if status:
        print(status)

    # Process live mic input
    mono_audio = np.mean(indata, axis=1)
    mono_audio = mono_audio[:hop_size] if len(mono_audio) >= hop_size else np.pad(mono_audio, (0, hop_size - len(mono_audio)))
    live_pitch = pitch_detector(mono_audio)[0]
    confidence = pitch_detector.get_confidence()

    # Get corresponding pitch from original vocals
    if current_frame < len(f0):
        original_pitch = f0[current_frame]
        current_frame += 1
    else:
        original_pitch = 0  # Out of range

    # Only display if confidence is high
    if 50 <= live_pitch <= 600 and confidence > 0.8:
        live_note = frequency_to_note(live_pitch)
        original_note = frequency_to_note(original_pitch)
        accuracy = calculate_accuracy(original_pitch, live_pitch)

        print(f"Original Vocal: {original_pitch:.2f} Hz ({original_note}) | Live Vocal: {live_pitch:.2f} Hz ({live_note}) | Accuracy: {accuracy:.1f}%")

# Wait for Enter key to start
input("Press ENTER to start karaoke ! ! ! ! !")

# Start playback and recording in sync
current_frame = 0  # Frame tracker for original vocals
with sd.InputStream(callback=callback, samplerate=samplerate, channels=1, blocksize=hop_size):
    print("Start singing... (Press Ctrl+C to stop)")
    sd.play(backing_track, samplerate)  # Play backing track

    try:
        while sd.get_stream().active:
            time.sleep(0.01)  # Avoid CPU overload
    except KeyboardInterrupt:
        print("Karaoke session ended.")
