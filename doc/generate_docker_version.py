#!/usr/bin/python
#
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
'''Docker version comparison generator.'''

import argparse
import logging
import json
import re
from collections import Counter
from dataclasses import dataclass
import os
import requests
from bs4 import BeautifulSoup  # sudo apt-get install python3-bs4 if pip doesn't work
from deepdiff import DeepDiff
from jinja2 import Environment, FileSystemLoader, select_autoescape

PROXY = {}
# PROXY = {'http': 'socks5h://127.0.0.1:8080',
#          'https': 'socks5h://127.0.0.1:8080'}


BASE_URL = "https://logs.onap.org/onap-integration/daily/"
ONAP_VERSION = 'master'
component_versions = {}
versions_to_be_compared_with_master = ['jakarta', 'istanbul', 'honolulu_MR1', 'honolulu', 'guilin_MR1']
VERSION_URL = []
END_URL = "infrastructure-healthcheck/k8s/kubernetes-status/onap_versions.json"

# first date where file is present for each version
ONAP_RELEASE_DATE = {
    "jakarta": "onap-daily-dt-oom-jakarta/2022-07/19_03-53/",
    "istanbul": "onap_daily_pod4_istanbul/2021-11/15_03-55/",
    "honolulu": "onap_daily_pod4_honolulu/2021-05/28_01-00/",
    "honolulu_MR1": "onap_daily_pod4_honolulu/2021-08/12_20-15/",
    "guilin_MR1": "onap_daily_pod4_guilin/2021-05/27_03-23/"
}

# Logger
logging.basicConfig()
LOGGER = logging.getLogger("Docker-Version-Status")
LOGGER.setLevel("INFO")

# Arg
PARSER = argparse.ArgumentParser()
PARSER.add_argument('-t', '--test', action='store_true' )
# PARSER.add_argument('-t', '--test', default=True, type=bool, help='Execute with test dataset')
ARGS = PARSER.parse_args()

DATA_VERSIONS = []

@dataclass
class ComponentVersion:
    """A component version."""
    component: str
    container: str
    image: str
    current_version: str
    other_version: {}
    status: int

# ***********************************************************************
# functions
# ***********************************************************************
def get_months(url):
    """Load and parse list of months"""
    months = []
    response_months = requests.get(url, proxies=PROXY)
    soup = BeautifulSoup(response_months.text, "lxml")

    for link in soup.find_all('a'):
        pattern = bool(re.match("[0-9]{4}-[0-9]{2}", link.contents[0]))
        if pattern:
            months.append(link.contents[0])
    return months

def get_days(url):
    """Load and parse list of days"""
    days = []
    response_days = requests.get(url, proxies=PROXY)
    soup = BeautifulSoup(response_days.text, "lxml")

    for link in soup.find_all('a'):
        pattern = bool(
            re.match("[0-9]{2}_[0-9]{2}-[0-9]{2}", link.contents[0]))
        if pattern:
            days.append(link.contents[0])
    return days

def get_diff_index(change):
    """Search Index of the Diff table to get the container related to the detected diff."""
    local_index = re.findall(r"\[([0-9]+)\]", change)
    return int(local_index[0])

def is_it_a_simple_version_change(change, delta_values_changed):
    """Detect if it is a simple version change or a subtitution."""
    # retrieve the change index
    change_index = get_diff_index(change)
    # count the number of occurence
    # if 1 => simplie version change
    return str(delta_values_changed).count("root[" + str(change_index) + "]") < 2

