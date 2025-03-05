# Inventory Management System API

This is a Python microservice created using FastAPI that provides a REST API for the Inventory Management System.

## How to Run

This microservice requires a MongoDB instance to run against.

### Prerequisites

- Docker and Docker Compose installed (if you want to run the microservice inside Docker)
- Python 3.12 and MongoDB 7.0 installed on your machine (if you are not using Docker)
- Public key (must be OpenSSH encoded) to decode JWT access tokens (if JWT authentication/authorization is enabled)
- [MongoDB Compass](https://www.mongodb.com/products/compass) installed (if you want to interact with the database using
  a GUI)
- This repository cloned

### Docker Setup

Ensure that Docker is installed and running on your machine before proceeding.

1. Create a `.env` file alongside the `.env.example` file. Use the example file as a reference and modify the values
   accordingly.

   ```bash
   cp inventory_management_system_api/.env.example inventory_management_system_api/.env
   ```

2. Create a `logging.ini` file alongside the `logging.example.ini` file. Use the example file as a reference and modify
   it accordingly:

   ```bash
   cp inventory_management_system_api/logging.example.ini inventory_management_system_api/logging.ini
   ```

3. Create a keyfile for mongodb to use for replica sets

   ```bash
   openssl rand -base64 756 > ./mongodb/keys/rs_keyfile
   chmod 0400 ./mongodb/keys/rs_keyfile
   sudo chown 999:999 ./mongodb/keys/rs_keyfile
   ```

4. (**Required only if JWT Auth is enabled**) Create a `keys` directory in the root of the project directory and inside
   it create a copy of the public key generated by the authentication component. This is needed for decoding of JWT
   access tokens signed by the corresponding private key.

#### Using `docker-compose.yml`

The easiest way to run the application with Docker for local development is using the `docker-compose.yml` file. It is
configured to spin up a MongoDB instance that can be accessed at `localhost:27017` using `root` as the username and
`example` as the password. It also starts the application in a reload mode using the `Dockerfile`.

1. Build and start the Docker containers:

   ```bash
   docker-compose up
   ```

   The microservice should now be running inside Docker at http://localhost:8000 and its Swagger UI could be accessed
   at http://localhost:8000/docs. A MongoDB instance should also be running at http://localhost:27017.

