import os
import threading
from moviepy.editor import VideoFileClip
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class simulationcamera(FileSystemEventHandler):
    def __init__(self, input_directory, output_path, duration):
        self.input_directory = input_directory
        self.output_path = output_path
        self.duration = duration
        self.processed_videos = set()  # Track processed videos
        self.lock = threading.Lock()

    def on_created(self, event):
        if not event.is_directory:
            file_extension = os.path.splitext(event.src_path)[1].lower()
            if file_extension == ".mp4":
                threading.Thread(target=self.process_video, args=(event.src_path,)).start()
            else:
                print(f"Ignoring non-video file: {event.src_path}")

    def process_video(self, input_path):
        with self.lock:
            if input_path in self.processed_videos:
                return
            self.processed_videos.add(input_path)

        cut_video(input_path, self.output_path, self.duration)

    def process_video_directory(self):
        for file_name in os.listdir(self.input_directory):
            if file_name.lower().endswith(".mp4"):
                input_path = os.path.join(self.input_directory, file_name)
                self.process_video(input_path)


def cut_video(input_path, output_path, duration=10):
    video = VideoFileClip(input_path)
    total_duration = video.duration
    start_time = 0
    end_time = duration

    while end_time <= total_duration:
        base_filename = os.path.splitext(os.path.basename(input_path))[0]
        output_filename = f"{output_path}/{base_filename}_{start_time}_{end_time}.mp4"

        if os.path.exists(output_filename):
            print(f"Skipping existing file: {output_filename}")
        else:
            subclip = video.subclip(start_time, end_time)
            subclip.write_videofile(output_filename, codec="libx265", threads=4, verbose=False)

        start_time += duration
        end_time += duration

    video.close()


# Example usage:
input_directory = "../Videocamera"
output_path = "../video"
duration = 10

event_handler = simulationcamera(input_directory, output_path, duration)
event_handler.process_video_directory()  # Process existing videos before starting the observer

observer = Observer()
observer.schedule(event_handler, path=input_directory, recursive=False)
observer.start()

try:
    while True:
        observer.join(1)
except KeyboardInterrupt:
    observer.stop()

observer.join()
