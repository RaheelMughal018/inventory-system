# Inventory Backend

A Flask-based backend service for managing suppliers in an inventory system.

---

## Table of Contents

- [Features](#features)
- [API Endpoints](#api-endpoints)
- [Environment Setup](#environment-setup)
- [Database Migrations](#database-migrations)
- [Running the Server](#running-the-server)
- [Testing the API](#testing-the-api)
- [Seeding the Database](#seeding-the-database)
- [Project Structure](#project-structure)

---

## Features

- Supplier CRUD operations (Create, Read, Update, Delete)
- RESTful API with JSON responses
- SQLAlchemy ORM with MySQL
- Flask-Migrate for database migrations
- Logging and error handling

---

## API Endpoints

All endpoints are prefixed with `/api/suppliers`.

| Method | Endpoint                | Description                | Request Body (JSON)         | Response Example |
|--------|------------------------ |---------------------------|-----------------------------|-----------------|
| GET    | `/api/suppliers/`       | List all suppliers         | -                           | `{ "success": true, "data": [...] }` |
| POST   | `/api/suppliers/`       | Create a new supplier      | `{ "name": "...", "phone": "...", "address": "..." }` | `{ "success": true, "data": {...} }` |
| PUT    | `/api/suppliers/<id>`   | Update a supplier          | `{ "name": "...", "phone": "...", "address": "..." }` | `{ "success": true, "data": {...} }` |
| DELETE | `/api/suppliers/<id>`   | Delete a supplier          | -                           | `{ "success": true, "data": {...} }` |

---

## Environment Setup

1. **Clone the repository:**
    ```bash
    git clone <repo-url>
    cd inventory-be
    ```

2. **Create a virtual environment:**
    ```bash
    python3.9 -m venv venv
    source venv/bin/activate
    ```

3. **Install dependencies:**
    ```bash
    pip install -r requirement.txt
    ```

4. **Set up environment variables:**
    - Copy `.env.example` to `.env` and update values as needed.
    ```bash
    cp .env.example .env
    ```

---

## Database Migrations

1. **Initialize migrations (first time only):**
    ```bash
    flask db init
    ```

2. **Generate a migration after model changes:**
    ```bash
    flask db migrate -m "Your migration message"
    ```

3. **Apply migrations:**
    ```bash
    flask db upgrade
    ```

---

## Running the Server

1. **Start the Flask server:**
    ```bash
    python run.py
    ```

2. The server will run at the URL specified in your `.env` (`LOCAL_URL`), e.g., [http://localhost:5000](http://localhost:5000).

---

## Testing the API

You can use [Postman](https://www.postman.com/) or `curl` to test the endpoints.

### Example: Create Supplier

```bash
curl -X POST http://localhost:5000/api/suppliers/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Acme Corp", "phone": "1234567890", "address": "123 Main St"}'
```

### Example: Get All Suppliers

```bash
curl http://localhost:5000/api/suppliers/
```

### Example: Update Supplier

```bash
curl -X PUT http://localhost:5000/api/suppliers/<supplier_id> \
  -H "Content-Type: application/json" \
  -d '{"name": "New Name"}'
```

### Example: Delete Supplier

```bash
curl -X DELETE http://localhost:5000/api/suppliers/<supplier_id>
```

---

## Seeding the Database

To populate the database with random suppliers for testing:

```bash
python seed.py
```

---

## Project Structure

```
inventory-be/
│
├── app/
│   ├── __init__.py
│   ├── models/
│   │   └── supplier.py
│   ├── routes/
│   │   └── suppliers.py
│   ├── services/
│   │   └── suppliers.py
│   ├── common/
│   │   ├── response.py
│   │   ├── error_handlers.py
│   │   └── logger.py
│   └── db/
│
├── migrations/
│   ├── env.py
│   ├── alembic.ini
│   └── ...
│
├── run.py
├── seed.py
├── requirement.txt
├── requirements-dev.txt
├── .env.example
├── .env
└── README.md
```

---

## License

MIT License

-