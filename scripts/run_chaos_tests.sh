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
# - execute a list of chaos tests
# - an aggregation of the results in an html page

#set -euxo pipefail

CHAOS_TESTS_LOCATION=${STABILITY_TESTS_LOCATION:-/tmp/resiliency}
ARCHIVES_LOCATION=${ARCHIVES_LOCATION:-/tmp/resiliency/}
CHAOS_DRAIN_SDC=$ARCHIVES_LOCATION/archives/chaos/chaos-drain

prepare_chaos_tests() {
  # current release has bug with image name parsing, need to install
  # from source until release (end of March 2021)
  local chaos_tests_location=$1
  mkdir -p $CHAOS_DRAIN_SDC
  cd $chaos_tests_location
  python3 -m venv resiliency_tests_env
  cd resiliency_tests_env
  . bin/activate
  pip install pip --upgrade
  pip install git+https://gitlab.com/Orange-OpenSource/lfn/onap/integration/onaptests_chaos.git
  cd $chaos_tests_location
}

launch_chaos_tests() {
  local chaos_tests_location=$1
  cd $chaos_tests_location

  # the goal of this script is to run sequentially
  # the selected resiliency tests

  TEST_DIR=$(pwd)
  NB_RETRY_MAX=10
  TARGET_NODE="compute01-onap-master"

  for test in node-cpu-hog node-memory-hog node-drain pod-delete-aai
  do
    echo "Setup $test RBAC"
    rbac_file=$test"-rbac.yaml"
    kubectl apply -f $TEST_DIR/$test/$rbac_file
    echo "launch chaos for $test"
    if [ $test = "node-drain" ]
    then
      kubectl cordon $TARGET_NODE
    fi

    chaos_file=$test"-chaos.yaml"
    kubectl apply -f $TEST_DIR/$test/$chaos_file

    # check the chaos is Completed
    echo "Wait for chaos completion"
    check_status=1
    nb_retry=0
    while [ $nb_retry -lt 10 ] &&  [ $check_status -gt 0 ]
    do
       kubectl get chaosengine -n onap $test | grep Completed
       check_status=$?
       let "nb_retry++"
       sleep 30
    done
    echo "Chaos $test completed"
  done

  if [ $test = "node-drain" ]
  then
    kubectl uncordon $TARGET_NODE
  fi

  sleep 120

  # get the results, wait for the result of the last test to be Completed
  # we expect that the previous ones are completed
  check_status=1
  nb_retry=0
  while [ $nb_retry -lt 10 ] && [ $check_status -gt 0 ]
  do
     kubectl describe chaosengine -n onap node-drain | grep Completed
     check_status=$?
     let "nb_retry++"
     sleep 30
     echo "Test still running...."
  done

  # we collect all the chaosresults in json files
  for result in $(kubectl get chaosresult -n onap |awk {'print $1'} | grep -v NAME)
  do
      result_file=$result".json"
      kubectl get chaosresult -n onap $result -o json > $result_file
  done

  # Cleanup chaos resources
  kubectl delete chaosengine -n onap --all
  kubectl delete chaosresult -n onap --all
}

generate_html_page() {
  echo "Generate html page"
  generate_chaos_reporting -r /tmp/resiliency/reporting_chaos.html
}

echo "Prepare chaos tests"
prepare_chaos_tests $CHAOS_TESTS_LOCATION

launch_chaos_tests $CHAOS_TESTS_LOCATION

generate_html_page
