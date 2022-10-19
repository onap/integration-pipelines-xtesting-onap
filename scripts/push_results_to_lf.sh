#!/bin/bash
# backup results to LF server

NEXUS_URL=https://nexus.onap.org
SILO=onap-integration
ARCHIVES_DIR=/tmp

# We need minio client in order to retrieve files when on S3 mode
if [ -z "${S3_ENDPOINT_URL}" ]
then
  echo "S3 vars are not set, not installing mc"
else
  wget https://dl.min.io/client/mc/release/linux-amd64/mc
  chmod +x mc
  ./mc alias set s3 "${S3_ENDPOINT_URL}" "${S3_ACCESS_KEY}" "${S3_SECRET_KEY}"
fi

# We need lftools to push results tyo LF
pip install lftools

# create .netrc
# netrc contains credentials to push artifacts to LF
# the password is defined as a gitlab-ci variable
if [ ! -f ~/.netrc ]; then
  # If .netrc does not exist create one from the template
  cp scripts/.netrc ~
else
  # if one already exists, save this config in /tmp
  # and replace it by the template
  mv ~/.netrc /tmp
  cp scripts/.netrc ~
fi
sed -i 's/LF_IT_NEXUS_PWD/'$LF_RESULTS_BACKUP'/g' ~/.netrc
chmod 600 ~/.netrc

# prepare the archives
echo "Prepare the archive for $pod"
if [ -z "$GERRIT_REVIEW" ]
then
  if [[ $1 == *"weekly"* ]]
  then
    FREQUENCY="weekly"
  else
    FREQUENCY="daily"
  fi
  if [ -z "${CI_PIPELINE_CREATED_AT}" ]
  then
    NEXUS_PATH="${SILO}/$FREQUENCY/$pod/$(date +'%Y-%m')/$(date +'%d_%H-%M')"
  else
    NEXUS_PATH="${SILO}/$FREQUENCY/$pod/$(date -d${CI_PIPELINE_CREATED_AT} +'%Y-%m')/$(date -d${CI_PIPELINE_CREATED_AT} +'%d_%H-%M')"
  fi
else
  if [ -z "$EXPERIMENTAL" ]
  then
    NEXUS_PATH="${SILO}/gating/$GERRIT_REVIEW-$GERRIT_PATCHSET"
  else
    NEXUS_PATH="${SILO}/experimental-gating/$GERRIT_REVIEW-$GERRIT_PATCHSET"
  fi
fi
mkdir -p $ARCHIVES_DIR/archives

if [ -z "${CI_PIPELINE_ID}" ]
then
  CI_PIPELINE_ID="64"
fi

if [ -z "${S3_ENDPOINT_URL}" ]
then
  echo "*** non S3 mode, use legacy method ***"
  cp -rf $1/* $ARCHIVES_DIR/archives
else
  echo "*** S3 mode ***"
  if [ -z "$GERRIT_REVIEW" ]
  then
    echo "** non gating result"
    if [ -z "${CI_PIPELINE_CREATED_AT}" ]
    then
      DATE=$(date "+%Y-%m-%d")
    else
      DATE=$(date -d${CI_PIPELINE_CREATED_AT} "+%Y-%m-%d")
    fi
    IDENTIFIER="${pod}/${DATE}-${CI_PIPELINE_ID}"
    if [ -z "$FREQUENCY" ]
    then
      TEST_TYPE="daily"
    else
      TEST_TYPE="${FREQUENCY}"
    fi
  else
    echo "** gating result"
    TEST_TYPE="gating"
    IDENTIFIER="${GERRIT_REVIEW}-${GERRIT_PATCHSET}-${CI_PIPELINE_ID}"
  fi
  if [ -z "$EXPERIMENTAL" ]
  then
    echo "* not an experimental test"
  else
    echo "* experimental test"
    TEST_TYPE="${TEST_TYPE}-experimental"
  fi

  S3_PATH="s3/onap/${TEST_TYPE}/${IDENTIFIER}/"
  cp -rf $1/index.html $ARCHIVES_DIR/archives/index.html
  ./mc cp --recursive "${S3_PATH}" $ARCHIVES_DIR/archives
  scripts/output_summary_s3.sh $ARCHIVES_DIR/archives
fi

# Push results to LF nexus
echo " call lftools"
lftools deploy archives $NEXUS_URL $NEXUS_PATH $ARCHIVES_DIR
echo "Results uploaded to $NEXUS_URL/content/sites/logs/$NEXUS_PATH"

# clean
rm -Rf $ARCHIVES_TMP_DIR
# restore old .netrc
if [ -f ~/tmp/.netrc ]; then
  mv ~/tmp/.netrc ~/.netrc
fi
