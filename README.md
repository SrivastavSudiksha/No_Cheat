# No_Cheat

No_Cheat is a smart exam monitoring system that watches over online exams and flags suspicious behavior — automatically.

It uses a webcam to check things like whether the candidate is looking away from the screen, if someone else has entered the frame, if the candidate has left the camera view, or if a phone or book is visible. The goal is simple: make remote exams fairer and harder to cheat in.

## What It Does

- Watches the webcam feed in real time during an exam
- Notices if the candidate keeps looking away from the screen
- Detects if more than one person shows up on camera
- Flags it if the candidate isn't visible at all
- Spots phones or books using a model trained on our own data
- Keeps a timestamped record of anything suspicious
- Shows everything on a simple dashboard for exam admins to review

## Built With

**Backend**
- Java + Spring Boot

**AI / Vision**
- Python
- OpenCV
- MediaPipe
- YOLOv8
- ONNX Runtime

**Database**
- MySQL / PostgreSQL

**Communication**
- REST APIs

## How It Works

```
Webcam feed
     ↓
Python detection service checks for:
  • is a face visible?
  • how many faces?
  • which way are they looking?
  • any phone/book in view?
     ↓
Violations get flagged and logged
     ↓
Sent to the Spring Boot backend
     ↓
Shown on the admin dashboard
```

## Breaking Down the Detection

**No face detected**
Picks up on the candidate stepping away or blocking the camera.

**Multiple faces**
Notices if someone else joins the candidate on camera.

**Looking away**
Tracks head position to tell if the candidate keeps glancing off-screen.

**Phones / books**
A model trained on our own recorded footage — not just an off-the-shelf detector.

**Logging**
Every flagged moment gets a timestamp so it can be reviewed later.

## Folder Layout

```
No_Cheat/
├── backend/              Spring Boot app
├── detection_service/    Python service that does the actual detection
│   ├── app.py
│   ├── face_detector.py
│   ├── gaze_estimator.py
│   └── object_detector.py
├── training/              Scripts used to train the models
│   ├── data_collection.py
│   ├── train_gaze_model.py
│   ├── train_face_model.py
│   └── train_object_model.py
├── dataset/                Our own recorded and labeled data
│   ├── gaze/
│   ├── face_count/
│   └── objects/
└── README.md
```

## Running It

**Detection service**
```bash
cd detection_service
pip install -r requirements.txt
python app.py
```

**Backend**
```bash
cd backend
./mvnw spring-boot:run
```

## Where It's At

🚧 Still a work in progress.

Thinking about adding next:
- Identity check via face recognition
- Picking up on odd background audio
- Keeping an eye on browser tab switching
- A scoring system instead of flat flags
- Getting it running on the cloud

## Made By

Sudiksha Srivastav