def get_component_status(container, delta_versions, version_master, other_version):
    """Get component status."""
    LOGGER.debug(container)
    container_status = "unchanged"
    # Look in values_changed
    for change_type in ['values_changed', 'iterable_item_added', 'iterable_item_removed']:
        # We test the change type as they may not occur, or only 1 type is possible
        if change_type in delta_versions:
            # Dive into the change found
            for change in delta_versions[change_type]:
                if change_type == 'values_changed':
                    # 2 cases
                    # - a simple version change for the same component (only version)
                    # in this case only the other_version shall be changed
                    # - a substitution (version, container, image,...)
                    # in this case a new component must be added and another removed
                    # it may be a little bit misleading
                    # as it could courrespond to an offset (not really a new component)
                    if is_it_a_simple_version_change(change, delta_versions[change_type]):
                        # simple replacement case
                        ## change_index = int(change[5:-12])
                        change_index = get_diff_index(change)
                        if container == other_version[change_index]['container']:
                            LOGGER.debug("Component version change: %s",
                            other_version[change_index]['container'])
                            container_status = "version_changed"
                    else:
                        if 'container' in change:
                            ## change_index = int(change[5:-14])
                            change_index = get_diff_index(change)
                            # substitution case
                            for substitution_change in delta_versions['values_changed']:
                                if str(change_index) in substitution_change:
                                    LOGGER.debug("From %s to %s",
                                        delta_versions['values_changed'][substitution_change]['old_value'],
                                        delta_versions['values_changed'][substitution_change]['new_value'])
                                    if container == delta_versions['values_changed'][substitution_change]['old_value']:
                                        container_status = "component_removed"
                                    if container == delta_versions['values_changed'][substitution_change]['new_value']:
                                        container_status = "component_added"
                elif change_type == 'iterable_item_added':
                    ## change_index = int(change[5:-1])
                    change_index = get_diff_index(change)
                    LOGGER.debug(
                        "New component added: %s", version_master[change_index]['container'])
                    if container == version_master[change_index]['container']:
                        container_status = "component_added"
                elif change_type == 'iterable_item_removed':
                    ## change_index = int(change[5:-1])
                    change_index = get_diff_index(change)
                    LOGGER.debug(
                        "Component removed: %s", other_version[change_index]['container'])
                    if container == other_version[change_index]['container']:
                        container_status = "component_removed"
    return container_status

def get_old_version_component(container, component_versions):
    """Retrieve the version of an old container."""
    container_version = "unknown"
    for component in component_versions:
        if component['container'] == container:
            return component['version']
    return container_version

def get_removed_container_list(delta_versions, component_versions, master_container):
    """Retrieve the removed containers."""
    removed_container_list = []
    # Look in the removed list
    try:
        for change in delta_versions['iterable_item_removed']:
            removed_container_list.append(component_versions[get_diff_index(change)])
    except KeyError:
        LOGGER.info("No Item in the removed section, look at the possible substitution")

    # Consider the subsitution case
    for delta in delta_versions['values_changed']:
        if "container" in delta:
            index_container = get_diff_index(delta)
            removed_container_list.append(component_versions[index_container])
    return removed_container_list

def get_data_version_container_index(container, dataset):
    """Get the index of a container from a dataset."""
    for data in dataset:
        if data.container == container:
            return dataset.index(data)
    return -1

def get_json_master_components():
    """Retrieve the json master description from LF backend."""
    local_url = BASE_URL + "onap_daily_pod4_master/"
    months_with_results = get_months(local_url)
    LOGGER.debug("months_with_results: %s", months_with_results)
    month =  months_with_results[-1]

    for day in get_days(local_url + month):
        response_day = requests.get(local_url + month + day + END_URL, proxies=PROXY)
        if response_day.status_code == 404:
            LOGGER.debug("%s : does not exist", local_url + month + day + END_URL)
        else:
            version_infos = {"month": month,
                             "day": day,
                             "file": local_url + month + day + END_URL}
            VERSION_URL.append(version_infos)

    # load latest version json from LFN backend
    version_file = VERSION_URL[-1]["file"]
    LOGGER.debug(version_file)
    # retrieve the file
    response_latest = requests.get(version_file, proxies=PROXY)
    return json.loads(response_latest.text)

def get_json_version_components(version):
    """Retrieve the versions of the component from LF Backend."""
    local_url = BASE_URL + ONAP_RELEASE_DATE[version] + END_URL
    local_response = requests.get(local_url, proxies=PROXY)
    return json.loads(local_response.text)

