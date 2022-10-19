#!/usr/bin/python
#
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
""" Module to generate Functest reporting for gitlab pages """

import argparse
import datetime
import logging
import json
import os
import re
import requests
import lxml
from bs4 import BeautifulSoup # sudo apt-get install python3-bs4 if pip doesn't work
from anytree import Node, RenderTree
import jinja2

PROXY = {}
# PROXY = {'http': 'socks5h://127.0.0.1:8080',
#          'https': 'socks5h://127.0.0.1:8080'}

MONTHS = []
DAYS = []
BASE_URL ="https://logs.onap.org/onap-integration/daily/"
END_URL = "daily-scores.json"


PARSER = argparse.ArgumentParser()
PARSER.add_argument('-v', '--onap_version', help='onap version',default='master')

ARGS = PARSER.parse_args()

ci_version = "onap_daily_pod4_" + ARGS.onap_version + "/"

# Logger
logging.basicConfig()
LOGGER = logging.getLogger("CI Timeview")
LOGGER.setLevel("INFO")

def get_months(url):
    """load and parse list of months"""
    local_months = []
    response_months = requests.get(url, proxies=PROXY)
    soup = BeautifulSoup(response_months.text ,"lxml")

    for link in soup.find_all('a'):
        pattern = bool(re.match("[0-9]{4}-[0-9]{2}", link.contents[0]))
        if pattern:
            local_months.append(link.contents[0])
    LOGGER.debug(local_months)
    return local_months

def get_days(url):
    """load and parse list of days"""
    local_days = []
    response_days = requests.get(url, proxies=PROXY)
    soup = BeautifulSoup(response_days.text ,"lxml")

    for link in soup.find_all('a'):
        pattern = bool(re.match("[0-9]{2}_[0-9]{2}-[0-9]{2}", link.contents[0]))
        if pattern:
            local_days.append(link.contents[0])
    LOGGER.debug(local_days)
    return local_days

def get_results_of_a_day(url, month, day):
    """ get the daily scores for a day"""
    daily_score = {}
    response_day = requests.get(url + month + day + END_URL, proxies=PROXY)
    if response_day.status_code != 200:
        LOGGER.debug(url + month +  day + END_URL + " : does not exist")
    else:
        parsed_month = re.match("[0-9]{4}-[0-9]{2}", month).group()
        parsed_day = re.match("[0-9]{2}", day).group()
        daily_score = { "date": parsed_month + "-" + parsed_day }
        json_res = json.loads(response_day.content)
        for res in json_res:
            # ugly workaround as one of the key contains a space
            # which is painful for processing
            daily_score.update({ res['tier'].replace(" ","-"): res['score'] })
    return daily_score

# ------------------------------------------------------------------------------
LOGGER.info("---------------------------------------")
LOGGER.info("Look for results for %s", ci_version)
url = BASE_URL + ci_version
months = get_months(url)
# NOTE the 2: has been set to exclude old results for which we do not have the
# json. Once applied, the number shall be 6 to consider the last 6 months
filtered_months = months[-3:]

LOGGER.info(filtered_months)
data_scores = []
for month in filtered_months:
    for day in get_days(url + "/" + month):
        if get_results_of_a_day(url, month, day) != {}:
            data_scores.append(
                get_results_of_a_day(url, month, day))

# check if local results daily-scores.json can be found
# if a result already exists for this day do nothing, else add it
if os.path.isfile('./daily-scores.json'):
    my_day = datetime.datetime.today()
    local_day = (str(my_day.year) + "-" + str(my_day.month) + "-" +
                 str(my_day.day))
    LOGGER.info("Local results found")
    with open('./daily-scores.json') as json_file:
        local_res = json.load(json_file)
    daily_score = {'date': local_day}
    for res in local_res:
        daily_score[res['tier'].replace(" ","-")] = res['score']
    data_scores.append(daily_score)

LOGGER.info("---------------------------------------")
LOGGER.info("Generate the page %s", ci_version)

TEMPLATELOADER = jinja2.FileSystemLoader(".")
TEMPLATEENV = jinja2.Environment(
    loader=TEMPLATELOADER, autoescape=True)
TEMPLATE_FILE = ("./template/index-stability-tmpl.html")
TEMPLATE = TEMPLATEENV.get_template(TEMPLATE_FILE)
OUTPUT_TEXT = TEMPLATE.render(
    data=data_scores,
    lab_owner=ci_version[:-1],
    lab_version=ARGS.onap_version)
FILENAME = "./index-stability.html"
with open(FILENAME, "w+") as fh:
    fh.write(OUTPUT_TEXT)
