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
import os

import jinja2
import json
import requests

from prettytable import PrettyTable

# Logger
logging.basicConfig()
LOGGER = logging.getLogger("Xtesting-ONAP-Status")
LOGGER.setLevel("INFO")
# LOGGER.setLevel("DEBUG")

PROXY = {}
# PROXY = {'http': 'socks5h://127.0.0.1:8080',
#          'https': 'socks5h://127.0.0.1:8080'}

# Initialization
URL_PRIVATE_BASE = "http://onap.api.testresults.opnfv.fr/api/v1/results"
URL_BASE = "http://testresults.opnfv.org/onap/api/v1/results"
URL_BASE_PODS = "http://testresults.opnfv.org/onap/api/v1/pods"
REPORTINGDATE = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

# init just connection_check to get the list of scenarios
# as all the scenarios run connection_check
# the following tests are the default daily tests
INFRA_HEALTHCHECK = {'name': 'infrastructure-healthcheck',
                     'tests': {'onap-k8s', 'onap-helm',
                     'onap-k8s-teardown'}}
#                     'onap-k8s-teardown','internal_check_certs'}}
HEALTHCHECK = {'name': 'healthcheck',
               'tests': {'core', 'full',
                         'healthdist', 'postinstall',
                         'hv-ves', 'ves-collector',
                         'basic_onboard', 'dcaemod',
                         'cps-healthcheck', 'cps-dmi-plugin-healthcheck',
                         'cps-temporal-healthcheck'}}
# SMOKE_USECASES = {'name': 'smoke usecases',
#                   'tests': {'basic_vm', 'freeradius_nbi', 'clearwater_ims',
#                             'pnf-registrate', '5gbulkpm', 'hv-ves'}}
SMOKE_USECASES = {'name': 'smoke usecases',
                  'tests': {'basic_vm', 'basic_network', 'basic_cnf', 'cmpv2',
                            'pnf-registrate', '5gbulkpm', 'basic_clamp',
                            'basic_vm_macro', 'pnf_macro', 'cds_resource_resolution',
                            'basic_cnf_macro'}}

SECURITY_USECASES = {'name': 'security',
                     'tests': {'root_pods', 'unlimitted_pods',
                               'nonssl_endpoints', 'nodeport_check_certs',
                               'kube_hunter'}}

TIERS = [INFRA_HEALTHCHECK, HEALTHCHECK, SMOKE_USECASES, SECURITY_USECASES]
TRENDS = [INFRA_HEALTHCHECK, HEALTHCHECK, SMOKE_USECASES, SECURITY_USECASES]

