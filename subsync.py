import os
import re
import time
import shlex
import shutil
import threading

from watchdog.observers import Observer
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from subprocess import check_call, CalledProcessError

NUM_WORKERS = int(os.environ.get('NUM_WORKERS')) if os.environ.get('NUM_WORKERS') else 1

JOBS_FOLDER = '/.config/jobs'
FAILED_JOBS_FOLDER = '/.config/failed_jobs'

if not os.path.exists(JOBS_FOLDER):
    os.mkdir(JOBS_FOLDER)
if not os.path.exists(FAILED_JOBS_FOLDER):
    os.mkdir(FAILED_JOBS_FOLDER)

event_lock = threading.Lock()
last_file_event = 0
last_event = None

worker_sem = threading.Semaphore(NUM_WORKERS)
working_lock = threading.Lock()
working = set()


class AnyEventHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        global last_file_event
        global last_event
        event_lock.acquire()
        t = time.time()
        if t > last_file_event:
            last_file_event = t
        if not isinstance(last_event, FileSystemEvent) or event.src_path != last_event.src_path:
            print(event)
        last_event = event
        event_lock.release()


def sync(file):
    global worker_sem
    global working

    with open(file, 'r') as f:
        command = f.readline()
    command = re.sub(r'-lang [\'"]?fra[\'"]?', '-lang fre', command)
    command = re.sub(r'-lang [\'"]?deu[\'"]?', '-lang ger', command)
    command = re.sub(r'-lang [\'"]?lit[\'"]?', '-lang eng', command)
    # Bazarr thinks YTS.LT releases are Lithuanian

    try:
        print(command)
        check_call(shlex.split(command))
        if os.path.exists(os.path.join(FAILED_JOBS_FOLDER, os.path.basename(file))):
            os.remove(os.path.join(FAILED_JOBS_FOLDER, os.path.basename(file)))

    except CalledProcessError:
        print(f'Subsync failed ! ({os.path.basename(file)})')

        ref = re.findall(r'(?<=--ref ")[^"]+(?=")', command)
        sub = re.findall(r'(?<=--sub ")[^"]+(?=")', command)
        command = f'ffsubsync "{ref}" -i "{sub}" --overwrite-input --encoding UTF-8 --max-offset-seconds 600'

        try:
            print(command)
            check_call(shlex.split(command))
            if os.path.exists(os.path.join(FAILED_JOBS_FOLDER, os.path.basename(file))):
                os.remove(os.path.join(FAILED_JOBS_FOLDER, os.path.basename(file)))

        except CalledProcessError:
            print(f'FFSubsync failed ! ({os.path.basename(file)})')
            shutil.copy(file, os.path.join(FAILED_JOBS_FOLDER, os.path.basename(file)))

    finally:
        working_lock.acquire()
        os.remove(file)
        working.remove(file)
        working_lock.release()

        worker_sem.release()


if __name__ == '__main__':
    observer = Observer()
    observer.schedule(AnyEventHandler(), JOBS_FOLDER, recursive=True)
    observer.start()

    while True:
        time.sleep(10)

        event_lock.acquire()
        content = os.listdir(JOBS_FOLDER)
        if last_file_event + 30 < time.time():
            event_lock.release()
            for thing in content:
                path = os.path.join(JOBS_FOLDER, thing)

                working_lock.acquire()
                cond = path in working
                working_lock.release()

                if cond:
                    continue
                if os.path.exists(path):
                    if os.path.isfile(path):
                        worker_sem.acquire()

                        working_lock.acquire()
                        working.add(path)
                        working_lock.release()

                        worker = threading.Thread(target=sync, args=(path,))
                        worker.start()
                    else:
                        print(f'Warning: non-file found in jobs queue ({thing})')
                else:
                    print(f"Job file doesn't exist ({thing})")
        else:
            event_lock.release()
