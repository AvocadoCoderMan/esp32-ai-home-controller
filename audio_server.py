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