from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.common.error_handlers import register_error_handlers
from app.api.v1 import auth, customer, user, supplier, category

app = FastAPI(title="Power Genix", version="1.0.0")

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    # "https://dev-app.modernremodelingmd.com",
    # "https://app.modernremodelingmd.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

# Register API routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(user.router, prefix="/api/v1/users", tags=["users"])
app.include_router(
    supplier.router, prefix="/api/v1/suppliers", tags=["suppliers"])
app.include_router(
    customer.router, prefix="/api/v1/customers", tags=["customers"])
app.include_router(
    category.router, prefix="/api/v1/categories", tags=["categories"])
app.include_router(
    category.router, prefix="/api/v1/items", tags=["items"])


@app.get("/")
def read_root():
    return {"message": "Welcome to the Power Genxis APIs!"}
