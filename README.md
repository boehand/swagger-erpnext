# swagger-erpnext

**Dynamic Swagger UI for ERPNext** — forked from [omkardarves/swagger](https://github.com/omkardarves/swagger) and extended with a ready-to-use ERPNext app (`erpnext_api_docs`) that provides generic CRUD endpoints for every DocType and automatically injects the Frappe CSRF token into the Swagger UI.

#### License: MIT

---

## Repository structure

```
swagger-erpnext/
├── swagger/                    # Swagger UI engine (omkardarves/swagger)
│   ├── www/
│   │   ├── swagger.html        # Swagger UI page (CSRF token auto-injected)
│   │   └── swagger.py          # Frappe get_context() – passes csrf_token to template
│   ├── swagger_generator.py    # Scans installed apps and builds swagger.json
│   └── swagger_ui/
│       └── doctype/
│           ├── swagger_settings/   # Settings DocType (app name, auth mode)
│           └── api_error_log/      # Error log DocType
│
└── apps/
    └── erpnext_api_docs/       # Custom ERPNext app – generic DocType CRUD API
        ├── setup.py / pyproject.toml / requirements.txt
        └── erpnext_api_docs/
            ├── hooks.py
            ├── api/
            │   └── doctype.py  # @frappe.whitelist() CRUD endpoints
            └── basemodels/
                └── doctype.py  # Pydantic v2 models
```

---

## Features

- **Automatic Swagger UI generation** — scans every installed app's `api/` folder and builds a live OpenAPI 3.0 spec
- **CSRF token auto-injection** — the Frappe session token is resolved server-side at page render time and injected into every non-GET request; no manual copy-pasting required
- **Generic DocType CRUD** — `erpnext_api_docs` ships five ready-to-use endpoints that work with any ERPNext DocType out of the box
- **Pydantic v2 validation** — request bodies are validated via `@validate_request(Model)` before they reach business logic
- **Docker-ready** — `Dockerfile.swagger` builds an image with both apps pre-installed on top of the official `frappe/erpnext:version-16` base

---

## CSRF token — how it works

Frappe protects every state-changing API call with a per-session CSRF token. The previous implementation removed the token header entirely, which bypassed the check but broke installations that enforce it.

The new approach:

1. `swagger/www/swagger.py` — a Frappe `get_context()` function reads `frappe.local.session.data.csrf_token` at request time and passes it to the Jinja template. `no_cache = 1` ensures the token is always fresh.
2. `swagger/www/swagger.html` — the token is written into a JS variable at render time and injected via `requestInterceptor` for all `POST`, `PUT`, `PATCH`, and `DELETE` calls.

---

## Setup

### 1. Install the `swagger` app

```bash
bench get-app --branch main https://github.com/boehand/swagger-erpnext
bench --site <your-site> install-app swagger
```

### 2. Install the `erpnext_api_docs` app

```bash
bench get-app erpnext_api_docs /path/to/apps/erpnext_api_docs
bench --site <your-site> install-app erpnext_api_docs
```

### 3. Generate the Swagger JSON

- Open the **Swagger Settings** DocType in the Frappe desk
- Set the **App Name** and choose an auth mode (Basic Auth or Bearer)
- Click **Generate Swagger JSON**

### 4. Open the Swagger UI

Navigate to `https://<your-site>/swagger` — the UI loads with the CSRF token already set.

---

## Generic DocType endpoints (`erpnext_api_docs`)

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

## Adding your own app's endpoints

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