# list of tests with dedicated reporting page to be referenced
RESULT_URLS_LEGACY = {
    'core': './xtesting-healthcheck/core/core/report.html',
    'small': './xtesting-healthcheck/small/small/report.html',
    'medium': './xtesting-healthcheck/medium/medium/report.html',
    'full': './xtesting-healthcheck/full/full/report.html',
    'postinstall': './xtesting-healthcheck/postinstall/postinstall/report.html',
    'healthdist': './xtesting-healthcheck/healthdist/healthdist/report.html',
    'onap-k8s': './infrastructure-healthcheck/k8s/kubernetes-status/index.html',
    'onap-k8s-teardown': './infrastructure-healthcheck/k8s-teardown/kubernetes-status/index.html',
    'onap-helm': './infrastructure-healthcheck/k8s/onap-helm/helm.html',
    'nodeport_check_certs': './infrastructure-healthcheck/k8s/nodeport_check_certs/certificates.html',
    'internal_check_certs': './infrastructure-healthcheck/internal_check_certs/internal_check_certs/certificates.html',
    'basic_vm': './smoke-usecases/basic_vm/basic_vm/reporting.html',
    'basic_vm_macro': './smoke-usecases/basic_vm_macro/basic_vm_macro/reporting.html',
    'basic_network': './smoke-usecases/basic_network/basic_network/reporting.html',
    'basic_cnf': './smoke-usecases/basic_cnf/basic_cnf/reporting.html',
    'basic_cds': './smoke-usecases/basic_cds/basic_cds/reporting.html',
    'basic_onboard': './smoke-usecases/basic_onboard/basic_onboard/reporting.html',
    'basic_clamp': './smoke-usecases/basic_clamp/basic_clamp/reporting.html',
    'pnf_macro': './smoke-usecases/pnf_macro/pnf_macro/reporting.html',
    'pnf-registrate': './xtesting-smoke-usecases-robot/pnf-registrate/pnf-registrate/report.html',
    '5gbulkpm':  './xtesting-smoke-usecases-robot/5gbulkpm/5gbulkpm/report.html',
    'hv-ves':  './xtesting-smoke-usecases-robot/hv-ves/hv-ves/report.html',
    'cmpv2':  './xtesting-smoke-usecases-robot/cmpv2/cmpv2/report.html',
    'dcaemod':  './xtesting-smoke-usecases-robot/dcaemod/dcaemod/report.html',
    'ves-collector':  './xtesting-smoke-usecases-robot/ves-collector/ves-collector/report.html',
    'root_pods': './security/root_pods/root_pods/root_pods.log',
    'unlimitted_pods': './security/unlimitted_pods/unlimitted_pods/unlimitted_pods.log',
    'cis_kubernetes': './security/cis_kubernetes/cis_kubernetes/cis_kubernetes.log',
    'nonssl_endpoints': './security/nonssl_endpoints/nonssl_endpoints/nonssl_endpoints.log',
    'jdpw_ports': './security/jdpw_ports/jdpw_ports/jdpw_ports.log',
    'kube_hunter': './security/kube_hunter/kube_hunter/kube_hunter.log',
    'versions': './security/versions/versions.html',
    'cps-healthcheck': './xtesting-healthcheck/cps-healthcheck/cps-healthcheck/report.html',
    'cds_resource_resolution': './smoke-usecases/cds_resource_resolution/cds_resource_resolution/reporting.html',
    'basic_cnf_macro':'./smoke-usecases/basic_cnf_macro/basic_cnf_macro/reporting.html',
    'cps-dmi-plugin-healthcheck':'./xtesting-healthcheck/cps-dmi-plugin-healthcheck/cps-dmi-plugin-healthcheck/report.html',
    'cps-temporal-healthcheck':'./xtesting-healthcheck/cps-temporal-healthcheck/cps-temporal-healthcheck/report.html'
    }

# list of tests with dedicated reporting page to be referenced
RESULT_URLS_S3 = {
    'core': './core/core/report.html',
    'full': './full/full/report.html',
    'postinstall': './postinstall/postinstall/report.html',
    'healthdist': './healthdist/healthdist/report.html',
    'onap-k8s': './k8s/k8s/kubernetes-status/index.html',
    'onap-k8s-teardown': './k8s-teardown/k8s-teardown/kubernetes-status/index.html',
    'onap-helm': './k8s/k8s/onap-helm/helm.html',
    'nodeport_check_certs': './k8s/k8s/nodeport_check_certs/certificates.html',
    'internal_check_certs': './infrastructure-healthcheck/internal_check_certs/internal_check_certs/certificates.html',
    'basic_vm': './basic_vm/basic_vm/reporting.html',
    'basic_vm_macro': './basic_vm_macro/basic_vm_macro/reporting.html',
    'basic_network': './basic_network/basic_network/reporting.html',
    'basic_cnf': './basic_cnf/basic_cnf/reporting.html',
    'basic_cds': './basic_cds/basic_cds/reporting.html',
    'basic_onboard': './basic_onboard/basic_onboard/reporting.html',
    'basic_clamp': './basic_clamp/basic_clamp/reporting.html',
    'pnf_macro': './pnf_macro/pnf_macro/reporting.html',
    'pnf-registrate': './pnf-registrate/pnf-registrate/report.html',
    '5gbulkpm':  './5gbulkpm/5gbulkpm/report.html',
    'hv-ves':  './hv-ves/hv-ves/report.html',
    'cmpv2':  './cmpv2/cmpv2/report.html',
    'dcaemod':  './dcaemod/dcaemod/report.html',
    'ves-collector':  './ves-collector/ves-collector/report.html',
    'root_pods': './root_pods/root_pods/root_pods.log',
    'unlimitted_pods': './unlimitted_pods/unlimitted_pods/unlimitted_pods.log',
    'cis_kubernetes': './cis_kubernetes/cis_kubernetes/cis_kubernetes.log',
    'nonssl_endpoints': './nonssl_endpoints/nonssl_endpoints/nonssl_endpoints.log',
    'jdpw_ports': './jdpw_ports/jdpw_ports/jdpw_ports.log',
    'kube_hunter': './kube_hunter/kube_hunter/kube_hunter.log',
    'versions': './security/versions/versions.html',
    'cps-healthcheck': './cps-healthcheck/cps-healthcheck/report.html',
    'cds_resource_resolution': './cds_resource_resolution/cds_resource_resolution/reporting.html',
    'basic_cnf_macro':'./basic_cnf_macro/basic_cnf_macro/reporting.html',
    'cps-dmi-plugin-healthcheck':'./cps-dmi-plugin-healthcheck/cps-dmi-plugin-healthcheck/report.html',
    'cps-temporal-healthcheck':'./cps-temporal-healthcheck/cps-temporal-healthcheck/report.html'
    }

