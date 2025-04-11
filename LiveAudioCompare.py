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
import whisper 
import pyfiglet 
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QFileDialog
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtCore import Qt

# GLOBAL SETUP 
print("GETTING SET UP!")
print("HOLD TIGHT :)")
hop_size = 512
loudness_threshold = 7.0e-5  # Used to filter out silence

# UTILITY FUNCTIONS 
def frequency_to_note(frequency):
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        if frequency <= 0:
            return "N/A"
        midi_note = round(69 + 12 * np.log2(frequency / 440.0))
        note_index = midi_note % 12
        octave = (midi_note // 12) - 1
        return f"{note_names[note_index]}{octave}"

def calculate_accuracy(original_freq, live_freq):
    if original_freq > 0 and live_freq > 0:
        return max(0, 100 - (abs(original_freq - live_freq) / original_freq * 100))
    return 0

def print_text(text, accuracy):

    if accuracy != -1: 
        if accuracy > 90.0: 
            feedback = "Excellent!!!"
            large_text = pyfiglet.figlet_format(f"{str(int(accuracy))}%")
            print(f"\033[30;32m{large_text} \n {feedback} \033[0m") 
        elif accuracy > 75.0 and accuracy < 90.0:
            feedback = "good job"
            large_text = pyfiglet.figlet_format(f"{str(int(accuracy))}%")
            print(f"\033[30;33m{large_text} \n {feedback} \033[0m") 
        elif accuracy > 50 and accuracy < 75.0:
            feedback = "not very good :/"
            large_text = pyfiglet.figlet_format(f"{str(int(accuracy))}%")
            print(f"\033[30;35m{large_text} \n {feedback} \033[0m") 
        else: 
            feedback = "You Suck!"
            large_text = pyfiglet.figlet_format(f"{str(int(accuracy))}%")
            print(f"\033[30;31m{large_text} \n {feedback} \033[0m") 

        print(f"\033[1;37;90m{text}\033[0m")


#CLASS -- SOURCE SEPERATION 
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

#WHISPER--LYRIC GENERATION 
def generate_lyrics_with_whisper(vocal_path="vocals.mp3"):
        print("Transcribing vocals with Whisper... this may take a moment.")

        model = whisper.load_model("base")  # You can use "small", "medium", or "large" for better accuracy
        result = model.transcribe(vocal_path)
        lyrics = result["segments"]  # List of dicts: start, end, text

        return lyrics

#AUDIO PROCESSING
def start_audio_processing(f0, rms_values, lyrics, samplerate, backing_track):
    current_frame = 0
    current_lyric_index = 0
    text_2 = ""
    pitch_detector = aubio.pitch("yin", 1024, hop_size, samplerate)
    pitch_detector.set_unit("Hz")
    pitch_detector.set_tolerance(0.8)
    accuracy_list =[]
    prev_accuracy = 0.0

    def callback(indata, frames, time, status):
        nonlocal current_frame, current_lyric_index,text_2, accuracy_list, prev_accuracy
        
        if status: print(status)

        # Process live mic input
        mono_audio = np.mean(indata, axis=1)
        mono_audio = mono_audio[:hop_size] if len(mono_audio) >= hop_size else np.pad(mono_audio, (0, hop_size - len(mono_audio)))
        live_pitch = pitch_detector(mono_audio)[0]
        confidence = pitch_detector.get_confidence()

        # Get corresponding pitch from original vocals
        original_pitch = f0[current_frame] if current_frame < len(f0) else 0
        original_loudness = rms_values[current_frame] if current_frame < len(rms_values) else 0
        current_time = current_frame * hop_size / samplerate
        current_frame += 1

        text = ""
        if current_lyric_index < len(lyrics):
            start = lyrics[current_lyric_index]['start']
            end = lyrics[current_lyric_index]['end']
            text = lyrics[current_lyric_index]['text']     
            if current_time > end:
                    current_lyric_index += 1

        # Only display if confidence is high
        if 50 <= live_pitch <= 600 and confidence > 0.8:
            live_note = frequency_to_note(live_pitch)
            original_note = frequency_to_note(original_pitch)
            accuracy = calculate_accuracy(original_pitch, live_pitch)
            
            if accuracy != prev_accuracy:
                accuracy_list.append(accuracy)
                prev_accuracy = accuracy

            print_text(text,accuracy)       
        else:
            if text != text_2:
                accuracy =-1
                print_text(text,accuracy)
                text_2 = text 

    with sd.InputStream(callback=lambda indata, frames, time_info, status:
                    callback(indata, frames, time_info, status),
                    samplerate=samplerate, channels=1, blocksize=hop_size):
        sd.play(backing_track, samplerate)
        try:
            while sd.get_stream().active:
                time.sleep(0.01)
        except KeyboardInterrupt:
            average = sum(accuracy_list) / len(accuracy_list)
            end_game = pyfiglet.figlet_format(f"GAME   ENDED")
            game_acr = pyfiglet.figlet_format(f"Your Accuracy was:") 
            avg_txt = pyfiglet.figlet_format(f"{int(average)}%") 
            print(end_game)
            print(game_acr)
            print(avg_txt)
    
#MAIN FLOW 

if __name__ == "__main__":
    app = QApplication(sys.argv)
    answer = input("Do you want to sing a new song? (yes/no): ").strip().lower()

    if answer == "yes":
        window = DragDropWindow()
        window.show()
        app.exec()  # Blocks execution until the window is closed
    else:
        # Check if both files exist
        if not os.path.exists("vocals.mp3") or not os.path.exists("no_vocals.mp3"):
            input("No previous song found. Press ENTER to add a song.")
            window = DragDropWindow()
            window.show()
            app.exec()

    print(" LOADING YOUR SONG ")
    y, sr = librosa.load("vocals.mp3" , sr=None)  # Load file at native sample rate
    backing, _ = librosa.load("no_vocals.mp3", sr=None)  # Load file at native sample rate
    f0 = librosa.yin(y, fmin=50, fmax=600, sr=sr, hop_length=hop_size) # Extract pitch from original vocals
    f0 = np.nan_to_num(f0)  # Replace NaN with 0 for unvoiced parts
    rms = librosa.feature.rms(y=y, frame_length=hop_size)[0]

    # Set up microphone input for live vocal processing
    device_info = sd.query_devices(kind="input")
    samplerate = int(device_info["default_samplerate"])
    pitch_detector = aubio.pitch("yin", 1024, hop_size, samplerate)
    pitch_detector.set_unit("Hz")
    pitch_detector.set_tolerance(0.8)

    lyrics = generate_lyrics_with_whisper("vocals.mp3")
    
    
    input("Press ENTER to start karaoke ! ! ! ! !")
    