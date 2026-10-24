import socket, threading
import wave
import webrtcvad
from audio_server import start_server
from enum import Enum

class SystemState(Enum):
    IDLE = "idle"               # Waiting for wake word
    LISTENING = "listening"     # Receiving UDP audio
    THINKING_SPEAKING = "thinking_speaking"       # Processing LLM and uploading wav for the esp to speak simultaneously (stream)
    SHUTDOWN = "shutdown"       # Failsafe triggered
    INPUT_READY ="input_ready"

# Initialize the starting state
current_state = SystemState.IDLE

# Initialize the VAD
vad = webrtcvad.Vad()
# Mode 3 is the most aggressive at filtering out background noise like TVs
vad.set_mode(3) 

# initialize the socket to listen for esp streams
UDP_IP = "0.0.0.0"
UDP_PORT = 5000
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
print(f"Listening on Port {UDP_PORT}...")

# 1. Fire up the server in the background
print("starting upload  webserver")
threading.Thread(target=start_server, daemon=True).start()

audio_buffer = bytearray()
recording = False
silence_frames = 0
MAX_SILENCE_FRAMES = 50  # 50 frames * 30ms = 1.5 seconds of silence



try:
    while True:
        data, addr = sock.recvfrom(4096)
        if data:
            if data == b"START":
                if current_state == SystemState.THINKING_SPEAKING:
                    print("Interruption detected! Aborting current speech...")
                    #TODO
                    # 1. Send the API command to the ESP32 to clear its media player queue
                    # 2. Set an event/flag to kill your background LLM/TTS generation tasks
                
                print(f"Wake word triggered! Receiving stream...")
                current_state = SystemState.LISTENING
                audio_buffer.clear()
                silence_frames = 0
                
            elif data == b"SHUTDOWN":
                print("EMERGENCY FAILSAFE TRIGGERED. Shutting down systems.")
                current_state = SystemState.SHUTDOWN
                # Send stop command to ESP32 media player here
                # Completely exit the program    
        
            elif data == b"STOP":
                print("15-second timeout reached! ESP32 closed the stream.")
                current_state= SystemState.INPUT_READY
                break;
        # ---------------------------------------------------------
        if current_state==SystemState.LISTENING:
            audio_buffer.extend(data)
            # 2. Check if we have enough bytes for a 30ms frame (960 bytes)
            while len(audio_buffer) >= 960:
                # Carve off the first 960 bytes
                frame = audio_buffer[:960]
                # Remove them from the buffer
                audio_buffer = audio_buffer[960:] 
                
                # 3. Feed the frame to the VAD
                # True = Human Voice, False = Silence
                is_speech = vad.is_speech(frame, 16000) 
                
                if is_speech:
                    silence_frames = 0 # Reset silence counter
                else:
                    silence_frames += 1
                
                # 4. If we hit 1.5 seconds of pure silence, kill the stream!
                if silence_frames >= MAX_SILENCE_FRAMES:
                    print("Silence detected! Stopping stream.")
                    sock.sendto(b"STOP", addr) 
                    recording = False
                    current_state = SystemState.THINKING
                    # e.g., threading.Thread(target=process_audio, args=(audio_buffer,)).start()
        
        elif current_state == SystemState.INPUT_READY:
            # save the wav file and send it to stt.py to get text back
            # send text to AI.py for ai response.
            current_state =SystemState.THINKING_SPEAKING
            print("stt starting")
        
        elif current_state == SystemState.THINKING_SPEAKING:
            # somehow get access to AI.py output stream and tool calling
            # TODO! remove python script execution in AI.py and implement here with threading instead of popen
            # after each sentence, send to tts and save to audio_output
            # if stream over: currentstate = idle
            print("AI reponse")



except KeyboardInterrupt:
    print("\nShutting down.")