def compare_func(x, y, level=None):
    try:
        res = x["container"] == y["container"] and \
            x["component"] == y["component"]
        return res
    except Exception:
        raise CannotCompare()


LOGGER.info("*********************************************************************")
LOGGER.info("*********************************************************************")
LOGGER.info("*******************        Retrieve Raw Data          ***************")
LOGGER.info("*********************************************************************")
LOGGER.info("*********************************************************************")
MONTHS = ['2021-08/']
LOGGER.info("Retrieve the Raw Data.")

# Retrieve the last available version file
# - we fist list the url of all the daily results on the given version
# - we check that the onap_versions.json exist
# - we take the last existing one VERSION_URL[-1]
# - we download this particular file


# Master is the ref
if ARGS.test:
    with open('./artifacts/versions/test_master.json') as json_file:
        LATEST_VERSION = json.load(json_file)
else:
    LATEST_VERSION = get_json_master_components()
CLEAN_LATEST_VERSION = [k for j, k in enumerate(
    LATEST_VERSION) if k not in LATEST_VERSION[j + 1:]]
SORTED_MASTER = sorted(CLEAN_LATEST_VERSION, key=lambda k: k['container'])
LOGGER.info("Versions of the latest run ================> %s", SORTED_MASTER)

for version in versions_to_be_compared_with_master:
    # Retrieve versions of official release (release or maintenance release)
    LOCAL_PATH = "./artifacts/versions/test_" + version + ".json"
    if ARGS.test:
        with open(LOCAL_PATH) as json_file:
            local_json_file = json.load(json_file)
    else:
        local_json_file = get_json_version_components(version)

    # remove duplicates
    local_clean = [k for j, k in enumerate(
        local_json_file) if k not in local_json_file[j + 1:]]
    # sort
    component_versions[version] = sorted(
        local_clean, key=lambda k: k['container'])
    LOGGER.debug("Versions of the release run %s", version)
    LOGGER.debug("================> %s", component_versions[version])

# # Post processing on the loaded versions
# # we got
# # - the last version
# # - the Honolulu versions
# # - the Guilin MR versions
# # we need first to cleanup (avoid duplicate)
# # then we need to build the object for the jinja template

LOGGER.info("*********************************************************************")
LOGGER.info("*********************************************************************")
LOGGER.info("*******************        Process the Data           ***************")
LOGGER.info("*********************************************************************")
LOGGER.info("*********************************************************************")