2. Follow the [post setup instructions](#post-setup-instructions)

#### Using `Dockerfile`

Use the `Dockerfile` to run just the application itself in a container. Use this only for local development (not
production)!

1. Build an image using the `Dockerfile` from the root of the project directory:

   ```bash
   docker build -f Dockerfile -t inventory_management_system_api_image .
   ```

2. Start the container using the image built and map it to port `8000` locally (please note that the public key volume
   is only needed if JWT Auth is enabled):

   ```bash
   docker run -p 8000:8000 --name inventory_management_system_api_container -v ./keys/jwt-key.pub:/inventory-management-system-api-run/keys/jwt-key.pub inventory_management_system_api_image
   ```

   or with values for the environment variables:

   ```bash
   docker run -p 8000:8000 --name inventory_management_system_api_container --env DATABASE__NAME=ims -v ./keys/jwt-key.pub:/inventory-management-system-api-run/keys/jwt-key.pub inventory_management_system_api_image
   ```

   The microservice should now be running inside Docker at http://localhost:8000 and its Swagger UI could be accessed
   at http://localhost:8000/docs.

3. Follow the [post setup instructions](#post-setup-instructions)

#### Using `Dockerfile.prod`

Use the `Dockerfile.prod` to run just the application itself in a container. This can be used for production.

1. Build an image using the `Dockerfile.prod` from the root of the project directory:

   ```bash
   docker build -f Dockerfile.prod -t inventory_management_system_api_image .
   ```

2. Start the container using the image built and map it to port `8000` locally:

   ```bash
   docker run -p 8000:8000 --name inventory_management_system_api_container -v ./keys/jwt-key.pub:/inventory-management-system-api-run/keys/jwt-key.pub inventory_management_system_api_image
   ```

   or with values for the environment variables:

   ```bash
   docker run -p 8000:8000 --name inventory_management_system_api_container --env DATABASE__NAME=test-ims -v ./keys/jwt-key.pub:/inventory-management-system-api-run/keys/jwt-key.pub inventory_management_system_api_image
   ```

   The microservice should now be running inside Docker at http://localhost:8000 and its Swagger UI could be accessed
   at http://localhost:8000/docs.

3. Follow the [post setup instructions](#post-setup-instructions)

### Local Setup

Ensure that Python is installed on your machine before proceeding.

1. Create a Python virtual environment and activate it in the root of the project directory:

   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

2. Install the required dependencies using pip:

   ```bash
   pip install .[dev]
   ```

3. Create a `.env` file alongside the `.env.example` file. Use the example file as a reference and modify the values
   accordingly.

   ```bash
   cp inventory_management_system_api/.env.example inventory_management_system_api/.env
   ```

4. Create a `logging.ini` file alongside the `logging.example.ini` file. Use the example file as a reference and modify
   it accordingly:

   ```bash
   cp inventory_management_system_api/logging.example.ini inventory_management_system_api/logging.ini
   ```

5. Create a keyfile for MongoDB to use for replica sets

   ```bash
   openssl rand -base64 756 > ./mongodb/keys/rs_keyfile
   sudo chmod 0400 ./mongodb/keys/rs_keyfile
   sudo chown 999:999 ./mongodb/keys/rs_keyfile
   ```

6. (**Required only if JWT Auth is enabled**) Create a `keys` directory in the root of the project directory and inside
   it create a copy of the public key generated by the authentication component. This is needed for decoding of JWT
   access tokens signed by the corresponding private key.

7. Start the microservice using FastAPI's CLI:

   ```bash
   fastapi dev inventory_management_system_api/main.py
   ```

   The microservice should now be running locally at http://localhost:8000. The Swagger UI can be accessed
   at http://localhost:8000/docs.

8. Follow the [post setup instructions](#post-setup-instructions)

9. To run the unit tests, run :

   ```bash
   pytest -c test/pytest.ini test/unit/
   ```

10. To run the e2e tests, run:

```bash
pytest -c test/pytest.ini test/e2e/
```

11. To run all the tests, run:

```bash
pytest -c test/pytest.ini test/
```

## Post setup instructions

When running for the first time there are a few extra steps required to setup the database. These instructions assume the database is running via docker, although the commands themselves can be adapted for a separate instance by removing the docker parts.

### Setting up the database

#### Using dev_cli

For development the easiest way to setup the database is to use the included dev_cli script assuming you are using Linux. To initialise the database use

```bash
python ./scripts/dev_cli.py db-init
```

#### Manually

#### Initialising the replica set

For development replica sets are required to be able to use transactions. Once the mongodb instance is running use `mongosh` to login and run

```bash
rs.initiate( {
   _id : "rs0",
   members: [
      { _id: 0, host: "<hostname>:27017" }
   ]
})
```

replacing `<hostname>` with the actual hostname for the replica set.

For docker you may use

```bash
docker exec -i ims_api_mongodb_container mongosh --username 'root' --password 'example' --authenticationDatabase=admin --eval "rs.initiate({ _id : 'rs0', members: [{ _id: 0, host: 'ims_api_mongodb_container:27017' }]})"
```

### Using mock data for testing [Optional]

#### Populating the database

The simplest way to populate the database with mock data is to use the already created database dump. If using docker for development you may use

```bash
python ./scripts/dev_cli.py db-import
```

to populate the database with mock data.

If you wish to do this manually the full command is

```bash
docker exec -i ims_api_mongodb_container mongorestore --username "root" --password "example" --authenticationDatabase=admin --db ims --archive < ./data/mock_data.dump
```

Otherwise there is a script to generate mock data for testing purposes given in `./scripts/generate_mock_data.py`. To use it from your development environment first ensure the API is running and then execute it with

```bash
python ./scripts/generate_mock_data.py
```

## Generating new mock data

The easiest way to generate new mock data assuming you are using Linux is via the dev_cli script. To do this use

```bash
python ./scripts/dev_cli.py db-generate
```

This will clear the database, import the default data e.g. units and then generate mock data. If the `generate_mock_data.py` script is changed, or if there are database model changes please use

```bash
python ./scripts/dev_cli.py db-generate -d
```

to update the `./data/mock_data.dump` file and commit the changes.

### Manually

The parameters at the top of the `generate_mock_data.py` file can be used to change the generated data. NOTE: This script will simply add to the existing database instance. So if you wish to update the `mock_data.dump`, you should first clear the database e.g. using

```bash
docker exec -i ims_api_mongodb_container mongosh ims --username "root" --password "example" --authenticationDatabase=admin --eval "db.dropDatabase()"
```

Then generate the mock data using

```bash
python ./scripts/generate_mock_data.py
```

and then update the `./data/mock_data.dump` file using `mongodump` via

```bash
docker exec -i ims_api_mongodb_container mongodump --username "root" --password "example" --authenticationDatabase=admin --db ims --archive > ./data/mock_data.dump
```

## Notes

### Application Configuration

The configuration for the application is handled
using [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/). It allows for loading config
values from environment variables or the `.env` file. Please note that even when using the `.env` file, Pydantic will
still read environment variables as well as the `.env` file, environment variables will always take priority over
values loaded from the `.env` file.

Listed below are the environment variables supported by the application.

| Environment Variable                          | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Mandatory                 | Default Value                                         |
|-----------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------| ------------------------- | ----------------------------------------------------- |
| `API__TITLE`                                  | The title of the API which is added to the generated OpenAPI.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | No                        | `Inventory Management System API`                     |
| `API__DESCRIPTION`                            | The description of the API which is added to the generated OpenAPI.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | No                        | `This is the API for the Inventory Management System` |
| `API__ROOT_PATH`                              | (If using a proxy) The path prefix handled by a proxy that is not seen by the app.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | No                        | ` `                                                   |
| `API__ALLOWED_CORS_HEADERS`                   | The list of headers that are allowed to be included in cross-origin requests.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Yes                       |                                                       |
| `API__ALLOWED_CORS_ORIGINS`                   | The list of origins (domains) that are allowed to make cross-origin requests.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Yes                       |                                                       |
| `API__ALLOWED_CORS_METHODS`                   | The list of methods that are allowed to be used to make cross-origin requests.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Yes                       |                                                       |
| `AUTHENTICATION__ENABLED`                     | Whether JWT auth is enabled.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Yes                       |                                                       |
| `AUTHENTICATION__PUBLIC_KEY_PATH`             | The path to the public key to be used for decoding JWT access token signed by the corresponding private key.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | If JWT auth enabled       |                                                       |
| `AUTHENTICATION__JWT_ALGORITHM`               | The algorithm to use to decode the JWT access token.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | If JWT auth enabled       |                                                       |
| `DATABASE__PROTOCOL`                          | The protocol component (i.e. `mongodb`) to use for the connection string for the `MongoClient` to connect to the database.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Yes                       |                                                       |
| `DATABASE__USERNAME`                          | The database username to use for the connection string for the `MongoClient` to connect to the database.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Yes                       |                                                       |
| `DATABASE__PASSWORD`                          | The database password to use for the connection string for the `MongoClient` to connect to the database.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Yes                       |                                                       |
| `DATABASE__HOST_AND_OPTIONS`                  | The host (and optional port number) component as well specific options (if any) to use for the connection string for the `MongoClient` to connect to the database. The host component is the name or IP address of the host where the `mongod` instance is running, whereas the options are `<name>=<value>` pairs (i.e. `?authMechanism=SCRAM-SHA-256&authSource=admin`) specific to the connection.<br> <ul><li>For a replica set `mongod` instance(s), specify the hostname(s) and any options as listed in the replica set configuration - `prod-mongodb-1:27017,prod-mongodb-2:27017,prod-mongodb-3:27017/?authMechanism=SCRAM-SHA-256&authSource=admin`</li><li>For a standalone `mongod` instance, specify the hostname and any options - `prod-mongodb:27017/?authMechanism=SCRAM-SHA-256&authSource=admin`</li></ul> | Yes                       |                                                       |
| `DATABASE__NAME`                              | The name of the database to use for the `MongoClient` to connect to the database.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Yes                       |                                                       |
| `OBJECT_STORAGE__ENABLED`                     | Whether the API is using [Object Storage API](https://github.com/ral-facilities/object-storage-api) to allow attachments and image uploads for the catalogue items, items, and systems.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Yes                       |                                                       |
| `OBJECT_STORAGE__API_REQUEST_TIMEOUT_SECONDS` | The maximum number of seconds that the request should wait for a reponse from the Object Storage API before timing out.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | If Object Storage enabled |                                                       |
| `OBJECT_STORAGE__API_URL`                     | The URL of the Object Storage API.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | If Object Storage enabled |                                                       |

### JWT Authentication/Authorization

This microservice supports JWT authentication/authorization and this can be enabled or disabled by setting
the `AUTHENTICATION__ENABLED` environment variable to `True` or `False`. When enabled, all the endpoints require a JWT
access token to be supplied. This ensures that only authenticated and authorized users can access the resources. To
decode the JWT access token, the application needs the public key that corresponding to the private key used for
encoding the token. Once the JWT access token is decoded successfully, it checks that it has a `username` in the
payload, and it has not expired. This means that any microservice can be used to generate JWT access tokens so long as
it meets the above criteria. The [LDAP-JWT Authentication Service](https://github.com/ral-facilities/ldap-jwt-auth) is
a microservice that provides user authentication against an LDAP server and returns a JWT access token.

### Migrations

#### Adding a migration

To add a migration first use

```bash
ims-migrate create <migration_name> <migration_description>
```

to create a new one inside the `inventory_management_system/migrations/scripts` directory. Then add the code necessary
to perform the migration. See `_example_migration.py` for an example on how to implement one.

#### Performing forward migrations

Before performing a migration you can first check the current status of the database and any outstanding migrations
using

```bash
ims-migrate status
```

or in Docker

```bash
docker exec -it inventory_management_system_api_container ims-migrate status
```

Then to perform all outstanding migrations up to the latest one use

```bash
ims-migrate forward latest
```

You may also specify a specific migration name to apply instead which will apply all migrations between the current
applied one and the specified one. A prompt will be shown to ensure the migrations being applied are sensible.

#### Performing backward migrations

To revert the database by performing backwards migrations you can first use

```bash
ims-migrate status
```

to check the current status of the database and available migrations and then use

```bash
ims-migrate backward <migration_name>
```

to perform all backward migrations to get from the current database state back to the state prior to the chosen
migration name (i.e. it also performs the backward migration for the given migration name).

#### Forcing migration state

If for some reason the migration state is different to what you expect it may be forced via

```bash
ims-migrate set <migration_name>
```

This is already set to `latest` automatically when using the `dev_cli` to regenerate mock data so that the dump retains
the expected state.
