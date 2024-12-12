import os
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class final_api_another:
    def __init__(self, target_url, video_directory):
        self.target_url = target_url
        self.video_directory = video_directory

    def run(self):
        self.send_videos_in_directory()
        self.start_listening()

    def send_videos_in_directory(self):
        for filename in os.listdir(self.video_directory):
            if filename.endswith('.mp4'):
                video_path = os.path.join(self.video_directory, filename)
                self.send_video(video_path)
                os.remove(video_path)

    def start_listening(self):
        event_handler = VideoHandler(self.send_video)
        observer = Observer()
        observer.schedule(event_handler, self.video_directory, recursive=False)
        observer.start()
        print("Listening for new videos...")

        try:
            while True:
                pass
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

    def send_video(self, video_path):
        with open(video_path, 'rb') as file:
            response = requests.post(self.target_url, files={'video': file})
            if response.status_code == 200:
                print("Video sent successfully.")
            else:
                print("Failed to send video.")

class VideoHandler(FileSystemEventHandler):
    def __init__(self, send_video_callback):
        self.send_video_callback = send_video_callback

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.mp4'):
            print(f"New video detected: {event.src_path}")
            self.send_video_callback(event.src_path)

if __name__ == '__main__':
    target_url = "http://192.168.1.3:5000/videoreceived"
    video_directory = "./sendVideos"
    sender = final_api_another(target_url, video_directory)
    sender.run()
