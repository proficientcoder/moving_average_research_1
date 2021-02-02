import os
import json
import pytz
import time
import datetime

import dateutil.parser as parser


class Segment:
    def current(self):
        if self.use_clock:
            return int(datetime.datetime.now().timestamp() / self.interval)
        else:
            return self.last

    def __init__(self, seconds=None, minutes=None, hours=None, days=None, use_clock=True, file=None):
        self.interval = None
        self.use_clock = use_clock
        self.file = file

        if seconds is not None:
            self.interval = seconds

        if minutes is not None:
            self.interval = minutes * 60

        if hours is not None:
            self.interval = hours * 60 * 60

        if days is not None:
            self.interval = days * 24 * 60 * 60

        self.last = 0

        if self.file is not None:
            if os.path.exists(self.file):
                with open(self.file, 'r') as handle:
                    self.last = json.load(handle)

    def from_time_str(self, datetime_str):
        dt = parser.parse(datetime_str)
        self.last = int(dt.timestamp() / self.interval)

    def from_datetime(self, dt):
        self.last = int(dt.timestamp() / self.interval)

    def expired(self):
        return self.current() != self.last

    def handled(self):
        self.last = self.current()

        if self.file is not None:
            with open(self.file, 'w') as handle:
                json.dump(self.last, handle)

    def get_bounds(self):
        seconds = self.current() * self.interval
        start_dt = datetime.datetime.fromtimestamp(seconds)

        seconds += (self.interval - 1)
        stop_dt = datetime.datetime.fromtimestamp(seconds)
        return start_dt, stop_dt

    def get_bounds_utc(self):
        start_dt, stop_dt = self.get_bounds()

        start_dt = start_dt.astimezone(pytz.utc)
        stop_dt = stop_dt.astimezone(pytz.utc)

        return start_dt, stop_dt
