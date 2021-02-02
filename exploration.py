import cv2
import time
import numpy as np
from dateutil import parser
from collections import namedtuple

import inc.oanda as broker
import inc.tradesim as tradesim



OANDA_account = namedtuple('OANDA_account', 'key account env host')
account = OANDA_account('????????????????????????????????-????????????????????????????????',
                        '???-???-???????-???',
                        'demo',
                        'api-fxpractice.oanda.com')


def main(account, instrument):
    bracket_start = parser.parse('11-01-2020 12:00 UTC')
    bracket_stop = parser.parse('11-08-2020 12:00 UTC')


    data = broker.fetch_m1(account, instrument, start_dt=bracket_start, stop_dt=bracket_stop)
    data = broker.raw_candles_to_dataframe(data)

    s = 190
    cache = dict()
    for sloww in range(10, s):
        for fastw in range(10, s):
            id = f'{sloww}-{fastw}'

            slow = data[f'close_{sloww}_ema']
            fast = data[f'close_{fastw}_ema']

            deltas, positions, spread = tradesim.ma_crossover_simple(np.array(data['bid']),
                                                              np.array(data['ask']),
                                                              np.array(slow),
                                                              np.array(fast),
                                                              tradesim.BOTH)
            cache[id] = deltas
            print(f'\r{id}', end='')


    print()
    frames = []
    width = 500
    for index in range(0, len(data)-width, 1):
        print(f'\r{index}/{len(data)}', end='')
        columns = []
        for sloww in range(10, s):
            rows = []
            for fastw in range(10, s):
                id = f'{sloww}-{fastw}'
                nav = cache[id][index+width]-cache[id][index]
                rows.append(nav)
            columns.append(rows)
        frames.append((columns, data['time'][index]))

    print()

    height = 1000
    width = 1000
    canvas = np.zeros(shape=[height, width, 3], dtype=np.uint8)
    cv2.rectangle(canvas,
                  (0, 0),
                  (width, height),
                  (0, 0, 0),
                  -1)

    print('Ready.....')
    cv2.imshow('Technical analysis', canvas)
    cv2.waitKey(0)

    for f in frames:
        f, d = f
        low = 0
        high = 0
        for x in range(0, s-10):
            for y in range(0, s-10):
                if f[x][y] < low:
                    low = f[x][y]
                if f[x][y] > high:
                    high = f[x][y]
        print(low, high)

        for x in range(0, s-10):
            for y in range(0, s-10):
                if x == y:
                    continue
                b = 0
                g = 0
                r = 0
                if f[x][y] < 0:
                    r = int(255 * (f[x][y] / low))
                if f[x][y] > 0:
                    g = int(255 * (f[x][y] / high))
                cv2.rectangle(canvas,
                              (50+x*5, 50+y*5),
                              (54+x*5, 54+y*5),
                              (b, g, r),
                              -1)
        cv2.rectangle(canvas,
                      (0, 0),
                      (1024, 50),
                      (0, 0, 0),
                      -1)
        cv2.putText(
            canvas,  # numpy array on which text is written
            d,  # text
            (50, 35),  # position at which writing has to start
            cv2.FONT_HERSHEY_SIMPLEX,  # font family
            1,  # font size
            (196, 196, 196),  # font color
            3)  # font stroke
        cv2.imshow('Technical analysis', canvas)
        cv2.waitKey(1)
        time.sleep(0.03)



if __name__ == '__main__':
    instrument = 'SPX500_USD'
    main(account, instrument)
