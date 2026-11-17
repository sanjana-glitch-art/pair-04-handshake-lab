#!/bin/sh
# Creates every p4.* topic and its dead-letter topic (idempotent).
set -e
KT=/opt/kafka/bin/kafka-topics.sh
B=${BOOTSTRAP:-p4-kafka:9092}
for t in application.created application.updated application.status_changed \
         event.registration_created job.created assistant.interaction assistant.memory_consolidate; do
  $KT --bootstrap-server "$B" --create --if-not-exists --topic "p4.$t" --partitions 3 --replication-factor 1
  $KT --bootstrap-server "$B" --create --if-not-exists --topic "p4.$t.dlq" --partitions 1 --replication-factor 1
done
$KT --bootstrap-server "$B" --list | grep '^p4\.'