NB_ITERATION_DATASET = 0
# we compare Master with a bunch of official release or maintenance releases
for version in versions_to_be_compared_with_master:
    LOGGER.info("----------------------------------------------------")
    LOGGER.info("----------------------------------------------------")
    LOGGER.info("-----Comparison Master versus %s --------", version)
    LOGGER.info("----------------------------------------------------")
    LOGGER.info("----------------------------------------------------")

    # we use DeeDiff to get the difference between the 2 json list
    delta_versions = DeepDiff(
        component_versions[version],
        SORTED_MASTER,
        ignore_order=True,
        iterable_compare_func=compare_func,
        cutoff_distance_for_pairs=0.1,
        cutoff_intersection_for_pairs=1.0,
        get_deep_distance=True)
    LOGGER.info("Delta between Master and %s", version)
    LOGGER.info("Delta = %s", delta_versions)

    # Manage containers found in Master
    for master_component in SORTED_MASTER:
        # test if container mentioned in delta
        # possible cases
        # * values_changed:
        #   - simple version change for the same component
        #   - substitution
        # * iterable_item_removed (remove in master)
        # * iterable_item_added (added in master)
        # create ComponentVersion accordingly
        INDEX_STATUS = 0
        other_version = {}
        CONTAINER_STATUS = get_component_status(
            master_component['container'],
            delta_versions, SORTED_MASTER,
            component_versions[version])
        LOGGER.info("Container status: %s", CONTAINER_STATUS)

        if CONTAINER_STATUS == 'version_changed':
            other_version[version] = get_old_version_component(
                master_component['container'], component_versions[version])
            INDEX_STATUS = 1
        elif CONTAINER_STATUS == 'component_added':
            # no other version
            INDEX_STATUS = 2
        else:
            other_version[version] = master_component['version']
            # need post processing see oldest version to see
            # if there is no changes since more than 2 release or not
            # temp index = -1
            # post processing shall allow to say if
            # index = 0: no changes since last release
            # index = 3: no changes since more than 2 release

        # As we are testing several releases, check if the object already exists
        # If so complete it, do not create a new one..
        if NB_ITERATION_DATASET < 1:
            LOGGER.info("Creation of the dataset for %s", master_component['container'])
            version_object = ComponentVersion(
                component=master_component['component'],
                container=master_component['container'],
                image=master_component['image'],
                current_version=master_component['version'],
                other_version=other_version,
                status=INDEX_STATUS)
            DATA_VERSIONS.append(version_object)
        else:
            # we already compared master with a release
            # the DATASET is initiated
            # we start the second comparison

            # First consider the changes between master and the new release
            LOGGER.info("Update of the dataset for %s", master_component['container'])
            index_data = get_data_version_container_index(
                master_component['container'], DATA_VERSIONS)

            local_other_version = DATA_VERSIONS[index_data].other_version
            if get_old_version_component(
                    master_component['container'],
                    component_versions[version]) != "unknown":
                local_other_version[version] = get_old_version_component(
                        master_component['container'], component_versions[version])
                DATA_VERSIONS[index_data].other_version = local_other_version

            # postprocessing to detect if the version of the container
            # did not change for at least 2 releases
            count_versions = Counter(local_other_version.values())
            for count_version in count_versions.values():
                if (count_version > 1 and
                    INDEX_STATUS < 1):
                    DATA_VERSIONS[index_data].status = 3
    NB_ITERATION_DATASET += 1

    # manage removed pods
    for removed_container in get_removed_container_list(
        delta_versions, component_versions[version], master_component):

        index_data = get_data_version_container_index(
            removed_container['container'], DATA_VERSIONS)
        LOGGER.info("Removed container index data in DATASET: %s", index_data)
        # "new" removed container, add it to DATASET
        if index_data < 0 or index_data is None:
            version_object = ComponentVersion(
                component=removed_container['component'],
                container=removed_container['container'],
                image=removed_container['image'],
                current_version="",
                other_version={version: removed_container['version']},
                status=4)
            DATA_VERSIONS.append(version_object)
        else:
            # removed container already seen as removed in another old release
            # just amend the DATASET to indicate the old versions
            LOGGER.info(
                "Update of the dataset for a removed container in master %s",
                removed_container['container'])
            index_data = get_data_version_container_index(
                removed_container['container'], DATA_VERSIONS)
            local_other_version = DATA_VERSIONS[index_data].other_version
            local_other_version[version] = get_old_version_component(
                removed_container['container'], component_versions[version])
            DATA_VERSIONS[index_data].other_version = local_other_version

# Exclude filebeat dockers
CLEAN_DATA_VERSIONS = []
for data in DATA_VERSIONS:
    # an xfail list coudl be used here
    if "filebeat" not in data.image:
        CLEAN_DATA_VERSIONS.append(data)

#LOGGER.info(str(CLEAN_DATA_VERSIONS))

LOGGER.info("*********************************************************************")
LOGGER.info("*********************************************************************")
LOGGER.info("******************       Generate Reporting           ***************")
LOGGER.info("*********************************************************************")
LOGGER.info("*********************************************************************")

jinja_env = Environment(
    autoescape=select_autoescape(['html']),
    loader=FileSystemLoader('./template'))
jinja_env.get_template('docker-version-tmpl.html').stream(
    data=CLEAN_DATA_VERSIONS).dump(
    '{}'.format("index-versions.html"))
