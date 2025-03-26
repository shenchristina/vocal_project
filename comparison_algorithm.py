import sounddevice as sd
import aubio
import numpy as np


# boring stuff
BUFFER_SIZE = 1024 # samples per buffer
HOP_SIZE = 512 # step size between pitch analysis's(?) smaller means more frequent, may need to optimize this value
DEVICE_INFO = sd.query_devices(kind='input')
SAMPLERATE = int(DEVICE_INFO['default_samplerate'])

ref_pitches = # pre proccesed reference track

scores = [] # keeps track of all scores to give final rating at the end, 1 score per frame
frame_index = 0 # keeps track of where we are in the ref track, to compare against our most recent user input

pitch_detector = aubio.pitch("yin", BUFFER_SIZE, HOP_SIZE, SAMPLERATE)
pitch_detector.set_unit("Hz")
pitch_detector.set_tolerance(0.8) # might need to fiddle with tolerance

note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"] # can either compare notes or freq

# midi notes are better for our purposes 
def hz_to_midi(frequency):
    if frequency <= 0:
        return None
    return 69 + 12 * np.log2(frequency / 440.0)

# spits out note and octave from given frequency
# even if we compare frequences might be most legible for users to get note feedback during gameplay
def frequency_to_note(frequency): 
    if frequency <= 0:
        return "N/A"
    midi_note = round(hz_to_midi(frequency))
    note_index = midi_note % 12
    octave = (midi_note // 12) - 1
    return f"{note_names[note_index]}{octave}"

# compares incoming user pitch to the ref track and outputs current score while also
# keeping track of all scores in the scores array defined globally
def compare_notes(user_pitch, ref_pitch, scores_list, tolerance_semitones=2):
    if user_pitch <= 0 or ref_pitch <= 0: # might change min freq here to avoid noise
        frame_score = 0.0
    else: # if ref pitch is not silent
        user_midi = hz_to_midi(user_pitch)
        ref_midi = hz_to_midi(ref_pitch)
        diff = abs(user_midi - ref_midi)
        # outputs score between 0 and 1
        frame_score = max(0.0, 1.0 - diff / tolerance_semitones) # might need to adjust scoring to make it more balanced/fair

    scores_list.append(frame_score) # for final score
    return frame_score # for feedback during gameplay

# called for every new block of audio coming in
# indata: raw mic audio
# frames: # of audio chunks
# time: not really used, might be helpful for debugging or future optimization 
# status: for errors/debugging
def callback(indata, frames, time, status):
    global frame_index # aligns ref track to user input

    if status:
        print(f"Stream status: {status}") # for errors

    mono_audio = np.mean(indata, axis=1) # collapse audio to mono
    pitch = pitch_detector(mono_audio)[0] # estimate pitch via aubio
    confidence = pitch_detector.get_confidence() # aubio confidence

    if confidence > 0.8 and 50 <= pitch <= 600: # only processes if high confidence and pitch is in human vocal range
        user_note = frequency_to_note(pitch) # freq to note for real time visual feedback (personally think a note is better for realtime feedback
                                             # as its easier to read than a 3 digit number)
        ref_note = frequency_to_note(ref_pitches[frame_index]) if frame_index < len(ref_pitches) else "N/A"
        ref_pitch = ref_pitches[frame_index] if frame_index < len(ref_pitches) else 0 # fetch expected pitch, if song is over returns 0

        score = compare_notes(pitch, ref_pitch, scores) # score for this "frame"/audio chunk
        # this should print out a live stream of whats going on
        print(f"User: {pitch:.1f} Hz ({user_note}) | Ref: {ref_pitch:.1f} Hz ({ref_note}) | Score: {score}/100")

        frame_index += 1 # next frame, ready for next audio chunk

print("Start Singing!\n")
# live input stream
try:
    # callback gets called (or should) everytime the microphone stream gets updated
    with sd.InputStream(callback=callback, samplerate=SAMPLERATE, channels=1, blocksize=HOP_SIZE):
        while True:
            pass # aslong as mic is running so will our program
except KeyboardInterrupt: # prints final scores upon completion
    final_score = round(np.mean(scores) * 100, 2) if scores else 0
    print(f"Final Score: {final_score}/100")
