#!/bin/sh
# Re-runs single load levels (used when the laptop slept during a run).
#   caffeinate -i ./loadtest/rerun.sh event_search:200 login:300 ...
set -e
cd "$(dirname "$0")/.."
backend/.venv/bin/python loadtest/prepare_data.py
for spec in "$@"; do
  name=${spec%%:*}; level=${spec##*:}
  case $name in
    login) props="-Jlogin_threads=$level -Jramp=2 -Jcrud_loops=5" ;;
    job_search) props="-Jsearch_threads=$level -Jramp=2 -Jcrud_loops=20" ;;
    application) props="-Japply_threads=$level -Jramp=2" ;;
    event_search) props="-Jevent_threads=$level -Jramp=2 -Jcrud_loops=20" ;;
  esac
  echo "=== $name @ $level users"
  jmeter -n -t loadtest/p4_handshake.jmx -Jlevel="$level" -Jdata_dir=loadtest/data -Jresume=loadtest/data/resume.pdf \
    -Jjmeter.save.saveservice.output_format=csv $props -l "loadtest/results/${name}_${level}.jtl.new" > "loadtest/results/${name}_${level}.log" 2>&1
  mv "loadtest/results/${name}_${level}.jtl.new" "loadtest/results/${name}_${level}.jtl"
  grep "summary =" "loadtest/results/${name}_${level}.log"
done
