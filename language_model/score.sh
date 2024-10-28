#!/usr/bin/env bash

dir="$SUBTITLE_REPO/language_model/data"

if [ ! -s "$dir/predictions-spa.txt" ]; then
    fairseq-interactive \
        "$dir/preprocessed" \
        --source-lang="eng" \
        --target-lang="spa" \
        --path="./checkpoints/checkpoint_best.pt" \
        --gen-subset="test" \
        --beam=5 \
        --batch-size=256 \
        grep '^H-' | cut -c 3- | awk -F '\t' '{print $NF}' \
            > "$dir/predictions-spa.txt" \
            || exit 1
else
    echo "$dir/predictions-spa.txt exists."
    read -pr "Do you want to proceed?" confirm
    if [ "$confirm" != 'y' ]; then
        exit 0
    fi
fi

grep '^H-' "$dir/predictions-spa.txt" | \
    # strip the first 2 characters
    cut -c 3- | \
    # sort them numerically
    sort -n -k 1 | \
    # print only the last field
    awk -F '\t' '{print $NF}' | \
    # Remove whitespace and then replace underscores with whitespace (order here matters)
    sed -e 's/[[:space:]]*//g' -e 's/[▁_]/ /g' | \
    # Strip leading whitespace from the tokenization above and redirect to prediction file
    sed -e 's/^ //g' #> "${PRED_FILE}"