def get_lab_owner(pod_name):
    url = (URL_BASE_PODS + "?name=" + pod_name)
    response = requests.get(url, proxies=PROXY)
    response_json = response.json()
    try:
        lab_owner = response_json['pods'][0]['creator']
    except KeyError:
        lab_owner = "unknown"
    except IndexError:
        lab_owner = "unknown"
    return lab_owner

# Retrieve the Functest configuration to detect which tests are relevant
# according to the pod, scenario
PERIOD = 1

LOGGER.info("generate Xtesting reporting page")

PARSER = argparse.ArgumentParser()
PARSER.add_argument('-p', '--pod', help='Pod name')
PARSER.add_argument('-d', '--db', help='Test DB URL')
PARSER.add_argument('-t', '--build_tag', help='Build_tag')
PARSER.add_argument('-m', '--mode', help='result retrieval mode', choices=['legacy', 's3'], default='legacy')
ARGS = PARSER.parse_args()

PODS = ['onap_xtesting_openlab-OPNFV-oom',
        'onap_oom_gating_pod4_1-ONAP-oom',
        'onap_oom_gating_pod4_2-ONAP-oom',
        'onap_oom_gating_pod4_3-ONAP-oom',
        'onap_oom_gating_pod4_4-ONAP-oom',
        'onap_oom_gating_azure_1-OPNFV-oom',
        'onap_oom_gating_azure_2-OPNFV-oom',
        'onap_oom_gating_azure_3-OPNFV-oom',
        'onap_oom_gating_azure_4-OPNFV-oom',
        'onap_daily_pod4_master-ONAP-oom',
        'onap_daily_pod4_istanbul-ONAP-oom',
        'onap_daily_pod4_jakarta-ONAP-oom']

if ARGS.pod is not None:
    PODS = [ARGS.pod]

    # adapt tests according to the typ of tests: daily/weekly/gating
    if "weekly" in ARGS.pod:
        # Complete the list with weekly tests
        SECURITY_USECASES['tests'].add('versions')
        SECURITY_USECASES['tests'].add('jdpw_ports')
        INFRA_HEALTHCHECK['tests'].add('internal_check_certs')
        PERIOD = 7
    if "gating" in ARGS.pod:
        SECURITY_USECASES['tests'].remove('kube_hunter')

    # adapt test according to the version: guilin / honolulu / master
    if "guilin" in ARGS.pod:
        HEALTHCHECK['tests'].remove('dcaemod')
        HEALTHCHECK['tests'].remove('cps-healthcheck')
        HEALTHCHECK['tests'].remove('cps-dmi-plugin-healthcheck')
        HEALTHCHECK['tests'].remove('cps-temporal-healthcheck')
        SMOKE_USECASES['tests'].remove('basic_clamp')
        SMOKE_USECASES['tests'].remove('cds_resource_resolution')
        SMOKE_USECASES['tests'].remove('basic_cnf_macro')
    if "honolulu" in ARGS.pod:
        HEALTHCHECK['tests'].remove('cps-healthcheck')
        HEALTHCHECK['tests'].remove('cps-dmi-plugin-healthcheck')
        HEALTHCHECK['tests'].remove('cps-temporal-healthcheck')
        SMOKE_USECASES['tests'].remove('cds_resource_resolution')
        SMOKE_USECASES['tests'].remove('basic_cnf_macro')
    if "istanbul" in ARGS.pod:
        HEALTHCHECK['tests'].remove('cps-dmi-plugin-healthcheck')
        HEALTHCHECK['tests'].remove('cps-temporal-healthcheck')
        SMOKE_USECASES['tests'].remove('cds_resource_resolution')
        SMOKE_USECASES['tests'].remove('basic_cnf_macro')
    # Exclude Cloudify based use cases in Master (after istanbul)
    # TO BE updated as it is possible to perform gating on old versions
    # We should exclude cases according to the version not the pod name
    if "master" in ARGS.pod or "gating" in ARGS.pod or "jakarta" in ARGS.pod:
        SMOKE_USECASES['tests'].remove('basic_clamp')
        SMOKE_USECASES['tests'].remove('cmpv2')

