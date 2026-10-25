# only use if you dont have a openwakeword and want to startup with a finger snap instead

import pyaudio
import numpy as np
import time

# --- AUDIO HARDWARE SETTINGS ---
CHUNK = 1024               # How many audio samples to grab at once (Lower = faster, Higher = less CPU)
FORMAT = pyaudio.paInt16   # 16-bit audio
CHANNELS = 1               # Mono microphone
RATE = 44100               # Standard audio sample rate (CD quality)

# --- THE SNAP ALGORITHM SETTINGS ---
TARGET_FREQ_MIN = 15000
TARGET_FREQ_MAX = 20000
# ⚠️ YOU WILL NEED TO TUNE THIS NUMBER:
# Run the script, snap your fingers, and look at the volume printed in the terminal.
VOLUME_THRESHOLD = 20000.0  

# --- THE STATE MACHINE TIMING ---
MAX_TIME_WINDOW = 0.8  # You have 1 second to do the second snap
MIN_TIME_WINDOW = 0.2  # Ignore echoes or sounds closer than 200ms

# Initialize the Audio Stream
p = pyaudio.PyAudio()
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

def is_snap(audio_data_np):
    """The Math Engine: Returns True if a snap is detected in the frequency band."""
    # 1. Run the Fast Fourier Transform
    frequencies = np.fft.rfftfreq(len(audio_data_np), 1.0 / RATE)
    magnitudes = np.abs(np.fft.rfft(audio_data_np))
    
    # 2. Mask out everything except our target high-pitch frequencies
    bandpass_mask = (frequencies >= TARGET_FREQ_MIN) & (frequencies <= TARGET_FREQ_MAX)
    
    # 3. Calculate average volume of just those frequencies
    target_volume = np.mean(magnitudes[bandpass_mask])
    
    # Return both the boolean result and the raw volume (helpful for tuning!)
    if target_volume > VOLUME_THRESHOLD:
        return True, target_volume
    return False, target_volume

print("🎙️ Microphone Live. Listening for Double-Snaps...")
last_snap_time = 0.0

try:
    while True:
        # exception_on_overflow=False is CRITICAL for Raspberry Pis!
        # If the Pi's CPU hiccups, this prevents the audio stream from crashing.
        data = stream.read(CHUNK, exception_on_overflow=False)
        audio_data = np.frombuffer(data, dtype=np.int16)
        
        # Check the chunk of audio for a snap
        snap_detected, vol = is_snap(audio_data)
        
        if snap_detected:
            current_time = time.time()
            time_difference = current_time - last_snap_time
            
            # STATE 2: Is it a valid DOUBLE snap?
            if MIN_TIME_WINDOW < time_difference < MAX_TIME_WINDOW:
                print(f"\n🚀 DOUBLE SNAP DETECTED! (Gap: {time_difference:.2f}s) -> WAKING UP HERMES!\n")
                
                # --- PUT YOUR TRIGGER CODE HERE ---
                # e.g., hermes.start_recording()
                
                # Reset the timer so a 3rd snap doesn't immediately trigger it again
                last_snap_time = 0.0 
                
            # STATE 1: Just a single snap. Start the timer!
            else:
                print(f"Single snap heard (Vol: {vol:.1f}). Waiting for second snap...")
                last_snap_time = current_time

except KeyboardInterrupt:
    print("\nStopping listener...")
finally:
    # Always cleanly close the hardware connection
    stream.stop_stream()
    stream.close()
    p.terminate()