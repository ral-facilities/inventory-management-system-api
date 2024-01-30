# Inventory Management System

## How to Run

This is a Python microservice created using FastAPI and requires a MongoDB instance to run against.

### Prerequisites
- Docker installed (if you want to run the microservice inside Docker)
- Python 3.10 (or above) and MongoDB 6.0 installed on your machine if you are not using Docker
- [MongoDB Compass](https://www.mongodb.com/products/compass) installed (if you want to interact with the database using a GUI)
- This repository cloned

### Docker Setup
The easiest way to run the application with Docker for local development is using the `docker-compose.yml` file. It is
configured to spin up a MongoDB instance that can be accessed at `localhost:27017` using `root` as the username and
`example` as the password. It also starts the application in a reload mode using the `Dockerfile`. Use the `Dockerfile`
or `Dockerfile.prod` to run just the application itself in a container. The former is for local development  and must
not be used in production.

Ensure that Docker is installed and running on your machine before proceeding.

1. Create a `.env` file alongside the `.env.example` file. Use the example file as a reference and modify the values accordingly.
    ```bash
    cp .env.example .env
    ```

2. Create a `logging.ini` file alongside the `logging.example.ini` file. Use the example file as a reference and modify it accordingly:
    ```bash
    cp logging.example.ini logging.ini
    ```

3. Create a `keys` directory in the root of the project directory and inside it create a copy of the public key generated by the authentication component. This is needed for decoding of JWT access tokens signed by the corresponding private key.


#### Using Docker Compose File

1. Build and start the Docker containers:
    ```bash
    docker-compose up
    ```
   The microservice should now be running inside Docker at http://localhost:8000 and its Swagger UI could be accessed
   at http://localhost:8000/docs. A MongoDB instance should also be running at http://localhost:27017.

#### Using Dockerfiles

1. Build an image using either the `Dockerfile` or `Dockerfile.prod` from the root of the project directory:
    ```bash
    docker build -f Dockerfile.prod -t ims_api_image .
    ```

2. Start the container using the image built and map it to port `8000` locally:
    ```bash
    docker run -p 8000:8000 --name ims_api_container ims_api_image
    ```
   or with values for the environment variables:
    ```bash
    docker run -p 8000:8000 --name ims_api_container --env DATABASE__NAME=test-ims ims_api_image
    ```
   The microservice should now be running inside Docker at http://localhost:8000 and its Swagger UI could be accessed
   at http://localhost:8000/docs.

### Local Setup

Ensure that MongoDB is installed and running on your machine before proceeding.

1. Create a Python virtual environment and activate it in the root of the project directory:
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```
2. Install the required dependencies using pip:
    ```bash
    pip install .[dev]
    ```
3. Create a `.env` file using the `.env.example` file and modify the values inside accordingly.
4. Create a `logging.ini` file using the `logging.example.ini` file and modify it accordingly.
5. Start the microservice using Uvicorn:
    ```bash
    uvicorn inventory_management_system_api.main:app --log-config inventory_management_system_api/logging.ini --reload
    ```
   The microservice should now be running locally at http://localhost:8000. The Swagger UI can be accessed
   at http://localhost:8000/docs.
6. To run the unit tests, run :
   ```bash
   AUTHENTICATION__PUBLIC_KEY_PATH="./test/keys/jwt-key.pub" pytest test/unit/
   ```
7. To run the e2e tests, run:
   ```bash
   DATABASE__NAME="test-ims" AUTHENTICATION__PUBLIC_KEY_PATH="./test/keys/jwt-key.pub" pytest test/e2e/
   ```
