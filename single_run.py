import numpy as np
import plotly.graph_objects as go
from dateutil import parser
from collections import namedtuple
from plotly.subplots import make_subplots

import inc.oanda as broker
import inc.tradesim as tradesim


OANDA_account = namedtuple('OANDA_account', 'key account env host')
account = OANDA_account('????????????????????????????????-????????????????????????????????',
                        '???-???-???????-???',
                        'demo',
                        'api-fxpractice.oanda.com')



def main(account, instrument):
    bracket_start = parser.parse('12-13-2020 12:00 UTC')
    bracket_stop = parser.parse('12-19-2020 12:00 UTC')

    data = broker.fetch_m1(account, instrument, start_dt=bracket_start, stop_dt=bracket_stop)
    data = broker.raw_candles_to_dataframe(data)

    # To draw candlesticks and EMA's
    slow = data['close_900_ema']
    fast = data['close_600_ema']

    deltas, positions, spread = tradesim.ma_crossover_simple(np.array(data['bid']),
                                                      np.array(data['ask']),
                                                      np.array(slow),
                                                      np.array(fast),
                                                      tradesim.BOTH)

    candlesticks = go.Candlestick(x=data['time'],
                                  open=data['open'],
                                  high=data['high'],
                                  low=data['low'],
                                  close=data['close'],
                                  name='OHLC')

    ema_slow = go.Scatter(x=data['time'],
                          y=slow,
                          name='Slow EMA')

    ema_fast = go.Scatter(x=data['time'],
                          y=fast,
                          name='Fast EMA')

    delta_g = go.Scatter(x=data['time'],
                         y=deltas,
                         name='NAV')

    position_g = go.Scatter(x=data['time'],
                            y=positions,
                            name='NAV')

    fig = make_subplots(rows=3, cols=1, row_heights=[0.40, 0.40, 0.20], shared_xaxes=True)

    fig.add_trace(candlesticks, row=1, col=1)
    fig.add_trace(ema_slow, row=1, col=1)
    fig.add_trace(ema_fast, row=1, col=1)
    fig.add_trace(delta_g, row=2, col=1)
    fig.add_trace(position_g, row=3, col=1)

    fig.update_layout(xaxis_rangeslider_visible=False)
    fig.show()


if __name__ == '__main__':
    instrument = 'SPX500_USD'
    main(account, instrument)