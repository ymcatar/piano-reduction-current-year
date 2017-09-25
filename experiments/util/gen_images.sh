set -e
#!/usr/bin/env bash

if [[ -z "$1" ]]; then
    echo "Usage: $0 [target folder containing xml files]" >&2
    exit 1
fi

for f in $1/**/*.xml; do
    mscore="/Applications/MuseScore 2.app/Contents/MacOS/mscore"

    echo "Processing $f"
    # -T 0 removes the margin
    "$mscore" "$f" -o "${f%.*}.png" -T 0
done
