#!/bin/bash
# Fetches Mortal analysis JSON from an mjai.ekyu.moe viewer link.
# Usage: ./mj_fetch.sh 'https://mjai.ekyu.moe/killerducky/?data=/report/HASH.json'

url="$1"
if [[ -z "$url" ]]; then
    echo "Usage: $0 <mjai-viewer-url>" >&2
    exit 1
fi

data_path="${url#*?data=}"
download_url="https://mjai.ekyu.moe${data_path}"

wget -P "$(dirname "$0")" "$download_url"
