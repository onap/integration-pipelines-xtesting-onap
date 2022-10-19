#!/usr/bin/env bash
#
# Copyright Samsung Electronics (c) 2021 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#

# This script will do the following:
# 1. install tern in $TERN_LOCATION/ternenv (defaults to $HOME)
# 2. query kubectl for all images from $K8NAMESPACE
# 3. run tern analysis on each image while generating $HTML_REPORT in
#    current directory & placing results in $OUT directory. Each report
#    and log will have the image name with '/' substituted to '_'.
# 4. push results via lftools taking ARCHIVES_LOCATION as argument.
#    Requires CI_PIPELINE_CREATED_AT, $POD, $LF_RESULTS_BACKUP vars to be set
#
# Dependencies:
# - fuse-overlayfs
# - attr
# - python3-venv
# - jq
# - lftools (python package)

set -euxo pipefail

TERN_LOCATION=${TERN_LOCATION:-"$HOME"}
OUT=${OUT:-tern}
HTML_REPORT=${HTML_REPORT:-index.html}
K8NAMESPACE=${K8NAMESPACE:-onap}
ARCHIVES_LOCATION=${ARCHIVES_LOCATION:-/tmp/tern}

install_tern() {
  # current release has bug with image name parsing, need to install
  # from source until release (end of March 2021)
  local tern_location=$1
  local initial_dir=$(pwd)
  cd $tern_location
  python3 -m venv ternenv
  cd ternenv
  . bin/activate
  git clone https://github.com/tern-tools/tern --branch main || true
  cd tern
  git pull origin main
  git checkout 52fd8f3ee915c0c637d82dbeb0856219780688c7
  python3 -m pip install wheel
  python3 -m pip install .
  cd $initial_dir
  echo "===========> Tern installed"
}

init_tern() {
  local tern_location=$1
  local initial_dir=$(pwd)
  cd $tern_location
  cd ternenv
  . bin/activate
  cd $initial_dir
}


print_head() {
  local html_report=$1

  echo '<!DOCTYPE html>
  <html lang="en">
    <head>
      <meta charset="utf-8">
      <title>ONAP Tern analysis</title>
    </head>
    <body>
      <table>
        <caption>Results</caption>
        <thead>
          <tr>
              <th>Image</th>
              <th>Version</th>
              <th>Report</th>
              <th>Log</th>
              <th>Pkgs with GPLv3</th>
              <th>Pkgs with undefined lic</th>
              <th>Notes</th>
          </tr>
        </thead>
        <tbody>' >> $html_report
}

print_tail() {
  local html_report=$1

  echo '      </tbody>
      </table>
    </body>
  </html>' >> $html_report
}

print_image() {
  local html_report=$1
  local full_img_name=$2
  local report=$3
  local log=$4


  local pkglicenses=""
  local gplv3pkgs=""
  local licnotfound=""
  local notes=""

  local img=${2%:*}
  local ver=${2##*:}

  if [[ -s "$report" ]]
  then
    pkglicenses=$(jq '.images | .[].image.layers | .[]?.packages | .[] | "\(.name) \(.pkg_licenses) \(.pkg_license)"' ${report}) || true
    gplv3pkgs=$(echo "${pkglicenses}" |grep GPL-3 | awk '{ print substr($1,2); }' | tr '\n' ' ') || true
    licnotfound=$(echo "${pkglicenses}" |grep -e ' \[\] \"' | awk '{ print substr($1,2); }' | tr '\n' ' ') || true
  else
    if [[ $(grep -m 1 -hEe "(Traceback|CRITICAL)" $log) ]];
    then
      notes='Report not generated, check logs for traceback/critical error'
    fi
  fi

  echo "        <tr>
          <td>${img}</td>
          <td>${ver}</td>
          <td><a href="${report}">Report</a></td>
          <td><a href="${log}">Log</a></td>
          <td>${gplv3pkgs}</td>
          <td>${licnotfound}</td>
          <td>${notes}</td>
        </tr>" >> $1
}

analyze() {
  local img=$1
  local report=$2
  local log=$3
  echo "$img analysis started"
  tern report -f json -i ${img} 1> ${report} 2> ${log} || true
}

get_images() {
  local namespace=$1
  kubectl get pods --namespace $namespace \
           -o jsonpath="{.items[*].spec.containers[*].image}" |\
           tr -s '[[:space:]]' '\n' | sort | uniq -u
}

push_results() {
  local archives_location=$1
  local nexus_url="https://nexus.onap.org"
  local nexus_path="onap-integration/weekly/$POD/$(date -d${CI_PIPELINE_CREATED_AT} +'%Y-%m')/$(date -d${CI_PIPELINE_CREATED_AT} +'%d_%H-%M')"
  echo "===========> Send Result to LF Backend"
  echo "nexus_url:"$nexus_url
  echo "nexus_path"$nexus_path
  cd $archives_location && lftools deploy archives $nexus_url $nexus_path $archives_location
}

images=( $(get_images $K8NAMESPACE) )

mkdir -p $OUT
rm -f $HTML_REPORT
install_tern $TERN_LOCATION

print_head ${HTML_REPORT}

for (( i=0; i<${#images[@]}; i++ ))
do

  fname=${images[$i]//\//_}
  report=${OUT}/${fname}".json"
  log=${OUT}/${fname}".log"

  analyze ${images[$i]} ${report} ${log}
  print_image ${HTML_REPORT} ${images[$i]} ${report} ${log}
done

print_tail ${HTML_REPORT}
echo "===========> Finished analysis of all images in "$K8NAMESPACE

push_results ${ARCHIVES_LOCATION}
