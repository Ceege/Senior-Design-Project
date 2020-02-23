from PySide.QtCore import *
from PySide.QtGui import *
import cv2
import sys
import Queue
import threading
import keyboard
import socket
import os
import numpy as np
from PIL import Image

from twisted.python import log
from twisted.internet import reactor
from autobahn.twisted.websocket import WebSocketServerProtocol
from autobahn.twisted.websocket import WebSocketServerFactory

import json

with open('data.txt') as json_file:
    data = json.load(json_file)
    print(data)
face_cascade = cv2.CascadeClassifier('C:\Users\CJ\Downloads\data\haarcascades\haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier('C:\Users\CJ\Downloads\data\haarcascades\haarcascade_eye.xml')
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read('trainer/trainer.yml')
font = cv2.FONT_HERSHEY_SIMPLEX
class MyServerProtocol(WebSocketServerProtocol):
    connections = list()

    def onConnect(self, request):
        print("Client connecting: {0}".format(request.peer))
        self.connections.append(self)

    def onOpen(self):
        print("WebSocket connection open.")

    def onMessage(self, payload, isBinary):
        if isBinary:
            print("Binary message received: {0} bytes".format(len(payload)))
        else:
            print("Text message received: {0}".format(payload.decode('utf8')))

        # echo back message verbatim
        self.sendMessage(payload, isBinary)

    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed: {0}".format(reason))
        self.connections.remove(self)

    @classmethod
    def broadcast_message(cls, data):
        for c in set(cls.connections):
            reactor.callFromThread(cls.sendMessage, c, data)


class VideoCap:

  def __init__(self, name):
    self.cap = cv2.VideoCapture(name)
    self.q = Queue.Queue()
    t = threading.Thread(target=self._reader)
    t.daemon = True
    t.start()

  # read frames as soon as they are available, keeping only most recent one
  def _reader(self):
    while True:
      ret, frame = self.cap.read()
      if not ret:
        break
      if not self.q.empty():
        try:
          self.q.get_nowait()   # discard previous (unprocessed) frame
        except Queue.Empty:
          pass
      self.q.put(frame)

  def read(self):
    return self.q.get()

class MainApp(QWidget):

    def __init__(self):
        QWidget.__init__(self)
        self.video_size = QSize(1280, 720)
        self.algorithm_index = 0
        self.names = []
        for p in data['people']:
            self.names.append(p['name'])
        self.setup_ui()
        self.console.append("People loaded " + str(len(data['people'])))
        self.move(300, 300)

    def connection(self):
        self.setup_camera()

    def faceDetection(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        for (x, y, w, h) in faces:
            # To draw a rectangle in a face
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 0), 2)
            roi_gray = gray[y:y + h, x:x + w]
            roi_color = frame[y:y + h, x:x + w]

            # Detects eyes of different sizes in the input image
            eyes = eye_cascade.detectMultiScale(roi_gray)

            # To draw a rectangle in eyes
            for (ex, ey, ew, eh) in eyes:
                cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 127, 255), 2)
        return frame

    def getPos(self, event):
        x = event.pos().x()
        y = event.pos().y()
        print(x)

    def btnstate(self, b):

        if b.text() == "None":
            if b.isChecked() == True:
                self.algorithm_index = 0
                self.console.append("No algorithm applied")
            else:
                print b.text() + " is deselected"
        if b.text() == "Face Detection":
            if b.isChecked() == True:
                self.algorithm_index = 1
                self.console.append("Face Detection applied")
            else:
                print b.text() + " is deselected"
        if b.text() == "Face Recognizer":
            if b.isChecked() == True:
                self.algorithm_index = 2
                self.console.append("Face Recognizer applied")
                self.console.append("Please enter name and hit enter")
                self.input_text.setEnabled(True)
                self.input_text.show()
            else:
                print b.text() + " is deselected"
                self.input_text.setEnabled(False)
                self.input_text.hide()
        if b.text() == "Face Recognition":
            if b.isChecked() == True:
                self.algorithm_index = 3
                self.console.append("Face Recognition applied")
            else:
                print b.text() + " is deselected"


    def FaceDetectName(self):
        face_id = len(data['people'])
        data['people'].append({
        'name': self.input_text.text(),
        'id': str(face_id),
        })
        self.names = []
        for p in data['people']:
            self.names.append(p['name'])
        with open('data.txt', 'w') as outfile:
            json.dump(data, outfile)

        self.console.append("* Initializing face capture. Look the camera and wait ...")
        # Initialize individual sampling face count
        count = 0
        while (True):
            img = self.capture.read()
            #img = cv2.flip(img, -1)  # flip video image vertically
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            for (x, y, w, h) in faces:
                cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
                count += 1
                self.console.append("Captured sample " + str(count))
                # Save the captured image into the datasets folder
                cv2.imwrite("dataset/User." + str(face_id) + '.' + str(count) + ".jpg", gray[y:y + h, x:x + w])
            if count >= 30:  # Take 30 face sample and stop video
                self.console.append("Captured all data")
                break
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        path = 'dataset'
        def getImagesAndLabels(path):
            imagePaths = [os.path.join(path, f) for f in os.listdir(path)]
            faceSamples = []
            ids = []
            for imagePath in imagePaths:
                PIL_img = Image.open(imagePath).convert('L')  # convert it to grayscale
                img_numpy = np.array(PIL_img, 'uint8')
                id = int(os.path.split(imagePath)[-1].split(".")[1])
                faces = face_cascade.detectMultiScale(img_numpy)
                for (x, y, w, h) in faces:
                    faceSamples.append(img_numpy[y:y + h, x:x + w])
                    ids.append(id)
            return faceSamples, ids

        self.console.append("Training faces. It will take a few seconds. Wait ...")
        faces, ids = getImagesAndLabels(path)
        recognizer.train(faces, np.array(ids))
        # Save the model into trainer/trainer.yml
        recognizer.save('trainer/trainer.yml')  # recognizer.save() worked on Mac, but not on Pi
        # Print the numer of faces trained and end program
        recognizer.read('trainer/trainer.yml')
        self.console.append("{0} faces trained. Exiting Program".format(len(np.unique(ids))))

    def faceRecognition(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        minW = 0.1*1280
        minH = 0.1*720
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=5,
            minSize=(int(minW), int(minH)),
        )
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            id, confidence = recognizer.predict(gray[y:y + h, x:x + w])
            # Check if confidence is less them 100 ==> "0" is perfect match
            if (confidence < 100):
                id = self.names[id]
                confidence = "  {0}%".format(round(100 - confidence))
            else:
                id = "unknown"
                confidence = "  {0}%".format(round(100 - confidence))

            cv2.putText(frame, str(id), (x + 5, y - 5), font, 1, (255, 255, 255), 2)
            cv2.putText(frame, str(confidence), (x + 5, y + h - 5), font, 1, (255, 255, 0), 1)

        return frame


    def setup_ui(self):
        """Initialize widgets.
        """
        self.image_label = QLabel()
        self.image_label.setFixedSize(self.video_size)
        self.image_label.mousePressEvent = self.getPos
        self.quit_button = QPushButton("Quit")
        self.quit_button.clicked.connect(self.close)

        self.textbox = QLineEdit("192.168.1.222")
        self.IPlabel = QLabel(self)
        self.IPlabel.setStyleSheet("QLabel { color : green; }")
        self.IPlabel.setText("My IP: " + socket.gethostbyname_ex(socket.gethostname())[2][2])

        self.IPlabel2 = QLabel(self)
        self.IPlabel2.setText("                               Phone IP: ")

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connection)

        self.button_menu = QHBoxLayout()
        self.button_menu.addWidget(self.IPlabel)
        self.button_menu.addWidget(self.IPlabel2)
        self.button_menu.addWidget(self.textbox)
        self.button_menu.addWidget(self.connect_button)
        self.button_menu.addWidget(self.quit_button)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.image_label)
        self.main_layout.addLayout(self.button_menu)

        # Right side UI setup

        self.main_layout1 = QVBoxLayout()
        self.b1 = QRadioButton("None")
        self.b1.setChecked(True)
        self.b1.toggled.connect(lambda: self.btnstate(self.b1))
        self.main_layout1.addWidget(self.b1)
        self.b2 = QRadioButton("Face Detection")
        self.b2.toggled.connect(lambda: self.btnstate(self.b2))
        self.main_layout1.addWidget(self.b2)
        self.b3 = QRadioButton("Face Recognizer")
        self.b3.toggled.connect(lambda: self.btnstate(self.b3))
        self.main_layout1.addWidget(self.b3)
        self.b4 = QRadioButton("Face Recognition")
        self.b4.toggled.connect(lambda: self.btnstate(self.b4))
        self.main_layout1.addWidget(self.b4)

        self.input_text = QLineEdit()
        self.input_text.returnPressed.connect(self.FaceDetectName)
        self.input_text.setEnabled(False)
        self.input_text.hide()
        self.main_layout1.addWidget(self.input_text)
        self.console = QTextBrowser()
        self.console.setFixedWidth(350)
        self.main_layout1.addWidget(self.console)

        self.master_layout = QHBoxLayout()
        self.master_layout.addLayout(self.main_layout)
        self.master_layout.addLayout(self.main_layout1)

        self.setLayout(self.master_layout)


    def setup_camera(self):
        """Initialize camera.
        """
        self.capture = VideoCap('https://' + self.textbox.text() + ':8080/video')
        # self.capture.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, self.video_size.width())
        # self.capture.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, self.video_size.height())
        self.console.append("Video Capture Initialized")
        self.timer = QTimer()
        self.timer.timeout.connect(self.display_video_stream)
        self.timer.start(30)

    def display_video_stream(self):
        """Read frame from camera and repaint QLabel widget.
        """
        frame = self.capture.read()
        if self.algorithm_index == 0:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if self.algorithm_index == 1:
            frame = self.faceDetection(frame)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if self.algorithm_index == 2:
            frame = self.faceDetection(frame)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if self.algorithm_index == 3:
            frame = self.faceRecognition(frame)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = QImage(frame, frame.shape[1], frame.shape[0],
                       frame.strides[0], QImage.Format_RGB888)
        self.image_label.setPixmap(QPixmap.fromImage(image))
        command = "none"
        if keyboard.is_pressed('a'):
            command = "left"
        if keyboard.is_pressed('w'):
            command = "up"
        if keyboard.is_pressed('s'):
            command = "down"
        if keyboard.is_pressed('d'):
            command = "right"
        if keyboard.is_pressed('w') and keyboard.is_pressed('d'):
            command = "leftup"
        if keyboard.is_pressed('w') and keyboard.is_pressed('a'):
            command = "rightup"
        MyServerProtocol.broadcast_message(command)

def thread_function():
    app = QApplication(sys.argv)
    win = MainApp()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    x = threading.Thread(target=thread_function)
    x.start()

    log.startLogging(sys.stdout)
    factory = WebSocketServerFactory()
    factory.protocol = MyServerProtocol
    reactor.listenTCP(9000, factory)
    reactor.run()
