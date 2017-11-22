#!/bin/sh

for file in $1/*
do
    python3 -m learning.piano.run_motif $file -p
done