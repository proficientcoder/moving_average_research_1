import numba
import numpy as np

LONG = 1
SHORT = 2
BOTH = 3

@numba.njit()
def ma_crossover_simple(_bid, _ask, _slow, _fast, long_short):
    l = len(_bid)

    position = int(0)
    profit = float(0)

    deltas = np.zeros(l, dtype=numba.float64)
    positions = np.zeros(l, dtype=numba.float64)

    new_position = 0
    for k in range(200, l):
        if _fast[k] < _slow[k]:
            if long_short and SHORT:
                new_position = -1
            else:
                new_position = 0
        else:
            if long_short and LONG:
                new_position = +1
            else:
                new_position = 0

        # Taking position and calculating NAV's
        while position < new_position:
            position += 1
            profit -= _ask[k]

        while position > new_position:
            position -= 1
            profit += _bid[k]

        nav = profit
        _position = position

        while _position < 0:
            _position += 1
            nav -= _ask[k]

        while _position > 0:
            _position -= 1
            nav += _bid[k]

        spread = _ask[k] - _bid[k]
        deltas[k] = nav
        positions[k] = position

    #      0       1
    return deltas, positions, spread

