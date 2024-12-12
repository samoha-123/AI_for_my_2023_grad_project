from ultralytics import YOLO

# Load a model
model = YOLO('yolov8n.pt')# load the fresh model

# start training the model
model.train(data='data.yaml',epochs=300, imgsz=700)

# Load a model
# model = YOLO('path/to/last.pt')  # load a partially trained model

# Resume training
# results = model.train(resume=True)