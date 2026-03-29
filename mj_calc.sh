#!/bin/bash
# mj_calc.sh — Mahjong game review calculator
# Usage:
#   ./mj_calc.sh         Calculate and fill SUMMARY/TOTAL for all games
#   ./mj_calc.sh calc    Same as above
#   ./mj_calc.sh new     Append a new blank game entry with today's date

DIR="$(cd "$(dirname "$0")" && pwd)"
FILE="$DIR/Mahjong Mistakes.txt"

if [[ ! -f "$FILE" ]]; then
    echo "Error: $FILE not found" >&2
    exit 1
fi

calc() {
    local tmp
    tmp=$(mktemp) || exit 1
    trap 'rm -f "$tmp"' EXIT

    awk '
BEGIN { n = split("1A 1B 1C 1D 1E 2A 2B 2C 3A 3B 3C 4A 4B 5A 5B", cats) }

function reset() {
    for (k in count) delete count[k]
    for (k in ev_sum) delete ev_sum[k]
    total = total_ev = total_turns = bang = q1 = q2 = q3 = 0
    in_game = buflen = last_content = 0
}

function emit() {
    printf "SUMMARY:"
    for (i = 1; i <= n; i++)
        if (count[cats[i]] > 0)
            printf " %s:%d(%.2f)", cats[i], count[cats[i]], ev_sum[cats[i]]
    print ""
    printf "TOTAL: %d mistakes, %.2f EV | ???:%d ??:%d ?:%d !:%d\n",
        total, total_ev, q3, q2, q1, bang
    if (total_turns > 0)
        printf "TURNS: %d | EV/Turn: %.4f\n", total_turns, total_ev / total_turns
}

function flush() {
    for (i = 1; i <= last_content; i++) print buf[i]
    print ""
    emit()
    print ""
}

{ gsub(/\r$/, "") }

in_game && /^(SUMMARY|TOTAL|TURNS):/ { next }

/^={6,}/ {
    if (in_game) flush()
    print; reset(); next
}

!in_game && /^Date:/ { in_game = 1 }

in_game {
    buf[++buflen] = $0
    if ($0 != "") last_content = buflen
    if (/^[ES][0-9]/ && match($1, /T[0-9]+$/))
        total_turns += substr($1, RSTART + 1) + 0
    if (/^[0-9]+ [!?]+ [0-9]+[A-Z]/) {
        count[$3]++; ev_sum[$3] += $4 + 0
        total++; total_ev += $4 + 0
        if ($2 == "?") q1++
        else if ($2 == "??") q2++
        else if ($2 == "???") q3++
        else if ($2 == "!") bang++
    }
    next
}

{ print }

END {
    if (in_game) {
        flush()
        print "======================================================================"
    }
}
' "$FILE" > "$tmp" && mv "$tmp" "$FILE"

    echo "Summaries updated."
}

new_game() {
    local date
    date=$(date +%Y-%m-%d)
    cat >> "$FILE" << EOF

Date: $date
Log:

E1
E2
E3
E4
S1
S2
S3
S4

SUMMARY:
TOTAL:

======================================================================
EOF
    echo "New game entry added for $date."
}

case "${1:-calc}" in
    calc) calc ;;
    new)  new_game ;;
    *)    echo "Usage: $0 [calc|new]" >&2; exit 1 ;;
esac
