import os
import time
import shlex
import threading

from watchdog.observers import Observer
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from subprocess import check_call, CalledProcessError

JOBS_FOLDER = './config/jobs'

c = threading.Condition()
last_file_event = 0
last_event = None


class AnyEventHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        global last_file_event
        global last_event
        c.acquire()
        t = time.time()
        if t > last_file_event:
            last_file_event = t
        if not isinstance(last_event, FileSystemEvent) or event.src_path != last_event.src_path:
            print(event)
        last_event = event
        c.release()


def sync(file):
    with open(file, 'r') as f:
        command = f.readline()

    try:
        print(command)
        check_call(shlex.split(command))
        os.remove(file)

    except CalledProcessError:
        print('Sync failed !')
        time.sleep(150)


if __name__ == '__main__':
    observer = Observer()
    observer.schedule(AnyEventHandler(), JOBS_FOLDER, recursive=True)
    observer.start()

    while True:
        time.sleep(10)

        c.acquire()
        content = os.listdir(JOBS_FOLDER)
        if last_file_event + 30 < time.time():
            c.release()
            for thing in content:
                path = os.path.join(JOBS_FOLDER, thing)
                if os.path.isfile(path):
                    sync(path)
                else:
                    print(f'Warning: non-file found in jobs queue ({path})')
        else:
            c.release()
