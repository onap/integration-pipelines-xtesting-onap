#!/usr/bin/env bash
#
# Copyright Oranges (c) 2021 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#

# This script will do the following:
# 1. prepare the benchmark env
# 2. clone onaptests_bench
# 3. run 2 tests:
# - 5 // onboarding during 24h (basic_onboard)
# - 10 // instantiation using a_la_carte bpmn during 24h (basic_vm)
# 4. push results via lftools taking ARCHIVES_LOCATION as argument.
#    Requires CI_PIPELINE_CREATED_AT, $POD, $LF_RESULTS_BACKUP vars to be set
#
# Dependencies:
# - python3-venv
# - libssl-dev
# - onaptests_bench

set -euxo pipefail

STABILITY_TESTS_LOCATION=${STABILITY_TESTS_LOCATION:-"$HOME"}
ARCHIVES_LOCATION=${ARCHIVES_LOCATION:-/tmp/stability/}
RESULTS_STABILITY_SDC=$ARCHIVES_LOCATION/archives/stability/results_sdc_5_24h/
RESULTS_STABILITY_INSTANTIATION=$ARCHIVES_LOCATION/archives/stability/results_instantiation_10_24h/

prepare_stability_tests() {
  # current release has bug with image name parsing, need to install
  # from source until release (end of March 2021)
  local stability_tests_location=$1
  mkdir -p $RESULTS_STABILITY_SDC
  mkdir -p $RESULTS_STABILITY_INSTANTIATION
  echo $CI_PIPELINE_CREATED_AT

  cd /tmp
  echo "Create virtualenv to launch stability tests"
  python3 -m venv stability_tests_env
  cd stability_tests_env
  . bin/activate
  echo "Install onaptests_bench as a python module"
  export CRYPTOGRAPHY_DONT_BUILD_RUST=1
  pip install pip --upgrade
  pip install --no-cache-dir git+https://gitlab.com/Orange-OpenSource/lfn/onap/integration/onaptests_bench.git
}

launch_stability_tests() {
  local stability_tests_location=$1
  cd /tmp/stability_tests_env
  . bin/activate
  # Tests are launched sequentially
  echo "===========> Launch Instantiation stability test"
  run_stability_tests -t basic_vm -s 10 -d 1440 -r $RESULTS_STABILITY_INSTANTIATION
  echo "===========> Launch SDC stability test"
  run_stability_tests -t basic_onboard -s 5 -d 1440 -r $RESULTS_STABILITY_SDC
}

push_results() {
  local archives_location=$1
  local nexus_url="https://nexus.onap.org"
  local nexus_path="onap-integration/weekly/$POD/$(date -d${CI_PIPELINE_CREATED_AT} +'%Y-%m')/$(date -d${CI_PIPELINE_CREATED_AT} +'%d_%H-%M')"
  sudo chown -Rf debian:debian $ARCHIVES_LOCATION
  echo "===========> Send Result to LF Backend"
  echo "nexus url:"$nexus_url
  echo "nexus_path"$nexus_path
  lftools deploy archives $nexus_url $nexus_path $archives_location
}

echo "Prepare stability tests"
prepare_stability_tests $STABILITY_TESTS_LOCATION

launch_stability_tests $STABILITY_TESTS_LOCATION

echo "push results to LF backend.."
push_results ${ARCHIVES_LOCATION}

# Once the stability tests results have been pushed to LF, we can
# - sync the results of the tests checking the versions
# - start the resiliency tests

# push the versions if results exist
if [ -f /dockerdata-nfs/onap/integration/security/versions/versions_reporting.html ]; then
  mkdir -p /tmp/versions/archives/security/versions/
  cp  /dockerdata-nfs/onap/integration/security/versions/versions_reporting.html /tmp/versions/archives/security/versions/versions.html
  push_results /tmp/versions
fi

# execute the resiliency tests then push the results to LF backend
cd /tmp/resiliency
./run_chaos_tests.sh
if [ -f  /tmp/resiliency/reporting_chaos.html ]; then
  mkdir -p /tmp/resiliency/archives/resiliency
  cp  /tmp/resiliency/reporting_chaos.html /tmp/resiliency/archives/resiliency/reporting_chaos.html
  push_results /tmp/resiliency
fi
