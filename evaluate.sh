#!/usr/bin/env bash
set -e

SYSTEM=ordering_svm

source __meta/env

s0008=0.xml:1.xml

SAMPLES=($s0002 $s0003 $s0004 $s0005 $s0006 $s0007 $s0008)
# SAMPLES=($s0000 $s0001)

i=2
for strain in ${SAMPLES[@]}; do
    echo "Running fold $i"
    args=(
        python3 -m learning.systems.$SYSTEM
        -S $strain
        reduce --train --model eval/${SYSTEM}_$i.model
        ${SAMPLES[@]}
        --no-output --no-log
        )
    echo ">> ${args[@]}"
    "${args[@]}" > >(tee eval/${SYSTEM}_$i.log) 2> >(tee eval/${SYSTEM}_$i.verbose.log)
    i=$(($i + 1))
done
