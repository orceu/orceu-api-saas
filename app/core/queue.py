import threading
from queue import Queue

# Fila thread-safe para simulação
_import_queue = Queue()

# Lock para leitura segura
_queue_lock = threading.Lock()

def enqueue_import_task(task: dict):
    with _queue_lock:
        _import_queue.put(task)

def get_all_tasks():
    with _queue_lock:
        tasks = []
        while not _import_queue.empty():
            tasks.append(_import_queue.get())
        return tasks
