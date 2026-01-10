from __future__ import annotations
import threading
from queue import Queue, Empty
import pythoncom
import pyttsx3

class VoiceManager:
    def __init__(self, rate: int=200):
        self.rate = rate
        self._q: Queue[str] = Queue()
        self._stop = threading.Event()
        self._closed = threading.Event()
        self._lock = threading.Lock()
        self._engine = None

        self._t = threading.Thread(target=self._loop, daemon=True)
        self._t.start()

    def speak(self, text: str, interrupt: bool=True):
        with self._lock:
            if interrupt:
                self.stop()
                self._drain_queue()
            self._q.put(text)

    def stop(self):
        self._stop.set()
        with self._lock:
            if self._engine:
                try:
                    self._engine.stop()
                except:
                    pass

    def close(self):
        self._closed.set()
        self.stop()
        self._drain_queue()

    def _drain_queue(self):
        while True:
            try:
                self._q.get_nowait()
                self._q.task_done()
            except Empty:
                break

    def _loop(self):
        pythoncom.CoInitialize()
        try:
            while not self._closed.is_set():
                self._stop.clear()
                try:
                    text = self._q.get(timeout=0.2)
                except Empty:
                    continue

                try:
                    with self._lock:
                        self._engine = pyttsx3.init()
                        self._engine.setProperty("rate", self.rate)

                    def on_word(name, location, length):
                        if self._stop.is_set():
                            raise RuntimeError("interrupted")

                    self._engine.connect("started-word", on_word)
                    self._engine.say(text)
                    self._engine.runAndWait()

                except RuntimeError:
                    pass
                finally:
                    with self._lock:
                        self._engine = None
                    self._q.task_done()
        finally:
            pythoncom.CoUninitialize()
