#!/bin/bash
# This bash script sleeps for [0,5] seconds and
# then copies an uploaded file containing a random number
# to the expected output location
# and checks whether the downloaded result.txt matches the input
# Exit codes:
#   0: Worker successfully ran the command and results match
#   2: The worker returned the wrong result
#   Anything else: Other errors (inspect)
#
# This happens ST_ITER times. (where ST_ITER is an environment variable)
# Defaults to 1 iteration if not set.

# Things being tested:
#   * (recc<->bgd-cas)  GetActionResult
#   * (recc<->bgd-cas) FindMissingBlobs
#   * (recc<->bgd-cas<->bots) BatchUpdateBlobs
#   * (recc<->bgd-cas<->bots) BatchReadBlobs
#   * (recc<->bgd-exec) WaitExecution
#   * (recc<->bgd-cas<->bots) Cas Upload
#   * (recc<->bgd-cas<->bots) Cas Downloads
#   * (bgd-exec<->bots) UpdateActionResult
#

iter=${ST_ITER:-1}

for ((i=1;i<=iter;i++)); do
    echo "Iteration [$i/$iter]"
    sleep $[ ( $RANDOM % 5 ) ]s

    mynum=$RANDOM
    echo $mynum > expected.txt

    set -o pipefail

    RECC_DEPS_OVERRIDE=expected.txt \
    RECC_OUTPUT_FILES_OVERRIDE=result.txt \
        recc cp expected.txt result.txt
    exitcode=$?
    if [[ $exitcode -ne 0 ]]; then
        exit $exitcode
    fi

    diff -y result.txt expected.txt || exit 2
done

