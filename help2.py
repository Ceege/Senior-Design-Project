import cv2
import Queue
import threading
import keyboard

import sys
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


# bufferless VideoCapture
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


cap = VideoCap('https://192.168.1.222:8080/video')
face_cascade = cv2.CascadeClassifier('C:\Users\CJ\Downloads\data\haarcascades\haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier('C:\Users\CJ\Downloads\data\haarcascades\haarcascade_eye.xml')
def thread_function():
    while True:
        frame = cap.read()
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
        imS = cv2.resize(frame, (960, 720))
        cv2.imshow("frame", imS)
        cv2.waitKey(1)
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


x = threading.Thread(target=thread_function)
x.start()

log.startLogging(sys.stdout)
factory = WebSocketServerFactory()
factory.protocol = MyServerProtocol
reactor.listenTCP(9000, factory)
reactor.run()
