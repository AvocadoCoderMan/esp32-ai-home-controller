"""
audio_server.py - tiny HTTP file server for the assistant's spoken replies.

Serves ./audio_output on port 5000 (TCP) so the ESP32 can download and play
the generated TTS .wav files. Started in a daemon thread by main.py.

Note: os.chdir() changes the working directory of the whole process, so use
absolute paths elsewhere.
"""
import http.server
import socketserver
import os

def start_server(port=5000, directory="./audio_output"):
    # Ensure the directory exists
    os.makedirs(directory, exist_ok=True)
    os.chdir(directory)
    
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), Handler) as httpd:
        print(f"Web server running on port {port}")
        httpd.serve_forever()