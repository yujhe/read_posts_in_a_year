#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import requests
import json
from datetime import datetime, date
import logging
import webbrowser
import time
import pandas as pd

consumer_key = '83388-b2ec4359911b6b6043827972'  # can be replaced with your consumer key
redirect_uri = 'https://app.getpocket.com/'


def display_monthly_read_statistic(year, df, detail, file=None):
    if file:
        logging.info('export your read statistics to file: {}'.format(file))
        f = open(file, 'w')
    else:
        f = None

    if df.empty:
        print('0 read post in {}'.format(year), file=f)
    else:
        grouped = df.groupby('month_read')

        print('# Read Posts in {}'.format(year), file=f)
        print('| Month   | Read |\n| ------- | ---- |', file=f)
        for month, count in grouped.size().iteritems():
            print('| {:7s} | {:4d} |'.format(month, count), file=f)

        if detail:
            print('\n', file=f)
            for month, group in grouped:
                sorted = group.sort_values(['is_article', 'date_read', 'resolved_title'], ascending=[False, True, True])
                print('## {}'.format(month), file=f)
                for idx, row in sorted.iterrows():
                    post_type = '(POST)' if row.is_article == '1' else '(VIDEO)' if row.has_video == '2' else '(UN)'
                    print('* {type:7} {date} {title}: {url}'.format(
                        date=row.date_read, type=post_type,
                        title=row.resolved_title, url=row.resolved_url), file=f)
                print('', file=f)

    if file:
        f.close()


def retrieve_read_posts_in_a_year(token, year):
    logging.info('retrieve archived posts from Pocket server')

    retrieve_uri = 'https://getpocket.com/v3/get'
    headers = {'Content-Type': 'application/json; charset=UTF-8', 'X-Accept': 'application/json'}
    payload = {'consumer_key': consumer_key,
               'access_token': token,
               'state': 'archive',
               'sort': 'oldest',
               'detailType': 'complete',
               'since': int(datetime(year, 1, 1).timestamp())
               }
    response = requests.get(retrieve_uri, headers=headers, data=json.dumps(payload))
    df = pd.DataFrame(response.json()['list']).transpose()

    columns = ['month_read', 'date_read', 'resolved_title', 'resolved_url', 'is_article', 'has_video', 'tags']
    if df.empty:
        return pd.DataFrame(columns=columns)

    next_year = datetime(year + 1, 1, 1)
    df = df[df.time_read.astype(int) < next_year.timestamp()]  # filter read posts in a year

    month_read = df.time_read.astype(int).apply(lambda t: datetime.fromtimestamp(t).date().strftime('%Y-%m'))
    date_read = df.time_read.astype(int).apply(lambda t: datetime.fromtimestamp(t).date().strftime('%Y/%m/%d'))

    df = df.assign(date_read=date_read.values, month_read=month_read.values)

    return df[columns]


def obtain_user_access_token(token):
    logging.info('obtain user access token from Pocket server')

    user_auth_uri = 'https://getpocket.com/v3/oauth/authorize'
    headers = {'Content-Type': 'application/json; charset=UTF-8', 'X-Accept': 'application/json'}
    payload = {'consumer_key': consumer_key, 'code': token}
    response = requests.post(user_auth_uri, headers=headers, data=json.dumps(payload))

    if response.ok:
        return response.json()['access_token']
    else:
        raise ValueError('obtain user access token from Pocket failed, due to {}'.format(response.headers))


def do_authorization(init, token):
    logging.info('authorize this app to access your Pocket list')

    auth_uri = 'https://getpocket.com/auth/authorize'
    webbrowser.open('{}?request_token={}&redirect_uri={}'.format(auth_uri, token, redirect_uri))
    if init:
        input('press <ENTER> after finish authorization in browser')
    else:
        time.sleep(3)


def obtain_request_token():
    logging.info('obtain request token from Pocket server')

    request_uri = 'https://getpocket.com/v3/oauth/request'
    headers = {'Content-Type': 'application/json; charset=UTF-8', 'X-Accept': 'application/json'}
    payload = {'consumer_key': consumer_key, 'redirect_uri': redirect_uri}
    response = requests.post(request_uri, headers=headers, data=json.dumps(payload))

    if response.ok:
        return response.json()['code']
    else:
        raise ValueError('obtain request token from Pocket failed, due to {}'.format(response.headers))


def parse_args():
    parser = argparse.ArgumentParser(description='show your read posts in a year from Pocket')
    parser.add_argument('--init', action='store_true', help='initial for 1st time authorization')
    parser.add_argument('-y', '--year', type=int, default=date.today().year, help='the reading status of this year')
    parser.add_argument('--detail', action='store_true', help='show read posts in detail')
    parser.add_argument('--export', type=str, help='export your read statistics to file')

    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    args = parse_args()
    file = args.export if args.export else '{}_read_posts.md'.format(args.year)

    request_token = obtain_request_token()
    do_authorization(args.init, request_token)
    user_access_token = obtain_user_access_token(request_token)
    df = retrieve_read_posts_in_a_year(user_access_token, args.year)
    display_monthly_read_statistic(args.year, df, args.detail)  # display to console
    display_monthly_read_statistic(args.year, df, args.detail, file)  # output to file
