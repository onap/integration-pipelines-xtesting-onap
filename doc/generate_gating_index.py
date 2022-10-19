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

import jinja2

# Logger
logging.basicConfig()
LOGGER = logging.getLogger("Gating-Index")
LOGGER.setLevel("INFO")
LOGGER.setLevel("DEBUG")

LOGGER.info("generate Xtesting gating index page")

REPORTINGDATE = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

PARSER = argparse.ArgumentParser()
PARSER.add_argument('-l', '--list', help='patchset list')
ARGS = PARSER.parse_args()

PATCHSET_LIST = []

# we expect an argument as follows: 12345-1,45678-99,65432-42
if ARGS.list is not None:
    PATCHSET_LIST = ARGS.list.split(",")

TEMPLATELOADER = jinja2.FileSystemLoader(".")
TEMPLATEENV = jinja2.Environment(
    loader=TEMPLATELOADER, autoescape=True)
TEMPLATE_FILE = ("./template/index-gating-tmpl.html")
TEMPLATE = TEMPLATEENV.get_template(TEMPLATE_FILE)
OUTPUT_TEXT = TEMPLATE.render(
    patchsets=PATCHSET_LIST,
    date=REPORTINGDATE)

FILENAME = "./index-gating.html"

with open(FILENAME, "w+") as fh:
    fh.write(OUTPUT_TEXT)
