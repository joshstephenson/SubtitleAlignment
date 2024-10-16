#!/usr/bin/env bash

if [ -z "$SUBTITLE_REPO" ]; then
    echo "Please set SUBTITLE_REPO environment variable to the root of this repository."
fi
if [ -z "$1" ] || [ -z "$2" ] ; then
    echo "Usage: $0 [source file] [target file]"
    exit 0
fi

SOURCE="$1"
TARGET="$2"
BASE_DIR=$(dirname $(dirname $SOURCE))
SOURCE_LANG=$(dirname $SOURCE | awk -F/ '{print $NF}')
TARGET_LANG=$(dirname $TARGET | awk -F/ '{print $NF}')
#echo "SOURCE: $SOURCE"
#echo "TARGET: $TARGET"
echo "Detecting $SOURCE_LANG --> $TARGET_LANG in Dir: $BASE_DIR"

SOURCE_SENT="${SOURCE/.srt/.sent}"
TARGET_SENT="${TARGET/.srt/.sent}"
PATH_FILE="$BASE_DIR/${SOURCE_LANG}-${TARGET_LANG}-vec.path"
ALIGNMENTS_FILE="$BASE_DIR/${SOURCE_LANG}-${TARGET_LANG}-vec.txt"

echo "Extracting sentences..."
$SUBTITLE_REPO/scripts/srt2sent.py -f "$SOURCE" -i > "$SOURCE_SENT"
echo "$SOURCE_SENT"

$SUBTITLE_REPO/scripts/srt2sent.py -f "$TARGET" -i > "$TARGET_SENT"
echo "$TARGET_SENT"

if [ -z "$LASER" ]; then
    echo "You need to set LASER env var"
    exit 1
fi

echo "Overlapping, embedding and aligning"
$SUBTITLE_REPO/scripts/sent2path.sh "$SOURCE_SENT" "$TARGET_SENT" | grep -v "| INFO |" > "$PATH_FILE" 2>/dev/null
$SUBTITLE_REPO/scripts/path2align.py -s "$SOURCE_SENT" -t "$TARGET_SENT" -a "$PATH_FILE" > "$ALIGNMENTS_FILE" 2>/dev/null
echo "$PATH_FILE"
echo "$ALIGNMENTS_FILE"
