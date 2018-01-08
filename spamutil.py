import os
import time

import sys


class Timer(object):
    def __init__(self, name):
        self.name = name
        self.start_time = time.time()
        self.end_time = None

    def show(self):
        if self.end_time is None:
            show_time = time.time()
        else:
            show_time = self.end_time

        elapsed = show_time - self.start_time
        return "time to %s: %0.2f s" % (self.name, elapsed)

    def stop(self):
        self.end_time = time.time()

    def stop_and_show(self):
        self.stop()
        return self.show()


log_handle = None


# noinspection PyProtectedMember
def dout(s):
    frame = sys._getframe(1)
    filename = frame.f_code.co_filename
    if type(s) == unicode:
        s = s.encode("utf-8")
    output = "%s:%d: %s" % (os.path.basename(filename), frame.f_lineno, s)
    print output
    if log_handle is not None:
        print >> log_handle, output
        log_handle.flush()


def dlogfile(filename):
    global log_handle
    log_handle = open(filename, "a")
