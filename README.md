# Inventory Management System

## How to Run

This is a Python microservice created using FastAPI and requires a MongoDB instance to run against. If you are using
Docker to run the application, the `docker-compose.yml file` has already been configured to start a MongoDB instance
that can be accessed at `localhost:27017` using `root` as the username and `example` as the password.

### Prerequisites
- Docker installed (if you want to run the microservice inside Docker)
- Python 3.10 (or above) and MongoDB 6.0 installed on your machine if you are not using Docker
- [MongoDB Compass](https://www.mongodb.com/products/compass) installed (if you want to interact with the database using a GUI)

### Docker Setup

1. Ensure that Docker is installed and running on your machine.
2. Clone the repository and navigate to the project directory:
    ```bash
    git clone git@github.com:ral-facilities/inventory-management-system-api.git
    cd inventory-management-system-api
3. Create a `logging.ini` file.
    ```bash
   cp logging.example.ini logging.ini
    ```

4. Build and start the Docker containers:
    ```bash
   docker-compose up
    ```
   The microservice should now be running inside Docker at http://localhost:8000. The Swagger UI can be accessed
   at http://localhost:8000/docs.

### Local Setup

1. Clone the repository and navigate to the project directory:
    ```bash
    git clone git@github.com:ral-facilities/inventory-management-system-api.git
    cd inventory-management-system-api
    ```
2. Create a Python virtual environment and activate it:
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```
3. Install the required dependencies using pip:
    ```bash
   pip install .[dev]
    ```
4. Create a `.env` file using the `.env.example` file and modify the values inside accordingly.
5. Create a `logging.ini` file using the `logging.example.ini` file and modify it accordingly.
6. Ensure that MongoDB is running locally. If it's not installed, you can follow the official MongoDB installation guide
   for your operating system.
7. Start the microservice using Uvicorn from the project directory:
    ```bash
   uvicorn inventory_management_system_api.main:app --log-config inventory_management_system_api/logging.ini --reload
    ```
   The microservice should now be running locally at http://localhost:8000. The Swagger UI can be accessed
   at http://localhost:8000/docs.
8. To run the unit tests, run :
   ```bash
   pytest test/unit/
   ```
9. To run the e2e tests, ensure that MongoDB is running locally and run:
   ```bash
   DATABASE__NAME="test-ims" pytest test/e2e/
   ```
