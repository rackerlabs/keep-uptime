#!/usr/bin/env python

import ConfigParser
import argparse
import json
import logging
import os
import signal
import sys
import time

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from rackspace import connection
from statsd import StatsClient


def timer(username, api_key, region, statsd_server):
    conn = connection.Connection(username=username, api_key=api_key,
                                 region=region)
    statsd = StatsClient(host=statsd_server)

    start = time.time()
    secret = conn.key_manager.create_secret(name="Uptime Test", payload="Test",
            payload_content_type="text/plain")

    timer = int((time.time() - start) * 1000)
    statsd.timing('uptime.{}'.format(region.lower()), timer)

    conn.key_manager.delete_secret(secret, ignore_missing=False)


def main():
    log_handler = logging.StreamHandler(sys.stdout)
    logging.getLogger('apscheduler.executors.default').addHandler(log_handler)

    parser = argparse.ArgumentParser(description='Get uptime metrics')
    parser.add_argument('-c', '--config', help='Path to config file',
                        default='etc/uptime.conf')
    args = parser.parse_args()
    config_file = args.config

    config = ConfigParser.ConfigParser()
    try:
        config.read(config_file)
    except IOError:
        print('Config file {} does not exist'.format(config_file))
        sys.exit(1)

    username = config.get('DEFAULT', 'username')
    api_key = config.get('DEFAULT', 'api_key')
    interval = int(config.get('DEFAULT', 'interval'))
    statsd_server = config.get('DEFAULT', 'statsd_server')
    regions = json.loads(config.get('DEFAULT', 'regions'))

    scheduler = BackgroundScheduler()
    for region in regions:
        scheduler.add_job(timer, 'interval', [username, api_key, region,
                          statsd_server], seconds=interval, name=region)

    scheduler.start()
    signal.signal(signal.SIGTERM, sys.exit)
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            scheduler.shutdown()
            sys.exit(0)


if __name__ == '__main__':
    main()

