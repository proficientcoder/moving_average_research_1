import os
import ujson
import logging
import requests
import datetime
import stockstats
import dateutil.parser as parser
import pandas as pd

from filelock import Timeout, FileLock

import inc.support as support


logging.basicConfig(level=logging.WARN)
http_session = requests.Session()


def request(account, endpoint, params, data, gp):
    if type(endpoint) is not str:
        raise ValueError

    if type(params) is not dict:
        raise ValueError

    if type(data) is not dict:
        raise ValueError

    headers = {'Content-Type': 'application/json',
               'Accept-Encoding': 'deflate, gzip',
               'Authorization': f'Bearer {account.key}'}
    url = "https://" + account.host + endpoint
    print(f'Retreiving {url}')

    if gp == 'GET':
        response = http_session.get(url, headers=headers, params=params, data=ujson.dumps(data))
    if gp == 'POST':
        response = http_session.post(url, headers=headers, params=params, data=ujson.dumps(data))

    s = response.content.decode("UTF-8")
    return ujson.loads(s)


def instruments(account):
    params = dict()
    data = dict()

    instruments = request(account, f'/v3/accounts/{account.account}/instruments', params, data, 'GET')

    return instruments['instruments']


def account(account):
    params = dict()
    data = dict()

    a = request(account, f'/v3/accounts/{account.account}', params, data, 'GET')

    return a['account']


def _trim(data, start_dt, stop_dt):
    if start_dt:
        while parser.parse(data[0]['time']) < start_dt:
            data.pop(0)
            if len(data) == 0:
                break

    if stop_dt:
        while parser.parse(data[-1]['time']) > stop_dt:
            data.pop(-1)
            if len(data) == 0:
                break

    return data



def fetch_s5(account, instrument, start_dt, stop_dt=None):
    data = _fetch(account, instrument, start_dt, 4320 * 5, 'S5', stop_dt)
    data = _trim(data, start_dt, stop_dt)
    return data


def fetch_m1(account, instrument, start_dt, stop_dt=None):
    data = _fetch(account, instrument, start_dt, 4320 * 60, 'M1', stop_dt)
    data = _trim(data, start_dt, stop_dt)
    return data


def _fetch(account, instrument, start_dt, seg_size, interval, stop_dt):

    # Folders
    #fn_cache_dir = os.path.join(os.path.abspath(os.sep), 'ticker-cache')
    fn_cache_dir = 'ticker-cache'
    fn_cache_ticker_dir = os.path.join(fn_cache_dir, f'{interval}_{instrument}')

    # Create folders
    if not os.path.exists(fn_cache_dir):
        os.mkdir(fn_cache_dir)

    if not os.path.exists(fn_cache_ticker_dir):
        os.mkdir(fn_cache_ticker_dir)

    # Lockfile
    lockfile = os.path.join(fn_cache_ticker_dir, 'ticker.lock')
    lock = FileLock(lockfile, timeout=60)

    if stop_dt == None:
        stop_dt = datetime.datetime.now(datetime.timezone.utc)

    first_seg = int(start_dt.timestamp() / seg_size)
    last_seg = int(stop_dt.timestamp() / seg_size)

    my_block = list()
    for i in range(first_seg, last_seg+1):
        fn = os.path.join(fn_cache_ticker_dir, str(i))

        start_dt = datetime.datetime.utcfromtimestamp((i+0) * seg_size)
        start = start_dt.isoformat() + 'Z'
        stop_dt = datetime.datetime.utcfromtimestamp((i+1) * seg_size)
        stop = stop_dt.isoformat() + 'Z'

        s = int(datetime.datetime.now(datetime.timezone.utc).timestamp() / seg_size)
        is_open_segment = (i == s)

        if not is_open_segment:
            if not os.path.exists(fn):
                params = {'granularity': interval,
                          'price': 'BAM',
                          'from': start,
                          'to': stop}
                data = {}
                rows = request(account, f'/v3/instruments/{instrument}/candles', params, data, 'GET')

                if 'candles' in rows:
                    rows = rows['candles']
                    my_block = my_block + rows
                    with lock:
                        with open(fn, 'w') as h:
                            ujson.dump(rows, h, indent=4)

            else:
                # Open file and add to block
                with open(fn, 'r') as h:
                    rows = ujson.load(h)
                my_block = my_block + rows

        if is_open_segment:
            params = {'granularity': interval,
                      'price': 'BAM',
                      'from': start,
                      'count': 5000}
            data = {}
            rows = request(account, f'/v3/instruments/{instrument}/candles', params, data, 'GET')
            if 'candles' in rows:
                rows = rows['candles']
                my_block = my_block + rows

    return my_block


def raw_candles_to_dict(raw):
    block_dict = list()
    for r in raw:
        b = dict()
        b['time'] = support.ztime_to_time(r['time'])
        b['bid'] = float(r['bid']['c'])
        b['ask'] = float(r['ask']['c'])
        b['open'] = float(r['mid']['o'])
        b['high'] = float(r['mid']['h'])
        b['low'] = float(r['mid']['l'])
        b['close'] = float(r['mid']['c'])
        b['volume'] = int(r['volume'])

        block_dict.append(b)

    return block_dict


def raw_candles_to_dataframe(raw):
    block_dict = raw_candles_to_dict(raw)
    block_dataframe = pd.DataFrame.from_dict(block_dict)
    block_dataframe = stockstats.StockDataFrame.retype(block_dataframe)

    return block_dataframe


def tradeable(account, instrument):
    instruments = request(account, f'/v3/accounts/{account.account}/pricing', {'instruments': instrument}, {}, 'GET')
    try:
        for p in instruments['prices']:
            if p['instrument'] == instrument:
                return p['tradeable']
    except:
        print(instruments)
        return False
        


def get_open_positions(account):
    all_positions = request(account, f'/v3/accounts/{account.account}/openPositions', {}, {}, 'GET')['positions']
    open_positions = dict()

    for p in all_positions:
        name = p['instrument']
        if name not in open_positions:
            open_positions[name] = 0
        open_positions[name] += int(p['long']['units'])
        open_positions[name] += int(p['short']['units'])

    return open_positions


def update_position(account, new_position, instrument):
    if not tradeable(account, instrument):
        print(f'Market is closed for {instrument}')
        return False

    all_positions = request(account, f'/v3/accounts/{account.account}/openPositions', {}, {}, 'GET')['positions']

    # Match instrument in list and add longs+short to total
    current_position = 0
    for p in all_positions:
        name = p['instrument']
        if name == instrument:
            current_position += int(p['long']['units'])
            current_position += int(p['short']['units'])

    print(f'Current position for {instrument} is {current_position}')

    # Correct the difference
    if current_position != new_position:
        difference = new_position - current_position
        print(f'A trade for {instrument} with size of {difference} needs to be made')

        data = {'order': {'instrument': instrument,
                          'units': difference,
                          'type': 'MARKET',
                          'positionFill': 'DEFAULT'}}

        response = request(account, f'/v3/accounts/{account.account}/orders', {}, data, 'POST')
        print(f'RESPONSE from server: {response}')
        return True
    else:
        return True
