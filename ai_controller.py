from car_crash_detection import CrashUtils
from flask import Flask, jsonify
import os
import time
from threading import Thread
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import mysql.connector
import random
from ultralytics import YOLO
import moviepy.editor as mp


def get_severity(model_path,video_path):
  model = YOLO(model_path)
  source = video_path
  # Run inference on the source
  results = model(source, stream=True)  # generator of Results objects
  detected_classes = {"low": 0,"medium": 0, "high": 0}
  there_is_a_smoke = False
  there_is_a_fire_or_injury = False
  for result in results:
    boxes = result.boxes.cpu().numpy()  # get boxes on cpu in numpy
    for box in boxes:
      cls = result.names[int(box.cls[0])]
      if cls == "low" or cls == "medium" or cls == "high":
        detected_classes[cls] = detected_classes[cls] + 1
      elif cls == "fire" or cls == "detected-injury":
        there_is_a_fire_or_injury = True
      elif cls == "smoke":
        there_is_a_smoke = True
  # print("detected_classes:", detected_classes, "there_is_a_smoke:", there_is_a_smoke,"there_is_a_fire_or_injury:", there_is_a_fire_or_injury)
  there_is_an_accident = any(value > 0 for value in detected_classes.values())
  there_is_a_car_smoke = there_is_a_smoke and there_is_an_accident
  if not there_is_an_accident and not there_is_a_fire_or_injury:
    return "none"
  elif there_is_a_fire_or_injury or there_is_a_car_smoke or (detected_classes["high"] >= detected_classes["medium"] and detected_classes["high"] >= detected_classes["low"]):
    return "high"
  elif detected_classes["medium"] >= detected_classes["high"] and detected_classes["medium"] >= detected_classes["low"]:
    return "medium"
  elif detected_classes["low"] >= detected_classes["high"] and detected_classes["low"] >= detected_classes["medium"]:
    return "low"


def generate_3d_list(length):
    city_list = []
    for _ in range(length):
        city_name = generate_city_name()
        longitude = random.uniform(-180, 180)
        latitude = random.uniform(-90, 90)
        city_data = [city_name, longitude, latitude]
        city_list.append(city_data)
    return city_list
def generate_city_name():
    # You can customize this function to generate city names as per your requirements
    # For simplicity, I'm generating random city names using a predefined list
    city_names = ['New York', 'London', 'Tokyo', 'Paris', 'Sydney', 'Beijing', 'Cairo', 'Rio de Janeiro', 'Moscow','Rome']
    return random.choice(city_names)
# Generating a 3D list of length 100
city_data_list = generate_3d_list(100)
# Printing the generated list
for city_data in city_data_list:
    print(city_data)


# Establish a connection to a MySQL database
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='ahmedshamaa',
    database='ai_for_safe_transportation'
)

# Create a cursor object
cursor = conn.cursor()

# Check if the table already exists
table_name = 'reports'
cursor.execute("SHOW TABLES LIKE '{}'".format(table_name))
table_exists = cursor.fetchone()

# If the table doesn't exist, create it
if not table_exists:
    # Execute the SQL CREATE TABLE statement
    sql = "CREATE TABLE `ai_for_safe_transportation`.`reports` (`id` INT NOT NULL AUTO_INCREMENT,`severity` VARCHAR(45) NULL,`location` VARCHAR(45) NULL,`latitude` DOUBLE NULL,`longitude` DOUBLE NULL,`name` VARCHAR(45) NULL,`state` VARCHAR(45) NULL,`action` VARCHAR(45) NULL,PRIMARY KEY (`id`),UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE);"
    cursor.execute(sql)
    print("Table created successfully.")
else:
    print("Table already exists.")

################################################
app = Flask(__name__)
#####################################################

input_dir = "video"
output_dir = "video_output"

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

inputpathList = []
results = []
results_severity = []






def is_video_file(file_path):
    video_extensions = ['.mp4', '.avi', '.mkv']  # Add more video extensions if needed
    file_extension = os.path.splitext(file_path)[1]
    return file_extension.lower() in video_extensions

def get_video_duration(video_path):
    try:
        video = mp.VideoFileClip(video_path)
        return video.duration
    except Exception as e:
        print(f"Error occurred while reading the duration of file '{video_path}': {e}")
        return 0

