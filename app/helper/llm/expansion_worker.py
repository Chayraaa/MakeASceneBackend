from queue import Queue
import threading


class ExpansionWorker:
    def __init__(self, process_fn):
        self._process_fn = process_fn
        self.queue = Queue()

        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def enqueue(self, item):
        self.queue.put(item)

    def _run(self):
        while True:
            item = self.queue.get()
            try:
                self._process_fn(item)
            except Exception as e:
                print("worker error:", e)