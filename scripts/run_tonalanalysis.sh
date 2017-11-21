#!/usr/bin/env bash
set -e

# This script runs all entrypoints of tonalanalysis (KY1601) and makes sure they
# terminate correctly. However, no attempt is made to ensure that they behave
# properly.

entrypoints=(
    learning.tonalanalysis.xml_parser
    learning.tonalanalysis.run_eventanalysis
    learning.tonalanalysis.tonal_parser
    learning.tonalanalysis.eventanalysis.event_analyzer
    learning.tonalanalysis.eventanalysis.event
    learning.tonalanalysis.eventanalysis.chord_flow
    learning.tonalanalysis.eventanalysis.chord
    learning.tonalanalysis.eventanalysis.lib
    learning.tonalanalysis.eventanalysis.eventtester
)

for entrypoint in ${entrypoints[@]}; do
    command="python3 -m $entrypoint"
    echo "============================================================"
    echo "Running: $command"
    echo "============================================================"
    $command
    echo "============================================================"
    echo "Finished running: $command"
    echo "============================================================"
done
