# xtesting-onap

leverage xtesting-onap-robot and xtesting-onap-vnf in CI/CD chains

https://hub.docker.com/r/morganrol/xtesting-onap-robot/
https://hub.docker.com/r/morganrol/xtesting-onap-vnf/

This project aims to automatically test ONAP. Its config source
is shared config files among all OPNFV installers:
- PDF - Pod Description File: describing the hardware level of the
  infrastructure hosting the VIM

## Input

  - configuration files:
    - mandatory:
        - vars/pdf.yml: POD Description File
        - vars/cluster.yml: information about ONAP cluster
        - inventory/jumphost: the ansible inventory for the jumphost
        - vars/kube-config: the kubernetes configuration file in order to have
          credentials to connect
        - clouds.yml: retrieve from the controler node used to create OpenStack
          resources when needed and verify the creation of resources through
          openstack commands. For xtesting, assuming that it is run from the
          controller node, it is transparent. If not copy the clouds.yml in the
          docker under /root/.config/openstack/clouds.yml and reference the
          cloud with the env variable OS_TEST_CLOUD
    - optional:
        - vars/vaulted_ssh_credentials.yml: Ciphered private/public pair of key
          that allows to connect to jumphost
  - Environment variables:
    - mandatory:
        - PRIVATE_TOKEN: to get the artifact
        - artifacts_src: the url to get the artifacts
        - OR artifacts_bin: b64_encoded zipped artifacts (tbd)
        - ANSIBLE_VAULT_PASSWORD: the vault password needed by ciphered ansible
          vars
        - TEST_CLOUD
          - role: name of the cloud as defined in the clouds.yaml_linting
          - value type: string
          - default: "openlab-vnfs-ci"
    - optional:
      - RUNNER_TAG:
          - override the default gitlab-runner tag (ta5_tnaplab)
          - "old" lab runner tag: tnaplab2
      - ANSIBLE_VERBOSE:
          - role: verbose option for ansible
          - values: "", "-vvv"
          - default: ""
      - POD:
          - role: name of the pod when we'll insert healtcheck results
          - value type;: string
          - default: empty
      - DEPLOYMENT:
          - role: name of the deployment for right tagging when we'll insert
            healtcheck results
          - value type: string
          - default: "oom"
      - INFRA_DEPLOYMENT:
          - role: name of the infra deployment for right tagging when we'll
            insert healtcheck results
          - value type: string
          - default: "rancher"
      - DEPLOYMENT_TYPE:
          - role: type of ONAP deployment done
          - values: "core", "small", "medium", "full"
          - default: "core" if nothing found in vars/cluster.yml
      - TEST_RESULT_DB_URL:
          - role: url of test db api
          - value type: string
          - default: "http://testresults.opnfv.org/onap/api/v1/results"
      - DEPLOY_SCENARIO
          - role: name of the deployment scenario
          - value type: string
          - default: "onap-ftw"
      - ONAP_NAMESPACE
          - role: the name of the namespace on kubernetes where ONAP is
            installed
          - value type: string
          - default: "onap"
      - ONAP_VERSION
          - role: the ONAP version deployed
          - value type: string
          - values: "beijing", "2.0.0-ONAP", "master"
          - default: "master"
      - INGRESS:
          - role: do we want to use ingress with ONAP or not
          - value type: boolean
          - default: False
      - CNF_NAMESPACE
          - role: the name of the namespace on kubernetes used for basic_cnf test
            installed
          - value type: string
          - default: "k8s"
      - tests_list
          - role: Define the vnf tests list
          - value type: string
          - values: "all", "basic_vm, freeradius_nbi, ims"
          - default: "all"
      - DEBUG
          - role: enable debug logs and the creation of xtesting.debug.log
          - value type: boolean
          - values: True, False (case insensitive)
          - default: False
      - HELM3_USE_SQL
          - role: ask to use SQL backend for helm3
          - value type: bool
          - default: False
      - RANDOM_WAIT
          - role: do we wait a random time before executing tests involving SDC.
                  This is interesting in order to avoid race conditions.
          - value type: bool
          - default: False

## Output

none

## Chaos testing

 Chaos testing suite using [Litmus](https://litmuschaos.io/)
Launching specified scenarios on specified target, to test the system resiliency

### How to launch a scenario without CI

<code>ansible-playbook onap-chaos-tests.yaml --tags "prepare,<\experiment name>\" --extra-vars "[\extra argument]\"
</code>

### Available scenarios

- **Node drain**
  Unschedule a node then evict all the pods on it
  - extra vars : <code>compute_chaos=<\node name>\ </code> default: First node in the cluster
  - tag : node_drain
- **Node cpu hog**
  Exhaust cpu ressources on the node
  - extra vars : <code>compute_chaos=<\node name>\ </code> default: First node in the cluster
  - tag : node_cpu_hog
- **Node memory hog**
  Exhaust memory ressources on the node
  - extra vars : <code>compute_chaos=<\node name>\ </code> default: First node in the cluster
  - tag : node_memory_hog

## Add Testresults to ONAP Integration result page

Name of test-pod: \<pipeline_name\>-\<pod_owner\>-\<DEPLOYMENT\>

e.g. onap-daily-dt-oom-istanbul-TNAP-oom

Result page: https://logs.onap.org/onap-integration
Instructions: https://wiki.onap.org/pages/viewpage.action?pageId=79202765

```
ag@ag-dev:~$ ssh onap-integration@testresults.opnfv.org
[onap-integration@gce-opnfv-sandbox-fbrockners ~]$ export LANG=de_DE
[onap-integration@gce-opnfv-sandbox-fbrockners ~]$ mongo
MongoDB shell version: 3.2.16
connecting to: test
Server has startup warnings:
2020-10-01T07:54:55.852+0000 I CONTROL  [initandlisten]
2020-10-01T07:54:55.852+0000 I CONTROL  [initandlisten] ** WARNING: /sys/kernel/mm/transparent_hugepage/enabled is 'always'.
2020-10-01T07:54:55.852+0000 I CONTROL  [initandlisten] **        We suggest setting it to 'never'
2020-10-01T07:54:55.852+0000 I CONTROL  [initandlisten]
2020-10-01T07:54:55.852+0000 I CONTROL  [initandlisten] ** WARNING: /sys/kernel/mm/transparent_hugepage/defrag is 'always'.
2020-10-01T07:54:55.852+0000 I CONTROL  [initandlisten] **        We suggest setting it to 'never'
2020-10-01T07:54:55.852+0000 I CONTROL  [initandlisten]
2020-10-01T07:54:55.852+0000 I CONTROL  [initandlisten] ** WARNING: soft rlimits too low. rlimits set to 4096 processes, 64000 files. Number of processes should be at least 32000 : 0.5 times number of files.
2020-10-01T07:54:55.852+0000 I CONTROL  [initandlisten]
singleNodeRepl:PRIMARY>
singleNodeRepl:PRIMARY> use onap
switched to db onap
singleNodeRepl:PRIMARY> show collections
deployresults
pods
projects
results
scenarios
test
testcases
users

singleNodeRepl:PRIMARY> db.pods.insert({"name":"onap-daily-dt-oom-istanbul-TNAP-oom","creator":"Deutsche Telekom","role":"daily","details":"contact: Andreas Geissler","creation_date":"2022-02-22 8:00:00"})
WriteResult({ "nInserted" : 1 })

```
Check if the pod is available:

http://testresults.opnfv.org/onap/api/v1/pods
