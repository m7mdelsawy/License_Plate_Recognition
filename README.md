# License Plate Recognition System

The License Plate Recognition System is a project that uses **artificial intelligence** to detect vehicles and accurately read license plates using **OpenCV**, **YOLO**, and **OCR** technologies. The goal of the project is to improve the automation of traffic management and speed monitoring using surveillance cameras.

## Features

- **Vehicle Detection** using the **YOLO** model.
- **License Plate Recognition** using **OCR**.
- **Speed Calculation** for vehicles and logging **violations** in a database.
- **Watchlist Management** to check suspicious license plates.
- **API Interface** using **FastAPI** to upload videos and track processing status.

## System Requirements

- Python 3.8 or higher
- Required Python libraries:
  - `fastapi`
  - `uvicorn`
  - `opencv-python`
  - `paddleocr`
  - `ultralytics`
  - `sqlite3`
  - `python-multipart`

You can install the required dependencies using:
```bash
pip install -r requirements.txt
