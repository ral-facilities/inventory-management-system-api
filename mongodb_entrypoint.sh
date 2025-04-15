#!/bin/bash

KEYFILE_PATH="/data/db/rs_keyfile"

# Generate the replica set keyfile if not already present
if [ ! -f "$KEYFILE_PATH" ]; then
  echo "Generating replica set keyfile..."
  openssl rand -base64 756 > "$KEYFILE_PATH"
  chmod 0400 "$KEYFILE_PATH"
  chown 999:999 "$KEYFILE_PATH"
fi

# Execute the standard entrypoint to start mongodb, but add the additional parameters to setup the replica set
# TODO: Put back in docker-compose?
echo "Starting MongoDB through default entrypoint..."
/usr/local/bin/docker-entrypoint.sh --replSet "rs0" --keyFile "$KEYFILE_PATH" "$@" &

# Wait for MongoDB to be ready to run commands on
echo "Waiting for Mongo to be ready..."
until mongosh --username 'root' --password 'example' --authenticationDatabase=admin --eval "db.adminCommand('ping')" > /dev/null 2>&1; do
  sleep 1
done

# Initialise replica sets if not already setup
if ! mongosh --username 'root' --password 'example' --authenticationDatabase=admin --quiet --eval "rs.status().ok" | grep -q '^1$'; then
  echo "Initializing replica set..."
  mongosh --username 'root' --password 'example' --authenticationDatabase=admin --eval 'rs.initiate({ _id: "rs0", members: [{ _id: 0, host: "localhost:27017" }] })'
fi

wait