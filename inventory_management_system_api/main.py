
from fastapi import FastAPI

API_DESCRIPTION = "This is the API for the Inventory Management System"

app = FastAPI(title="Inventory Management System API", description=API_DESCRIPTION)

@app.get("/")
def read_root():
    return {"Title": "Inventory Management System API"}
