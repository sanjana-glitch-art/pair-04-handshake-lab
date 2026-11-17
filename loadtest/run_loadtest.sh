#!/bin/sh
# Runs every load level against the gateway (default http://localhost:9040).
#   ./loadtest/run_loadtest.sh            CRUD levels 100..500 and assistant 5..50
#   ./loadtest/run_loadtest.sh crud       CRUD only
#   ./loadtest/run_loadtest.sh assistant  assistant only
# Raw results go to loadtest/results/*.jtl; analyze_results.py summarizes them.
set -e
cd "$(dirname "$0")/.."
PLAN=loadtest/p4_handshake.jmx
OUT=loadtest/results
mkdir -p "$OUT"
WHAT=${1:-all}

run() {  # name level extra-props...
  name=$1; level=$2; shift 2
  rm -f "$OUT/${name}_${level}.jtl"
  echo "=== $name @ $level users"
  jmeter -n -t "$PLAN" -Jlevel="$level" -Jdata_dir=loadtest/data -Jresume=loadtest/data/resume.pdf \
    -Jjmeter.save.saveservice.output_format=csv "$@" -l "$OUT/${name}_${level}.jtl" > "$OUT/${name}_${level}.log" 2>&1
  tail -3 "$OUT/${name}_${level}.log" | grep -E "summary =" || true
}

if [ "$WHAT" = all ] || [ "$WHAT" = crud ]; then
  backend/.venv/bin/python loadtest/prepare_data.py
  for level in 100 200 300 400 500; do
    run login "$level" -Jlogin_threads="$level" -Jramp=2 -Jcrud_loops=5   # bcrypt-bound: 5 sign-ins per user
    run job_search "$level" -Jsearch_threads="$level" -Jramp=2 -Jcrud_loops=20
    run application "$level" -Japply_threads="$level" -Jramp=2
    run event_search "$level" -Jevent_threads="$level" -Jramp=2 -Jcrud_loops=20
  done
fi

if [ "$WHAT" = all ] || [ "$WHAT" = assistant ]; then
  for level in 5 10 20 50; do
    run assistant "$level" -Jassistant_threads="$level" -Jramp=1 -Jresponse_timeout=900000
  done
fi
