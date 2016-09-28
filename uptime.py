#!/usr/bin/env python

import ConfigParser
import argparse
import json
import logging
import os
import requests
import signal
import sys
import time

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from statsd import StatsClient


def timer(username, api_key, region, statsd_server):
    identity_data = {
        'auth': {
            'RAX-KSKEY:apiKeyCredentials': {
                'username': username,
                'apiKey': api_key
            }
        }
    }
    identity_hdr = {'content-type': 'application/json'}

    identity_resp = requests.post(
            'https://identity.api.rackspacecloud.com/v2.0/tokens',
            data=json.dumps(identity_data),
            headers=identity_hdr)

    identity_resp.raise_for_status()
    identity = identity_resp.json()

    token = identity['access']['token']['id']
    for catalog_item in identity['access']['serviceCatalog']:
        if catalog_item['name'] == 'cloudKeep':
            for endpoint in catalog_item['endpoints']:
                if endpoint['region'] == region.upper():
                    endpoint_url = endpoint['publicURL']

    start = time.time()

    secret_data = {
        'name': 'Uptime Test',
        'payload': 'Uptime Test Payload',
        'payload_content_type': 'text/plain'
    }
    secret_hdr = {
        'content-type': 'application/json',
        'x-auth-token': token
    }
    secret_resp = requests.post('{}/v1/secrets'.format(endpoint_url),
                                data=json.dumps(secret_data),
                                headers=secret_hdr)
    secret_resp.raise_for_status()
    secret = secret_resp.json()

    delete_resp = requests.delete(secret['secret_ref'], headers=secret_hdr)
    delete_resp.raise_for_status()

    timer = int((time.time() - start) * 1000)
    statsd = StatsClient(host=statsd_server)
    statsd.timing('uptime.{}'.format(region.lower()), timer)


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

