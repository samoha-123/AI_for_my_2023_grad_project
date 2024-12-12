from flask import Flask, request
import os

class final_api:
    def __init__(self):
        self.app = Flask(__name__)

    def run(self):
        self.app.route('/videoreceived', methods=['POST'])(self.receive_video)
        self.app.run(host='0.0.0.0', port=5000)

    def receive_video(self):
        video_file = request.files['video']
        save_directory = os.path.join('Videocamera')
        os.makedirs(save_directory, exist_ok=True)
        video_file.save(os.path.join(save_directory, video_file.filename))
        print("Video received and saved.")
        return 'Video received', 200

if __name__ == '__main__':
    receiver = final_api()
    receiver.run()
