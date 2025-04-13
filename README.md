# VocalHero

## An Interactive Vocal Analysis through Source Separation and Live Pitch Tracking
### By Christina Shen, Isaac Wilson, Greyson Mueller


VoiceHero is an interactive vocal analysis tool designed to enhance singing accuracy through real time audio processing and feedback in a game based format. The system utilizes advanced source separation techniques to isolate vocals from background music and applies pitch detection algorithms to analyze the user’s vocal performance. By separating the audio into distinct components: pitch, frequency, and loudness. The system allows for precise feedback on pitch accuracy, vocal alignment, and vocal dynamics. Players engage with the system by singing along to songs, with their performance continuously compared to the guide track, providing real-time visual and auditory feedback. The combination of sound analysis and gamification aims to create an educational tool for vocal training, enabling users to improve their singing skills in an interactive and engaging way. The project will leverage existing audio processing tools and machine learning models for source separation, pitch detection, and note extraction, with the goal of creating an accessible, fun, and effective learning experience for aspiring singers. 

In this Repo There are multiple files all that show different versions of this code. 

Aubio_note.py: This code shows how the live vocal analysis is done. 

Comparison_algorithm.py: This code is the baseline that we used for comparision between the orginal and live vocals. 

Split.py: This is how we implemented the source seperation in the final code. 

LiveAudioCompare.py + VoiceHero.py: The final product combining everything into one functional code. 

