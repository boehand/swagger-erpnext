# swagger-erpnext

**Dynamic Swagger UI for ERPNext** — forked from [omkardarves/swagger](https://github.com/omkardarves/swagger) and extended with:

- Automatic CSRF token injection for all write requests
- DocType-specific endpoints with fully typed field schemas (configurable via Settings)
- A ready-to-use ERPNext app (`erpnext_api_docs`) with generic CRUD endpoints for every DocType

#### License: MIT

---

## Repository structure

```
swagger-erpnext/
├── swagger/                          # Swagger UI engine (this app)
│   ├── www/
│   │   ├── swagger.html              # Swagger UI page (CSRF token auto-injected)
│   │   └── swagger.py               # Frappe get_context() – reads CSRF token from session
│   ├── swagger_generator.py         # Builds swagger.json from api/ folders + DocType list
│   └── swagger_ui/
│       └── doctype/
│           ├── swagger_settings/    # Settings DocType (app name, auth mode, DocType list)
│           ├── swagger_doctype_entry/  # Child table for the DocType list
│           └── api_error_log/       # Error log DocType
│
└── apps/
    └── erpnext_api_docs/            # Custom ERPNext app – generic DocType CRUD API
        ├── setup.py / pyproject.toml / requirements.txt
        └── erpnext_api_docs/
            ├── hooks.py
            ├── api/
            │   └── doctype.py       # @frappe.whitelist() CRUD endpoints
            └── basemodels/
                └── doctype.py       # Pydantic v2 models
```

---

## Features

- **Automatic Swagger UI generation** — scans the `api/` folders of all installed apps and builds a live OpenAPI 3.0 spec
- **CSRF token injection** — the Frappe session token is resolved server-side at page render time and injected via `requestInterceptor` into every non-GET request; no manual copy-pasting needed
- **DocType-specific endpoints** — add DocType names in Swagger Settings; the generator produces fully typed OpenAPI paths with all fields, types, and required markers
- **Generic CRUD API** — `erpnext_api_docs` ships five ready-to-use endpoints that work with any ERPNext DocType
- **Pydantic v2 validation** — request bodies are validated via `@validate_request(Model)` before reaching business logic
- **Docker-ready** — `Dockerfile.swagger` builds an image on top of `frappe/erpnext:version-16`

---

## Setup

### 1. Install the `swagger` app

```bash
bench get-app --branch main https://github.com/boehand/swagger-erpnext
bench --site <your-site> install-app swagger
```

### 2. Install the `erpnext_api_docs` app

```bash
bench get-app erpnext_api_docs /path/to/repo/apps/erpnext_api_docs
bench --site <your-site> install-app erpnext_api_docs
```

### 3. Generate the Swagger JSON

- Open the **Swagger Settings** DocType in the Frappe desk
- Set the **App Name**, choose an auth mode, and fill in the DocType list (see below)
- Click **Generate Swagger JSON**

### 4. Open the Swagger UI

Navigate to `https://<your-site>/swagger` — the UI loads with the CSRF token already set.

---

## DocType-specific endpoints

In the **"DocType-specific Endpoints"** section of Swagger Settings there is a table where you can add any number of ERPNext DocTypes by name:

| Field | Description |
|-------|-------------|
| **DocType** | Name of the DocType to document, e.g. `Customer`, `Sales Invoice`, `Item` |

After clicking **Generate Swagger JSON**, the generator produces five fully typed endpoints per entry using the **native Frappe REST API** (`/api/resource/…`):

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/resource/{DocType}` | List records — with filters, field selection, limit, pagination |
| `POST` | `/api/resource/{DocType}` | Create a record — only writable fields shown, required fields marked |
| `GET` | `/api/resource/{DocType}/{name}` | Fetch a single record |
| `PUT` | `/api/resource/{DocType}/{name}` | Update a record |
| `DELETE` | `/api/resource/{DocType}/{name}` | Delete a record |

Because these are real Frappe REST paths, **"Try it out"** works directly in the Swagger UI — the CSRF token is sent automatically.

### How fields are translated

The generator reads all fields of the DocType via `frappe.get_meta()` and maps them to OpenAPI schemas:

- **Field types** are mapped: `Data` → `string`, `Int` → `integer`, `Currency` → `number`, `Check` → `integer enum [0, 1]`, `Date` → `string (format: date)`, `Select` → `string` with an automatic `enum` from the field options, etc.
- **Required fields** (`reqd = 1`) appear in `required`
- **Read-only fields** appear only in the response schema, not in the write body
- **Meta-fields** (`name`, `owner`, `creation`, `modified`, …) are automatically included as `readOnly` in the response schema
- **Layout fields** (Section Break, Column Break, child tables) are skipped

Each DocType gets its own **tag** (collapsible group) in the Swagger UI and a `$ref` entry in `components/schemas`.

### Example: typical ERPNext master data

```
Customer
Supplier
Item
Sales Order
Purchase Order
Sales Invoice
Purchase Invoice
Payment Entry
Delivery Note
Stock Entry
```

---

## Generic CRUD endpoints (`erpnext_api_docs`)

These endpoints accept any DocType as a parameter — useful for quick ad-hoc testing without touching the Settings.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/method/erpnext_api_docs.api.doctype.create_document` | Create a document |
| `GET` | `/api/method/erpnext_api_docs.api.doctype.get_document` | Fetch a single document |
| `GET` | `/api/method/erpnext_api_docs.api.doctype.list_documents` | List documents with filters |
| `PUT` | `/api/method/erpnext_api_docs.api.doctype.update_document` | Update a document |
| `DELETE` | `/api/method/erpnext_api_docs.api.doctype.delete_document` | Delete a document |
| `GET` | `/api/method/erpnext_api_docs.api.doctype.list_doctypes` | List available DocTypes |

All endpoints require an authenticated session (`allow_guest=False`) and respect Frappe's permission system.

---

## CSRF token — how it works

Frappe protects every write API call with a per-session CSRF token. The original implementation set the token header to `null`, which bypassed the check.

The new approach:

1. **`swagger/www/swagger.py`** — a Frappe `get_context()` function reads `frappe.local.session.data.csrf_token` at request time and passes it to the Jinja template. `no_cache = 1` ensures the token is always fresh.
2. **`swagger/www/swagger.html`** — the token is written into a JS variable at render time and injected via `requestInterceptor` for all `POST`, `PUT`, `PATCH`, and `DELETE` calls.

---

## Adding endpoints from your own app

Create an `api/` folder inside your app and add functions that call `swagger.validate_http_method(...)`:

```python
# myapp/myapp/api/customer.py
import frappe
import swagger
from swagger.validator import validate_request
from pydantic import BaseModel

class CustomerModel(BaseModel):
    customer_name: str
    customer_type: str = "Company"

@frappe.whitelist(allow_guest=False)
@validate_request(CustomerModel)
def create_customer(validated_data: CustomerModel = None):
    swagger.validate_http_method("POST")
    doc = frappe.get_doc({"doctype": "Customer", **validated_data.model_dump()})
    doc.insert()
    frappe.db.commit()
    return {"status": "success", "data": doc.as_dict()}
```

After clicking **Generate Swagger JSON** the new endpoint appears in the UI automatically.

---

## Docker

```bash
docker build -f Dockerfile.swagger -t erpnext-swagger .
```

The Dockerfile extends `frappe/erpnext:version-16`, installs the `swagger` app via `bench get-app`, and copies `apps/erpnext_api_docs` from the build context.

---

## Contributing

Contributions are welcome — open an issue or submit a pull request.
