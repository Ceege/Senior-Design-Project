from PySide.QtCore import *
from PySide.QtGui import *
import cv2
import sys
import Queue
import threading
import keyboard

from twisted.python import log
from twisted.internet import reactor
from autobahn.twisted.websocket import WebSocketServerProtocol
from autobahn.twisted.websocket import WebSocketServerFactory

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
        self.video_size = QSize(1920, 1080)
        self.setup_ui()
        self.setup_camera()

    def setup_ui(self):
        """Initialize widgets.
        """
        self.image_label = QLabel()
        self.image_label.setFixedSize(self.video_size)

        self.quit_button = QPushButton("Quit")
        self.quit_button.clicked.connect(self.close)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.image_label)
        self.main_layout.addWidget(self.quit_button)

        self.setLayout(self.main_layout)

    def setup_camera(self):
        """Initialize camera.
        """
        self.capture = VideoCap('https://192.168.1.222:8080/video')
        # self.capture.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, self.video_size.width())
        # self.capture.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, self.video_size.height())

        self.timer = QTimer()
        self.timer.timeout.connect(self.display_video_stream)
        self.timer.start(10)

    def display_video_stream(self):
        """Read frame from camera and repaint QLabel widget.
        """
        frame = self.capture.read()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        #frame = cv2.flip(frame, 1)
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