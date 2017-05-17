#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import subprocess
import sys
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


def log(message):
    print("[Monitor]", message)


class MyFileSystemEventHandler(FileSystemEventHandler):
    def __init__(self, func):
        super(MyFileSystemEventHandler, self).__init__()
        self.restart = func

    def on_any_event(self, event):
        if event.src_path.endswith(".py"):
            log("Python source file changed: {}".format(event.src_path))
            self.restart()


command = ("echo", "ok")
process = None


def kill_process():
    global process
    if process:
        log("Kill process [{}]...".format(process.pid))
        process.kill()
        process.wait()
        log("Process ended with code {}.".format(process.returncode))
        process = None


def start_process():
    global process, command
    log("Start process {}...".format(" ".join(command)))
    process = subprocess.Popen(command, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)


def restart_process():
    kill_process()
    start_process()


def start_watch(path, callback):
    observer = Observer()
    observer.schedule(MyFileSystemEventHandler(restart_process()), path, recursive=True)
    observer.start()
    log("Watching directory {}...".format(path))
    start_process()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == '__main__':
    argv = sys.argv[1:]
    if not argv:
        print("Usage: ./pymonitor your-script.py")
        exit(0)
    if argv[0] != "python":
        argv.insert(0, "python")
    command = tuple(argv)
    path = os.path.abspath(".")
    start_watch(path, None)
