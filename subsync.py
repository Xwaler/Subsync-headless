import os
import time
import shlex
import shutil
import requests
import threading
import json

from watchdog.observers import Observer
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from subprocess import check_call, DEVNULL, check_output, STDOUT, CalledProcessError

BAZARR_URL = os.environ.get('BAZARR_URL')
BAZARR_API_KEY = os.environ.get('BAZARR_API_KEY')
BAZARR_USERNAME = os.environ.get('BAZARR_USERNAME')
BAZARR_PASSWORD = os.environ.get('BAZARR_PASSWORD')
NUM_WORKERS = int(os.environ.get('NUM_WORKERS')) if os.environ.get('NUM_WORKERS') else 1

JOBS_FOLDER = 'jobs'
FAILED_JOBS_FOLDER = 'failed_jobs'

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
        job = json.load(f)

    if job['ref_lang'] == 'None':
        job['ref_lang'] = 'eng'

    subsync_ref_lang = job['ref_lang'] \
        .replace('fra', 'fre') \
        .replace('deu', 'ger') \
        .replace('lit', 'eng')  # Bazarr thinks YTS.LT releases are Lithuanian

    subsync_sub_lang = job['sub_lang'] \
        .replace('fra', 'fre') \
        .replace('deu', 'ger') \
        .replace('lit', 'eng')  # Bazarr thinks YTS.LT releases are Lithuanian

    print(f'Syncing {os.path.basename(file)}')
    command = f'/subsync/bin/subsync --cli --verbose 0 sync ' \
              f'--ref "{job["ref"]}" --ref-stream-by-type audio --ref-lang "{subsync_ref_lang}" ' \
              f'--sub "{job["sub"]}" --sub-lang "{subsync_sub_lang}" ' \
              f'--out "{job["sub"]}" --overwrite'

    try:
        check_call(shlex.split(command), stdout=DEVNULL, stderr=DEVNULL)
        print(f'Successful subsync {os.path.basename(file)}')
        if os.path.exists(os.path.join(FAILED_JOBS_FOLDER, os.path.basename(file))):
            os.remove(os.path.join(FAILED_JOBS_FOLDER, os.path.basename(file)))

    except CalledProcessError as e:
        print(f'Subsync failed {os.path.basename(file)} | {e}')

        command = f'/usr/local/bin/ffsubsync "{job["ref"]}" -i "{job["sub"]}" ' \
                  f' --max-offset-seconds 600 --encoding UTF-8 --overwrite-input'

        try:
            stdout = check_output(shlex.split(command), stderr=STDOUT, encoding='UTF-8')
            if 'Synchronization failed' in str(stdout):
                raise CalledProcessError(2, shlex.split(command))
            print(f'Successful ffsubsync {os.path.basename(file)}')
            if os.path.exists(os.path.join(FAILED_JOBS_FOLDER, os.path.basename(file))):
                os.remove(os.path.join(FAILED_JOBS_FOLDER, os.path.basename(file)))

        except CalledProcessError as e:
            print(f'FFSubsync failed {os.path.basename(file)} | {e}')

            print(f'Blacklisting {os.path.basename(file)}')
            s = requests.session()
            headers = {"x-api-key": BAZARR_API_KEY}
            r = s.post(f"{BAZARR_URL}/api/system/account?action=login",
                       data={"username": BAZARR_USERNAME, "password": BAZARR_PASSWORD})
            if not r.ok:
                print("Authentication failed")
                shutil.copy(file, os.path.join(FAILED_JOBS_FOLDER, os.path.basename(file)))
            else:
                data = {
                    'subtitles_path': job["sub"],
                    'provider': job["provider"],
                    'subs_id': job["sub_id"],
                    'language': job["sub_code_2"],
                }
                if not job["series_id"]:
                    url = f"{BAZARR_URL}/api/movies/blacklist?radarrid={job['episode_id']}"
                else:
                    url = f"{BAZARR_URL}/api/episodes/blacklist?seriesid={job['series_id']}&episodeid={job['episode_id']}"
                r = s.post(url, data=data, headers=headers)

                if r.ok:
                    print(f'Blacklisted {os.path.basename(file)}')
                else:
                    print(f'Failed to blacklist {os.path.basename(file)} : {r.text}')
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
        time.sleep(3)

        event_lock.acquire()
        content = os.listdir(JOBS_FOLDER)
        if last_file_event + 10 < time.time():
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
