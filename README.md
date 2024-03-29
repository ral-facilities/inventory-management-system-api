# Inventory Management System

## How to Run

This is a Python microservice created using FastAPI and requires a MongoDB instance to run against.

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

3. (**Required only if JWT Auth is enabled**) Create a `keys` directory in the root of the project directory and inside
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
   docker run -p 8000:8000 --name inventory_management_system_api_container -v ./keys/jwt-key.pub:/inventory-management-system-api-run/keys/jwt-key.pub -v ./logs:/inventory-management-system-api-run/logs inventory_management_system_api_image
   ```
   or with values for the environment variables:
   ```bash
   docker run -p 8000:8000 --name inventory_management_system_api_container --env DATABASE__NAME=test-ims -v ./keys/jwt-key.pub:/inventory-management-system-api-run/keys/jwt-key.pub -v ./logs:/inventory-management-system-api-run/logs inventory_management_system_api_image
   ```
   The microservice should now be running inside Docker at http://localhost:8000 and its Swagger UI could be accessed
   at http://localhost:8000/docs.

#### Using `Dockerfile.prod`

Use the `Dockerfile.prod` to run just the application itself in a container. This can be used for production.

1. While in root of the project directory, change the permissions of the `logs` directory so that it is writable by
   other users. This allows the container to save the application logs to it.

   ```bash
   sudo chmod -R 0777 logs/
   ```

2. Build an image using the `Dockerfile.prod` from the root of the project directory:

   ```bash
   docker build -f Dockerfile.prod -t inventory_management_system_api_image .
   ```

3. Start the container using the image built and map it to port `8000` locally:
   ```bash
   docker run -p 8000:8000 --name inventory_management_system_api_container -v ./keys/jwt-key.pub:/inventory-management-system-api-run/keys/jwt-key.pub -v ./logs:/inventory-management-system-api-run/logs inventory_management_system_api_image
   ```
   or with values for the environment variables:
   ```bash
   docker run -p 8000:8000 --name inventory_management_system_api_container --env DATABASE__NAME=test-ims -v ./keys/jwt-key.pub:/inventory-management-system-api-run/keys/jwt-key.pub -v ./logs:/inventory-management-system-api-run/logs inventory_management_system_api_image
   ```
   The microservice should now be running inside Docker at http://localhost:8000 and its Swagger UI could be accessed
   at http://localhost:8000/docs.

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

5. (**Required only if JWT Auth is enabled**) Create a `keys` directory in the root of the project directory and inside
   it create a copy of the public key generated by the authentication component. This is needed for decoding of JWT
   access tokens signed by the corresponding private key.

6. Start the microservice using Uvicorn:

   ```bash
   uvicorn inventory_management_system_api.main:app --log-config inventory_management_system_api/logging.ini --reload
   ```

   The microservice should now be running locally at http://localhost:8000. The Swagger UI can be accessed
   at http://localhost:8000/docs.

7. To run the unit tests, run :

   ```bash
   pytest -c test/pytest.ini test/unit/
   ```

8. To run the e2e tests, run:

   ```bash
   pytest -c test/pytest.ini test/e2e/
   ```

9. To run all the tests, run:
   ```bash
   pytest -c test/pytest.ini test/
   ```

## Notes

### Application Configuration

The configuration for the application is handled
using [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/). It allows for loading config
values from environment variables or the `.env` file. Please note that even when using the `.env` file, Pydantic will
still read environment variables as well as the `.env` file, environment variables will always take priority over
values loaded from the `.env` file.

Listed below are the environment variables supported by the application.

| Environment Variable              | Description                                                                                                  | Mandatory           | Default Value                                         |
|-----------------------------------|--------------------------------------------------------------------------------------------------------------|---------------------|-------------------------------------------------------|
| `API__TITLE`                      | The title of the API which is added to the generated OpenAPI.                                                | No                  | `Inventory Management System API`                     |
| `API__DESCRIPTION`                | The description of the API which is added to the generated OpenAPI.                                          | No                  | `This is the API for the Inventory Management System` |
| `API__ROOT_PATH`                  | (If using a proxy) The path prefix handled by a proxy that is not seen by the app.                           | No                  | ` `                                                   |
| `API__ALLOWED_CORS_HEADERS`       | The list of headers that are allowed to be included in cross-origin requests.                                | Yes                 |                                                       |
| `API__ALLOWED_CORS_ORIGINS`       | The list of origins (domains) that are allowed to make cross-origin requests.                                | Yes                 |                                                       |
| `API__ALLOWED_CORS_METHODS`       | The list of methods that are allowed to be used to make cross-origin requests.                               | Yes                 |                                                       |
| `AUTHENTICATION__ENABLED`         | Whether JWT auth is enabled.                                                                                 | Yes                 |                                                       |
| `AUTHENTICATION__PUBLIC_KEY_PATH` | The path to the public key to be used for decoding JWT access token signed by the corresponding private key. | If JWT auth enabled |                                                       |
| `AUTHENTICATION__JWT_ALGORITHM`   | The algorithm to use to decode the JWT access token.                                                         | If JWT auth enabled |                                                       |
| `DATABASE__PROTOCOL`              | The protocol of the database to use for the `MongoClient` to connect to the database.                        | Yes                 |                                                       |
| `DATABASE__USERNAME`              | The username of the database user for the `MongoClient` to connect to the database.                          | Yes                 |                                                       |
| `DATABASE__PASSWORD`              | The password of the database user for the `MongoClient` to connect to the database.                          | Yes                 |                                                       |
| `DATABASE__HOSTNAME`              | The hostname of the database to use for the `MongoClient` to connect to the database.                        | Yes                 |                                                       |
| `DATABASE__PORT`                  | The port of the database to use for the `MongoClient` to connect to the database.                            | Yes                 |                                                       |
| `DATABASE__NAME`                  | The name of the database to use for the `MongoClient` to connect to the database.                            | Yes                 |                                                       |

### JWT Authentication/Authorization

This microservice supports JWT authentication/authorization and this can be enabled or disabled by setting
the `AUTHENTICATION__ENABLED` environment variable to `True` or `False`. When enabled, all the endpoints require a JWT
access token to be supplied. This ensures that only authenticated and authorized users can access the resources. To
decode the JWT access token, the application needs the public key that corresponding to the private key used for
encoding the token. Once the JWT access token is decoded successfully, it checks that it has a `username` in the
payload, and it has not expired. This means that any microservice can be used to generate JWT access tokens so long as
it meets the above criteria. The [LDAP-JWT Authentication Service](https://github.com/ral-facilities/ldap-jwt-auth) is
a microservice that provides user authentication against an LDAP server and returns a JWT access token.

### Adding units

Units should be added to the MongoDB database using `mongoimport` on the provided units file found at
`/data/units.json`. If adding more units to this file, ensure the `_id` values are valid `ObjectId`'s.

#### Updating a local MongoDB instance

To update the list of units, replacing all existing with the contents of the `./data/units.json` file use the command

```bash
mongoimport --username 'root' --password 'example' --authenticationDatabase=admin --db ims --collection units --type=json --jsonArray --drop ./data/units.json
```

from the root directory of this repo, replacing the username and password as appropriate.

#### Updating a MongoDB instance running in a docker container

When running using docker first locate the running container with the instance of MongoDB using `docker ps`. Then use

```bash
docker exec -i CONTAINER_ID mongoimport --username 'root' --password 'example' --authenticationDatabase=admin --db ims --collection units --type=json --jsonArray --drop < ./data/units.json
```

Replacing `CONTAINER_ID` with the actual container ID of the MongoDB instance.

### Using mock data for testing

#### Populating the database

The simplest way to populate the database with mock data is to use the already created database dump. If using docker you can use the command

```bash
docker exec -i CONTAINER_ID mongorestore --username "root" --password "example" --authenticationDatabase=admin --db ims --archive < ./data/mock_data.dump
```

to populate the database with mock data.

#### Generating new data

There is a script to generate mock data for testing purposes given in `./scripts/generate_mock_data.py`. To use it from your development environment first ensure the API is running and then execute it with

```bash
python ./scripts/generate_mock_data.py
```

The parameters at the top of the file can be used to change the generated data. NOTE: This script will simply add to the existing database instance. So if you wish to update the `mock_data.dump`, you should first clear the database e.g. using

```bash
docker exec -i CONTAINER_ID mongosh ims --username "root" --password "example" --authenticationDatabase=admin --eval "db.dropDatabase()"
```

Then generate the mock data, import the units and then save the changes using `mongodump` via

```bash
docker exec -i CONTAINER_ID mongodump --username "root" --password "example" --authenticationDatabase=admin --db ims --archive > ./data/mock_data.dump
```
