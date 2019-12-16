import time
import re
from typing import List, Union, Tuple
from .osm_params import *
from ...common_tools.auxiliary_functions import reporter


def placegetter(place: str) -> Tuple[Union[None, List[float]], list]:
    """
    Send a request to the Nominatim API via HTTP GET and return a geometry polygon
    for the region we are querying

    Parameters
    ----------
    place : str
        Name of the place we want to download a network for

    Adapted from http://www.github.com/gboeing/osmnx
    """

    params = {'q': place, 'format': 'json'}

    report = []
    pause_duration = 1
    timeout = 30
    error_pause_duration = 180

    # prepare the Nominatim API URL
    url = nominatim_endpoint.rstrip('/') + '/search'
    prepared_url = requests.Request('GET', url, params=params).prepare().url
    # Pause, then request it
    report.append(reporter('Pausing {:,.2f} seconds before making API GET request'.format(pause_duration)))
    time.sleep(pause_duration)
    start_time = time.time()
    report.append('Requesting {} with timeout={}'.format(prepared_url, timeout))
    # response = requests.get(url, params=place, timeout=timeout, headers=http_headers)
    response = requests.get(url, params=params, timeout=timeout, headers=http_headers)

    # get the response size and the domain, log result
    size_kb = len(response.content) / 1000.
    domain = re.findall(r'(?s)//(.*?)/', url)[0]
    report.append(
        reporter('Downloaded {:,.1f}KB from {} in {:,.2f} seconds'.format(size_kb, domain, time.time() - start_time)))

    response_json = None
    bbox = None
    for attempts in range(max_attempts):
        report.append(reporter('Attempt: {}'.format(attempts)))
        if response.status_code != 200:
            report.append(reporter(
                'Server at {} returned status code {} and no JSON data. Re-trying request in {:.2f} seconds.'.format(
                    domain, response.status_code, error_pause_duration)))

        if response.status_code in [429, 504]:
            # SEND MESSAGE
            time.sleep(error_pause_duration)
            continue
        elif response.status_code == 200:
            response_json = response.json()
            report.append(reporter('COMPLETE QUERY RESPONSE FOR PLACE:', 1))
            report.append(reporter(str(response_json), 1))
            if len(response_json):
                bbox = [float(x) for x in response_json[0]['boundingbox']]
                bbox = [bbox[2], bbox[0], bbox[3], bbox[1]]
                report.append(reporter('PLACE FOUND:{}'.format(response_json[0]['display_name']), 1))
            return (bbox, report)
        else:
            response_json = None
            bbox = None

        if attempts == max_attempts - 1:
            report.append(reporter('Maximum download attempts was reached without success. '
                                   'Please wait a few minutes and try again'))
        else:
            report.append(reporter('We got error {} for place query. Error not currently well handled by the software'))

        return (None, report)
