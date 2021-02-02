import numba
from itertools import chain

@numba.njit()
def remap(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def ztime_to_time(time):
    return time[:10] + ' ' + time[11:19]


def time_to_ztime(time):
    return time[:10] + 'T' + time[11:19] + '.000000000Z'

