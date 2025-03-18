import sounddevice as sd
import aubio
import numpy as np

# MACOS COMPATIBILITY
device_info = sd.query_devices(kind='input')
samplerate = int(device_info['default_samplerate'])
buffer_size = 1024  # Smaller buffer for faster response (reduce latency)
hop_size = 512  # More frequent updates (smaller hop size)

# Initialize aubio pitch detector with YIN
pitch_detector = aubio.pitch("yin", buffer_size, hop_size, samplerate)
pitch_detector.set_unit("Hz")
pitch_detector.set_tolerance(0.8)

# MIDI note to name mapping
note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

def frequency_to_note(frequency):
    """Convert frequency (Hz) to the closest musical note"""
    if frequency <= 0:
        return "N/A"
    midi_note = round(69 + 12 * np.log2(frequency / 440.0))
    note_index = midi_note % 12  # note name
    octave = (midi_note // 12) - 1 
    return f"{note_names[note_index]}{octave}" 


# Process live audio and detect pitch
def callback(indata, frames, time, status):
    if status:
        print(status)

    mono_audio = np.mean(indata, axis=1)

    if len(mono_audio) >= hop_size:
        mono_audio = mono_audio[:hop_size] 
    else:
        mono_audio = np.pad(mono_audio, (0, hop_size - len(mono_audio))) 

    pitch = pitch_detector(mono_audio)[0] 
    confidence = pitch_detector.get_confidence()

    if 50 <= pitch <= 600 and confidence > 0.8:  # Human singing range (can be adjusted during trials)
        note = frequency_to_note(pitch)
        print(f"Detected Frequency: {pitch:.2f} Hz | Note: {note}")

# Start recording with improved settings for faster processing
with sd.InputStream(callback=callback, samplerate=samplerate, channels=1, blocksize=hop_size):
    print("Start Singing... Ctrl+C to stop.")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("Finished")
