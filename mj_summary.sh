#!/bin/bash
# Mahjong game review summary calculator
# Usage: ./mj_summary.sh game_log.txt
#
# Reads your game log and outputs:
#   SUMMARY line with per-category count(total_ev)
#   TOTAL line with severity breakdown
#   TURNS + EV/Turn if turn counts are in round headers
#
# Turn count formats supported:
#   E1T13       (compact)
#   E2 Turns 10 (spelled out)

file="${1:?Usage: $0 <game_log.txt>}"

awk '
BEGIN {
    split("1A 1B 1C 1D 1E 2A 2B 2C 3A 3B 3C 4A 4B 5A 5B", cats, " ")
    ncats = 15
}

/^[ES][0-9]/ {
    if (match($1, /T[0-9]+$/))
        total_turns += substr($1, RSTART+1) + 0
    for (i=1; i<=NF; i++)
        if ($i == "Turns" && i < NF) {
            total_turns += $(i+1) + 0
            break
        }
}

/^[0-9]+[\.]? [!?]+ [0-9]+[A-Z]/ {
    sub(/\./, "", $1)
    sev = $2; cat = $3; ev = $4 + 0

    count[cat]++; ev_sum[cat] += ev
    total++; total_ev += ev

    if      (sev == "!")   bang++
    else if (sev == "?")   q1++
    else if (sev == "??")  q2++
    else if (sev == "???") q3++
}

END {
    printf "SUMMARY:"
    for (i=1; i<=ncats; i++) {
        c = cats[i]
        if (count[c] > 0)
            printf " %s:%d(%.2f)", c, count[c], ev_sum[c]
    }
    print ""
    printf "TOTAL: %d mistakes, %.2f EV | ???:%d ??:%d ?:%d !:%d\n",
        total, total_ev, q3, q2, q1, bang
    if (total_turns > 0)
        printf "TURNS: %d | EV/Turn: %.4f\n", total_turns, total_ev / total_turns
    else
        print "TURNS: (add turn counts to headers, e.g. E1T13 or E1 Turns 13)"
}
' "$file"
