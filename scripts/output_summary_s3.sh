#!/bin/bash

echo '_____________________________ Results ______________________'
echo ''
echo '************************************************************'
echo '************************************************************'
echo '************ Infrastructure-healthcheck Results ************'
echo '************************************************************'
echo '************************************************************'
if [ -f "$1/k8s/k8s/kubernetes-status/onap-k8s.log" ]; then
    echo '--------> onap-k8s'
    grep '>>>' "$1/k8s/k8s/kubernetes-status/onap-k8s.log" | tr ',' '\n' | sed 's/>>>/ */; s/\[\([^]]\)/[\'$'\n   - \\1/; s/^[ ]\([^\* ]\)/   - \\1/'
else
    echo '--------> onap-k8s NOT executed'
fi
if [ -f "$1/k8s/k8s/onap-helm/onap-helm.log" ]; then
echo '--------> onap-helm'
grep '>>>' "$1/k8s/k8s/onap-helm/onap-helm.log" | tr ',' '\n' | sed 's/>>>/ */; s/\[\([^]]\)/[\'$'\n   - \\1/; s/^[ ]\([^\* ]\)/   - \\1/'
else
    echo '--------> onap-helm NOT executed'
fi
echo ''
echo '************************************************************'
echo '************************************************************'
echo '********************* Healthcheck Results ******************'
echo '************************************************************'
echo '************************************************************'
if [ -f "$1/full/xtesting.log" ]; then
    echo '--------> robot full healthcheck tests'
    sed -n '/xtesting.core.robotframework - INFO - $/,/Output/p' "$1/full/xtesting.log"
else
    echo '--------> robot full healthcheck tests NOT executed'
fi
echo ''
echo '************************************************************'
echo '************************************************************'
echo '********************* Basic tests Results ******************'
echo '************************************************************'
echo '************************************************************'
if [ -f "$1/healthdist/xtesting.log" ]; then
    echo '--------> healthdist (vFW onboarding and distribution)'
    sed -n '/xtesting.core.robotframework - INFO - $/,/Output/p' "$1/healthdist/xtesting.log" | grep '::' | grep '|'
else
    echo '--------> healthdist tests NOT executed'
fi
if [ -f "$1/postinstall/xtesting.log" ]; then
    echo '--------> postinstall tests (dmaap and A&AI)'
    sed -n '/xtesting.core.robotframework - INFO - $/,/Output/p' "$1/postinstall/xtesting.log" | grep '::' | grep '|'
else
    echo '--------> postinstall tests NOT executed'
fi
if [ -f "$1/cmpv2/xtesting.log" ]; then
    echo '--------> CMPv2 tests'
    sed -n '/xtesting.core.robotframework - INFO - $/,/Output/p' "$1/cmpv2/xtesting.log" | grep '::' | grep '|'
else
    echo '--------> CMPv2 tests NOT executed'
fi
if [ -f "$1/dcaemod/xtesting.log" ]; then
    echo '--------> DCAEMOD tests'
    sed -n '/xtesting.core.robotframework - INFO - $/,/Output/p' "$1/dcaemod/xtesting.log" | grep '::' | grep '|'
else
    echo '--------> DCAEMOD tests NOT executed'
fi
if [ -f "$1/hv-ves/xtesting.log" ]; then
    echo '--------> HV-VES tests'
    sed -n '/xtesting.core.robotframework - INFO - $/,/Output/p' "$1/hv-ves/xtesting.log" | grep '::' | grep '|'
else
    echo '--------> HV-VES tests NOT executed'
fi
if [ -f "$1/ves-collector/xtesting.log" ]; then
    echo '--------> VES collector tests'
    sed -n '/xtesting.core.robotframework - INFO - $/,/Output/p' "$1/ves-collector/xtesting.log" | grep '::' | grep '|'
else
    echo '--------> VES collector tests NOT executed'