RESULT_URLS = RESULT_URLS_LEGACY
LOGGER.info("init core result_url: %s", RESULT_URLS['core'])
if ARGS.mode == "s3":
    LOGGER.info("use s3 mode for file retrieval")
    LOGGER.info("intended core result_url: %s", RESULT_URLS_S3['core'])
    RESULT_URLS = RESULT_URLS_S3
    LOGGER.info("s3 core result_url: %s", RESULT_URLS['core'])

LOGGER.info("final core result_url: %s", RESULT_URLS['core'])
LOGGER.info("List of PODS: %s", PODS)
for pod in PODS:
    LOGGER.info("POD: %s", pod)

    # Get the version
    lab_version = "unknown"
    lab_owner = get_lab_owner(pod)
    LOGGER.info("Lab owner: %s", lab_owner)

    TREND_LINE = ""
    SCORE = 0

    # Trend
    # *****
    # calculation of the TREND
    SCORE_TREND = 0
    if ARGS.db is not None:
        URL_BASE = str([ARGS.db][0])
    LOGGER.info("Database: %s", URL_BASE)

    for tier_trend in TRENDS:
        tier_results = []
        nb_tests = 0
        nb_pass = 0
        nb_fail = 0
        score = 0

        for test in tier_trend['tests']:
            project = 'integration'
            # Security tests affected to security project
            if tier_trend['name'] == 'security':
                project = 'security'
            url = (URL_BASE + "?project_name=" + project + "&case=" + test +
                   "&pod_name=" + pod + "&last=5")
            response = requests.get(url, proxies=PROXY)
            response_json = response.json()
            # Note the 'u' must be used in python 2.7
            # str(response_json).count("criteria': 'uFAIL")
            # it shall be removed if using python3
            nb_fail = nb_fail + str(response_json).count("criteria': 'FAIL")
            nb_pass = nb_pass + str(response_json).count("criteria': 'PASS")
        try:
            score_trend = round(100 * nb_pass / (nb_pass + nb_fail))
        except ZeroDivisionError:
            score_trend = 0
        LOGGER.debug("Score Trend %s: %s", tier_trend, score_trend)
        tier_trend['score'] = score_trend

    # calculation of the overall SCORE for TREND
    NB_TIERS = 0
    for tier_trend in TRENDS:
        NB_TIERS += 1
        SCORE_TREND = SCORE_TREND + tier_trend['score']
    SCORE_TREND = round(SCORE_TREND / NB_TIERS)

    LOGGER.info("Score Trend: %s", str(SCORE_TREND))

    # calculation of the overall SCORE
    for tier in TIERS:
        tier_results = []
        nb_tests = 0
        nb_pass = 0
        score = 0
        for test in tier['tests']:
            # for Gating we consider the build_tag to retrieve the results
            # For daily runs, we do not. A build_tag is created based on
            # gitlab CI id and is different for each CI stage
            param_build_tag = ""
            if "gating" in pod and ARGS.build_tag is not None:
                param_build_tag = "&build_tag=" + str([ARGS.build_tag][0])
            project = 'integration'
            # Security tests affected to security project
            if tier['name'] == 'security':
                project = 'security'

            # onap-k8s and onap-k8s-teardown are the same test
            # BUT
            # onap-k8s is executed after the installation (fresh installation)
            # onap-k8s-teardown after the tests
            # in case of tests executed in onap namespace, a test may trigger
            # an error status even it was OK at the end of the installation
            # a special uggly processing is then needed to avoid false negative
            search_test = test
            if test == "onap-k8s-teardown":
                search_test = "onap-k8s"

            nb_test_max = 5

            url = (URL_BASE + "?project_name=" + project +
                   "&case=" + search_test +
                   "&period=" + str(PERIOD) +
                   "&pod_name=" + pod + "&last=" + str(nb_test_max) +
                   param_build_tag)
            LOGGER.debug("url: %s", url)
            response = requests.get(url, proxies=PROXY)
            response_json = response.json()
            response_url = ""

            if test in RESULT_URLS:
                response_url = RESULT_URLS[test]
            LOGGER.debug("response_json: %s", response_json)
            req_result = ""

            nb_results_found = len(response_json['results'])

            try:
                if test == "onap-k8s":
                    # We run that test twice (it's failing due to nodeport checks)
                    # so to get the latest result of onap-k8s test (running on startup)
                    # we need to get the 3rd result
                    req_result = response_json['results'][2]['criteria']
                else:
                    req_result = response_json['results'][0]['criteria']

                if lab_version == "unknown":
                    lab_version = response_json['results'][0]['version']

            except IndexError:
                req_result = None

            result = {'name': test,
                      'result': req_result,
                      'url': response_url}
            LOGGER.debug("result: %s", result)

            nb_tests += 1
            if req_result == "PASS":
                nb_pass += 1
            LOGGER.debug("nb_pass: %s", nb_pass)
            LOGGER.debug("nb_tests: %s", nb_tests)
            score = round(100 * nb_pass / nb_tests)
            LOGGER.debug("score: %s", score)
            tier_results.append(result)

        tier['score'] = score
        tier['results'] = tier_results

    # calculation of the overall SCORE
    NB_TIERS = 0
    for tier in TIERS:
        NB_TIERS += 1
        LOGGER.debug("Score %s", tier)
        SCORE = SCORE + tier['score']
    SCORE = round(SCORE / NB_TIERS)
    LOGGER.info("Score: %s", str(SCORE))

    # calculation of the evolution score versus trend
    if SCORE > 1.05*SCORE_TREND:
        # increasing
        TREND_LINE = "long arrow alternate up icon"
        LOGGER.info("Better status")
    elif SCORE < 0.95*SCORE_TREND:
        # decreasing
        TREND_LINE = "long arrow alternate down icon"
        LOGGER.info("Worst status")
    else:
        # stable
        TREND_LINE = "long arrow alternate right icon"
        LOGGER.info("stable status")

    TEMPLATELOADER = jinja2.FileSystemLoader(".")
    TEMPLATEENV = jinja2.Environment(
        loader=TEMPLATELOADER, autoescape=True)
    TEMPLATE_FILE = ("./template/index-tmpl.html")
    TEMPLATE = TEMPLATEENV.get_template(TEMPLATE_FILE)
    OUTPUT_TEXT = TEMPLATE.render(
        tiers=TIERS,
        pod=pod,
        period=PERIOD,
        date=REPORTINGDATE,
        score=SCORE,
        trend=TREND_LINE,
        lab_version=lab_version,
        lab_owner=lab_owner)

    FILENAME = "./index.html"

    with open(FILENAME, "w+") as fh:
        fh.write(OUTPUT_TEXT)

    # Generate txt reporting with my pretty Table
    vote=2
    score_daily = []
    dashboard_table = PrettyTable()
    dashboard_table.field_names = ["Test Name", "Category", "Status"]
    dashboard_table._max_width = {"Test Name" : 30, "Category": 40,"Status" : 10}
    #print(TIERS)
    for tier in TIERS:
        tier_score = {'tier': tier['name'],
                      'score': tier['score']}
        score_daily.append(tier_score)
        for test in tier['results']:
            if tier['name'] == "infrastructure-healthcheck":
                if test['name'] == "onap-k8s" or test['name'] == "onap-helm":
                    if test['result'] == "FAIL" or test['result'] == None:
                        vote-=2
            if tier['name'] == "healthcheck" or tier['name'] == "smoke usecases":
                if test['result'] == "FAIL" or test['result'] == None:
                    vote-=1
            dashboard_table.add_row([test['name'],tier['name'], test['result']])
    if vote < -2:
        vote = -2

    LOGGER.info(dashboard_table)
    LOGGER.info("If I could, I would vote " + str(vote))
    with open("./daily-status.txt", "w") as write_file:
             write_file.write(str(dashboard_table))
             write_file.write("\n")
             write_file.write("**********************\n")
             write_file.write("* Automated vote: "+ str(vote) +"\n")
             write_file.write("**********************\n")
             write_file.close()
    # Gating vote
    # Infra HC onap-helm and onap-K8S MUST be OK
    # HC > 90 only 1 error OK in Full if not critical component
    # Smoke 1

    # Generate heatlth json to build a time view odf the daily dashboard_table
    # create a json file for version tracking

    with open("./daily-scores.json", "w") as write_file:
             json.dump(score_daily, write_file)
