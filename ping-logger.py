#!/usr/bin/env python3

import os
import requests
import shutil
import statistics
import subprocess
import time
import yaml


def post_to_influxdb():
    """Formats fping output and posts it to an InfluxDB server."""

    points = []

    # An example fping output line looks like this:
    #
    # example.com : 3.56 1.88 - - - 1.18 1.28 1.39 4.67 1.27
    for line in fping_output_lines:
        host = line.split(':')[0].rstrip()
        responses = line.split(':')[1].lstrip().split(' ')
        pings = [float(response) for response in responses if response != '-']

        if len(pings) == 0:
            continue

        minimum = min(pings)
        average = "{0:.2f}".format(statistics.mean(pings))
        maximum = max(pings)
        standard_deviation = "{0:.2f}".format(statistics.pstdev(pings))
        loss = responses.count("-") / config['ping_count']

        tags = [
            'ping',
            'src=' + config['src_host_name'],
            'dest=' + host
        ]
        fields = [
            'min=' + str(minimum),
            'avg=' + str(average),
            'max=' + str(maximum),
            'sd=' + str(standard_deviation),
            'loss=' + str(loss)
        ]

        points.append(','.join(tags) + ' ' + ','.join(fields)
                      + ' ' + str(timestamp))

    requests.post(
        config['influxdb_connection']['server']
        + '/write?db='
        + config['influxdb_connection']['database']
        + '&precision=s',
        auth=(config['influxdb_connection']['username'],
              config['influxdb_connection']['password']),
        data='\n'.join(points)
    )


# Load the configuration.

config = yaml.safe_load(open(os.getenv('HOME')
                             + '/.config/ping-logger/config.yaml'))
concatenated_hosts = '\n'.join(config['dest_hosts'])

# Now run the test!

timestamp = int(time.time())
fping_run = subprocess.run([shutil.which('fping'), '-C',
                           str(config['ping_count']), '-q', '-R'],
                           input=concatenated_hosts, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True)
fping_output_lines = fping_run.stdout.splitlines()
post_to_influxdb()