fi
if [ -f "$1/basic_onboard/xtesting.log" ]; then
    echo "--------> Basic Onboard tests (SDC)"
    NORMAL_RUN=$(grep -A2 RESULT "$1/basic_onboard/xtesting.log" | grep basic_onboard | grep -v ERROR | awk {'print $2 ": "  $8 " (" $6 ")"'})
    if [ -z "$NORMAL_RUN" ]
    then
        RESULT=$(tail -n 1 "$1/basic_onboard/xtesting.log" | cut -d'-' -f6 | cut -d':' -f 2)
        echo "basic_onboard: $RESULT"
        echo "basic_onboard hasn't finished well, check logs"
    else
        echo "$NORMAL_RUN"
    fi

else
    echo "--------> Basic onboard tests NOT executed"
fi
if [ -f "$1/basic_cds/xtesting.log" ]; then
    echo "--------> CDS tests"
    NORMAL_RUN=$(grep -A2 RESULT "$1/basic_cds/xtesting.log" | grep basic_cds | grep -v ERROR | awk {'print $2 ": "  $8 " (" $6 ")"'})
    if [ -z "$NORMAL_RUN" ]
    then
        RESULT=$(tail -n 1 "$1/basic_cds/xtesting.log" | cut -d'-' -f6 | cut -d':' -f 2)
        echo "basic_cds: $RESULT"
        echo "basic_cds hasn't finished well, check logs"
    else
        echo "$NORMAL_RUN"
    fi

else
    echo "--------> CDS tests NOT executed"
fi
echo ''

echo '************************************************************'
echo '************************************************************'
echo '******************** End to End usecases *******************'
echo '************************************************************'
echo '************************************************************'
for test in pnf-registrate 5gbulkpm;do
    if [ -f "$1/$test/xtesting.log" ]; then
        echo "--------> $test tests"
        sed -n '/xtesting.core.robotframework - INFO - $/,/Output/p' "$1/$test/xtesting.log" | grep '::' | grep '|'
    else
        echo "--------> $test tests NOT executed"
    fi
done

for test in basic_vm basic_network basic_cnf basic_vm_macro basic_clamp pnf_macro cds_resource_resolution basic_cnf_macro;do
    if [ -f "$1/$test/xtesting.log" ]; then
        echo "--------> $test tests"
        NORMAL_RUN=$(grep -A2 RESULT "$1/$test/xtesting.log" |grep $test | grep -v ERROR | awk {'print $2 ": "  $8 " (" $6 ")"'})
        if [ -z "$NORMAL_RUN" ]
        then
            RESULT=$(tail -n 1 "$1/$test/xtesting.log" | cut -d'-' -f6 | cut -d':' -f 2)
            echo "$test: $RESULT"
            echo "$test hasn't finished well, check logs"
        else
            echo "$NORMAL_RUN"
        fi
    else
        echo "--------> $test tests NOT executed"
    fi
done
echo ''

echo '************************************************************'
echo '************************************************************'
echo '********************** Security tests **********************'
echo '************************************************************'
echo '************************************************************'
for test in nonssl_endpoints jdpw_ports kube_hunter root_pods unlimitted_pods;do
    if [ -f "$1/$test/xtesting.log" ]; then
        echo "--------> $test tests"
        NORMAL_RUN=$(grep -A2 RESULT "$1/$test/xtesting.log" |grep $test | grep -v -E -- 'DEBUG|INFO|ERROR' | awk {'print $2 ": "  $8 " (" $6 ")"'})
        if [ -z "$NORMAL_RUN" ]
        then
            RESULT=$(tail -n 1 "$1/$test/xtesting.log" | cut -d'-' -f6 | cut -d':' -f 2)
            echo "$test: $RESULT"
            echo "$test hasn't finished well, check logs"
        else
            echo "$NORMAL_RUN"
        fi
    else
        echo "--------> $test tests NOT executed"
    fi
done
echo ''
echo '____________________________________________________________'