prev_video_name = None
prev_random_city_data=None
def process_videos():
    global prev_video_name
    global prev_random_city_data
    while True:
        if inputpathList:
            video = inputpathList.pop(0)
            inputpath = video[0]
            outputpath = video[1]

            if not is_video_file(inputpath):
                print(f"Skipping file '{inputpath}' as it is not a video file.")
                continue

            video_duration = get_video_duration(inputpath)
            if video_duration == 0:
                print(f"Skipping video '{inputpath}' due to an error in reading the duration.")
                continue
            elif video_duration < 10:
                print(f"Skipping video '{inputpath}' with duration less than 10 seconds.")
                continue

            predicted_class_probabilities = CrashUtils.crashDetection(
                inputPath=inputpath,
                seq=5,
                skip=1,
                outputPath=outputpath,
                showInfo=True,
                thresholding=0.83,
            )

            # Check if the inputpath already exists in the results list
            existing_result = next((res for res in results if res[0] == inputpath), None)
            if existing_result:
                existing_result[1] = predicted_class_probabilities
            else:
                # Add the input video filename and its predicted_class_probabilities to the results list
                result = [inputpath, predicted_class_probabilities]
                results.append(result)
                #Add the input video filename and its predicted_class_probabilities to the results_severity list
                videoNameFromInputpath2 = inputpath.replace("video\\", "")
                resulttt = [videoNameFromInputpath2, "null"]
                results_severity.append(resulttt)

            print("Predicted Class Probabilities: ", predicted_class_probabilities)
            # Execute the SQL SELECT statement to check if the name already exists
            videoNameFromInputpath = inputpath.replace("video\\", "")
            check_sql = "SELECT name FROM `ai_for_safe_transportation`.`reports` WHERE name = %s"
            cursor.execute(check_sql, (videoNameFromInputpath,))
            existing_row = cursor.fetchone()

            if existing_row:
                print("A row with name '{}' already exists. Skipping insertion.".format(videoNameFromInputpath))
            elif predicted_class_probabilities == "accident":
                # Selecting a random city data from the list
                cut_name = videoNameFromInputpath.split('_')[0]
                if prev_video_name is not None and cut_name == prev_video_name.split('_')[0]:
                    random_city_data =prev_random_city_data
                else:
                    random_city_data = random.choice(city_data_list)
                    prev_random_city_data=random_city_data
                # Execute the SQL INSERT statement
                severitypredicted=get_severity('final_model_nano.pt',inputpath)
                insert_sql = "INSERT INTO `ai_for_safe_transportation`.`reports` (`name`, `state`,`location`,`latitude`,`longitude`,`severity`) VALUES (%s, %s, %s, %s, %s,%s)"
                cursor.execute(insert_sql, (videoNameFromInputpath, predicted_class_probabilities,random_city_data[0],random_city_data[1], random_city_data[2], severitypredicted))
                # Commit the changes to the database
                conn.commit()
                print("Row inserted successfully.")
            else :
                # Selecting a random city data from the list
                cut_name = videoNameFromInputpath.split('_')[0]
                if prev_video_name is not None and cut_name == prev_video_name.split('_')[0]:
                    random_city_data = prev_random_city_data
                else:
                    random_city_data = random.choice(city_data_list)
                    prev_random_city_data = random_city_data
                # Execute the SQL INSERT statement

                insert_sql = "INSERT INTO `ai_for_safe_transportation`.`reports` (`name`, `state`,`location`,`latitude`,`longitude`,`severity`) VALUES (%s, %s, %s, %s, %s,%s)"
                cursor.execute(insert_sql, (videoNameFromInputpath, predicted_class_probabilities, random_city_data[0], random_city_data[1],random_city_data[2], "low"))
                # Commit the changes to the database
                conn.commit()
                print("Row inserted successfully.")

            prev_video_name=videoNameFromInputpath





def start_processing():
    while True:
        update_input_path_list()
        if inputpathList:
            process_videos()
        time.sleep(1)


@app.route('/mylist', methods=['GET'])
def get_list():
    resultss = [[item.replace('video\\', '') for item in sublist] for sublist in results]
    return jsonify(resultss)

@app.route('/api/mylistOfSevirity', methods=['GET'])
def get_severity_data():
    try:
        return jsonify(results_severity)

    except Exception as e:
        # Handle any potential errors
        print("Error:", str(e))
        return jsonify({'error': 'An error occurred'}), 500

def update_input_path_list():
    # Get a list of all video files in the input directory
    new_inputpathList = []
    for filename in os.listdir(input_dir):
        if filename.endswith(".mp4"):
            inputpath = os.path.join(input_dir, filename)
            outputpath = os.path.join(output_dir, filename)
            new_inputpathList.append([inputpath, outputpath])

    # Check for new videos and add them to the list
    for video in new_inputpathList:
        if video not in inputpathList:
            inputpathList.append(video)

    # Check for deleted videos and remove them from the list and results
    videos_to_remove = []
    for video in inputpathList:
        if video not in new_inputpathList:
            videos_to_remove.append(video)

    for video in videos_to_remove:
        inputpathList.remove(video)
        result = next((res for res in results if res[0] == video[0]), None)
        if result:
            results.remove(result)

    # Delete corresponding files from video_output directory
    for video in videos_to_remove:
        output_file = video[1]
        if os.path.exists(output_file):
            os.remove(output_file)

    # Remove any results that have a video path not present in inputpathList
    results_to_remove = []
    for result in results:
        video_path = result[0]
        if not any(video_path == video[0] for video in inputpathList):
            results_to_remove.append(result)

    for result in results_to_remove:
        results.remove(result)





class ai_controller(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.is_directory:
            return
        elif event.event_type == 'created':
            if event.src_path.endswith(".mp4"):
                update_input_path_list()
        elif event.event_type == 'deleted':
            if event.src_path.endswith(".mp4"):
                deleted_file = event.src_path
                deleted_output_file = os.path.join(output_dir, os.path.basename(deleted_file))
                # Remove the deleted file from inputpathList
                inputpathList[:] = [video for video in inputpathList if video[0] != deleted_file]
                # Remove the corresponding output file if it exists
                if os.path.exists(deleted_output_file):
                    os.remove(deleted_output_file)
                # Remove the corresponding result entry if it exists
                results[:] = [result for result in results if result[0] != deleted_file]
                update_input_path_list()


event_handler = ai_controller()
observer = Observer()
observer.schedule(event_handler, path=input_dir, recursive=True)




if __name__ == "__main__":
    observer.start()
    processing_thread = Thread(target=start_processing)
    processing_thread.start()
    app.run()
    observer.stop()


observer.join()
