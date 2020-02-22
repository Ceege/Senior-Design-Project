from PySide.QtCore import *
from PySide.QtGui import *
import cv2
import sys
import Queue
import threading
import keyboard
import socket

from twisted.python import log
from twisted.internet import reactor
from autobahn.twisted.websocket import WebSocketServerProtocol
from autobahn.twisted.websocket import WebSocketServerFactory

face_cascade = cv2.CascadeClassifier('C:\Users\CJ\Downloads\data\haarcascades\haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier('C:\Users\CJ\Downloads\data\haarcascades\haarcascade_eye.xml')

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
        self.setup_ui()
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
        print(socket.gethostbyname_ex(socket.gethostname())[2][2])

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

        self.console = QTextBrowser()
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
