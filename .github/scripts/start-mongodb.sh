# Generate keyfile for replica sets and set file permissions
echo "Generating keyfile"
openssl rand -base64 756 > ./mongodb/keys/rs_keyfile
sudo chmod 0400 ./mongodb/keys/rs_keyfile
sudo chown 999:999 ./mongodb/keys/rs_keyfile

# Setup mongodb and wait 10 seconds for it to initialise
echo "Starting MongoDB"
docker compose pull mongo-db
docker compose up -d --wait --wait-timeout 30 mongo-db
sleep 10

echo "Initialising MongoDB replica set"
docker exec -i mongodb_container mongosh --username 'root' --password 'example' --authenticationDatabase=admin --eval "rs.initiate({ _id : 'rs0', members: [{ _id: 0, host: 'localhost:27017' }]})"

# Fix permission issue when setting up python afterwards, it seems to try and access the data directory but doesn't
# have permission to once edited
sudo chmod -R 777 ./mongodb/data

echo "::group::Checking replica set status"
docker exec -i mongodb_container mongosh --username 'root' --password 'example' --authenticationDatabase=admin --eval "rs.status()"
echo "::endgroup::"
