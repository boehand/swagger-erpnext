import ast
import importlib.util
import inspect
import json
import os

import frappe
from pydantic import BaseModel


# ---------------------------------------------------------------------------
#  Frappe-Feldtyp → OpenAPI-Schema
# ---------------------------------------------------------------------------

_FRAPPE_TYPE_MAP = {
    "Data":             {"type": "string"},
    "Small Text":       {"type": "string"},
    "Text":             {"type": "string"},
    "Long Text":        {"type": "string"},
    "Text Editor":      {"type": "string"},
    "Code":             {"type": "string"},
    "Markdown Editor":  {"type": "string"},
    "Autocomplete":     {"type": "string"},
    "Color":            {"type": "string"},
    "Phone":            {"type": "string"},
    "Duration":         {"type": "string"},
    "Geolocation":      {"type": "string"},
    "Attach":           {"type": "string"},
    "Attach Image":     {"type": "string"},
    "Password":         {"type": "string", "format": "password"},
    "Link":             {"type": "string"},
    "Dynamic Link":     {"type": "string"},
    "Select":           {"type": "string"},
    "Int":              {"type": "integer"},
    "Long Int":         {"type": "integer"},
    "Float":            {"type": "number"},
    "Currency":         {"type": "number"},
    "Percent":          {"type": "number"},
    "Rating":           {"type": "number"},
    "Check":            {"type": "integer", "enum": [0, 1], "description": "0 = nein, 1 = ja"},
    "Date":             {"type": "string", "format": "date"},
    "Datetime":         {"type": "string", "format": "date-time"},
    "Time":             {"type": "string"},
    "JSON":             {"type": "object"},
}

# Feldtypen, die keine sinnvolle API-Repräsentation haben
_SKIP_FIELDTYPES = {
    "Section Break", "Column Break", "Tab Break",
    "HTML", "Heading", "Image", "Fold",
    "Table", "Table MultiSelect",
}

# Interne Frappe-Metafelder werden vom Response-Schema getrennt behandelt
_META_FIELDS = {
    "name", "owner", "creation", "modified", "modified_by",
    "docstatus", "idx", "parent", "parenttype", "parentfield",
}


def _field_to_openapi(field) -> dict | None:
    """Konvertiert ein Frappe-DocField in ein OpenAPI-Schema-Objekt."""
    if field.fieldtype in _SKIP_FIELDTYPES:
        return None

    schema = _FRAPPE_TYPE_MAP.get(field.fieldtype, {"type": "string"}).copy()

    if field.fieldtype == "Select" and field.options:
        opts = [o.strip() for o in field.options.split("\n") if o.strip()]
        if opts:
            schema["enum"] = opts

    if field.label:
        schema["description"] = field.label

    if field.read_only:
        schema["readOnly"] = True

    if field.default not in (None, ""):
        schema["default"] = field.default

    return schema


def _build_doctype_schemas(doctype_name: str) -> tuple[dict, dict, list]:
    """
    Gibt zurück:
      write_props  – Felder die per POST/PUT gesendet werden dürfen
      full_props   – alle Felder inkl. read-only (für Response-Schema)
      required     – Liste der Pflichtfelder
    """
    meta = frappe.get_meta(doctype_name)
    write_props: dict = {}
    full_props: dict = {}
    required: list = []

    for field in meta.fields:
        if field.fieldname in _META_FIELDS:
            continue
        schema = _field_to_openapi(field)
        if schema is None:
            continue

        full_props[field.fieldname] = schema
        if not field.read_only:
            write_props[field.fieldname] = schema
            if field.reqd:
                required.append(field.fieldname)

    return write_props, full_props, required


def generate_doctype_resource_paths(swagger: dict, doctype_name: str) -> None:
    """
    Erzeugt vollständig ausformulierte OpenAPI-Pfade für einen DocType
    über die native Frappe REST-API:

      GET  /api/resource/{DocType}          → Liste
      POST /api/resource/{DocType}          → Anlegen
      GET  /api/resource/{DocType}/{name}   → Einzeldatensatz
      PUT  /api/resource/{DocType}/{name}   → Aktualisieren
      DELETE /api/resource/{DocType}/{name} → Löschen
    """
    try:
        write_props, full_props, required = _build_doctype_schemas(doctype_name)
    except Exception as e:
        frappe.log_error(f"Swagger: DocType '{doctype_name}' konnte nicht geladen werden: {e}")
        return

    # ------------------------------------------------------------------
    #  Wiederverwendbare Schema-Referenz im components-Block
    # ------------------------------------------------------------------
    if "schemas" not in swagger["components"]:
        swagger["components"]["schemas"] = {}

    meta_read_only = {
        "name":        {"type": "string", "readOnly": True, "description": "Primärschlüssel"},
        "owner":       {"type": "string", "readOnly": True, "description": "Ersteller"},
        "creation":    {"type": "string", "format": "date-time", "readOnly": True},
        "modified":    {"type": "string", "format": "date-time", "readOnly": True},
        "modified_by": {"type": "string", "readOnly": True},
        "docstatus":   {"type": "integer", "enum": [0, 1, 2], "readOnly": True,
                        "description": "0=Entwurf, 1=Eingereicht, 2=Abgebrochen"},
    }

    swagger["components"]["schemas"][doctype_name] = {
        "type": "object",
        "properties": {**meta_read_only, **full_props},
    }

    write_schema: dict = {"type": "object", "properties": write_props}
    if required:
        write_schema["required"] = required

    ref = {"$ref": f"#/components/schemas/{doctype_name}"}

    security = [{"basicAuth": []}]

    list_response = {
        "200": {
            "description": f"Liste von {doctype_name}-Datensätzen",
            "content": {"application/json": {"schema": {
                "type": "object",
                "properties": {"data": {"type": "array", "items": ref}},
            }}},
        }
    }
    item_response = {
        "200": {
            "description": f"{doctype_name}-Datensatz",
            "content": {"application/json": {"schema": {
                "type": "object",
                "properties": {"data": ref},
            }}},
        }
    }

    # ------------------------------------------------------------------
    #  /api/resource/{DocType}  – Liste & Anlegen
    # ------------------------------------------------------------------
    list_path = f"/api/resource/{doctype_name}"
    swagger["paths"][list_path] = {
        "get": {
            "summary": f"{doctype_name} – Liste",
            "tags": [doctype_name],
            "parameters": [
                {
                    "name": "fields",
                    "in": "query",
                    "schema": {"type": "string"},
                    "description": 'JSON-Array der zurückzugebenden Felder, z.B. `["name","modified"]`',
                    "example": '["name","modified"]',
                },
                {
                    "name": "filters",
                    "in": "query",
                    "schema": {"type": "string"},
                    "description": 'Frappe-Filterarray, z.B. `[["field","=","value"]]`',
                },
                {
                    "name": "limit",
                    "in": "query",
                    "schema": {"type": "integer", "default": 20},
                },
                {
                    "name": "limit_start",
                    "in": "query",
                    "schema": {"type": "integer", "default": 0},
                    "description": "Offset für Paginierung",
                },
                {
                    "name": "order_by",
                    "in": "query",
                    "schema": {"type": "string", "default": "modified desc"},
                },
            ],
            "responses": list_response,
            "security": security,
        },
        "post": {
            "summary": f"{doctype_name} – Anlegen",
            "tags": [doctype_name],
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": write_schema}},
            },
            "responses": item_response,
            "security": security,
        },
    }

    # ------------------------------------------------------------------
    #  /api/resource/{DocType}/{name}  – Lesen, Aktualisieren, Löschen
    # ------------------------------------------------------------------
    name_param = {
        "name": "name",
        "in": "path",
        "required": True,
        "schema": {"type": "string"},
        "description": f"Name / Primärschlüssel des {doctype_name}-Datensatzes",
    }

    item_path = f"/api/resource/{doctype_name}/{{name}}"
    swagger["paths"][item_path] = {
        "get": {
            "summary": f"{doctype_name} – Einzeldatensatz",
            "tags": [doctype_name],
            "parameters": [name_param],
            "responses": item_response,
            "security": security,
        },
        "put": {
            "summary": f"{doctype_name} – Aktualisieren",
            "tags": [doctype_name],
            "parameters": [name_param],
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": write_schema}},
            },
            "responses": item_response,
            "security": security,
        },
        "delete": {
            "summary": f"{doctype_name} – Löschen",
            "tags": [doctype_name],
            "parameters": [name_param],
            "responses": {"200": {"description": f"{doctype_name} gelöscht"}},
            "security": security,
        },
    }


# ---------------------------------------------------------------------------
#  Bestehende Hilfsfunktionen (unverändert)
# ---------------------------------------------------------------------------

def find_pydantic_model_in_decorator(node):
    for n in ast.walk(node):
        if isinstance(n, ast.FunctionDef):
            for decorator in n.decorator_list:
                if isinstance(decorator, ast.Call):
                    if (
                        isinstance(decorator.func, ast.Name)
                        and decorator.func.id == "validate_request"
                    ):
                        if decorator.args:
                            if isinstance(decorator.args[0], ast.Name):
                                return decorator.args[0].id
                            elif isinstance(decorator.args[0], ast.Attribute):
                                return f"{ast.dump(decorator.args[0].value)}.{decorator.args[0].attr}"
    return None


def get_pydantic_model_schema(model_name, module):
    if hasattr(module, model_name):
        model = getattr(module, model_name)
        if issubclass(model, BaseModel):
            return model.model_json_schema()
    return None


def process_function(app_name, module_name, func_name, func, swagger, module):
    try:
        source_code = inspect.getsource(func)
        tree = ast.parse(source_code)

        if not any(
            "validate_http_method" in ast.dump(node) and isinstance(node, ast.Call)
            for node in ast.walk(tree)
        ):
            print(f"Skipping {func_name}: 'validate_http_method' not found")
            return

        pydantic_model_name = find_pydantic_model_in_decorator(tree)

        path = f"/api/method/{app_name}.api.{module_name}.{func_name}".lower()

        http_methods = {
            "GET": "GET",
            "POST": "POST",
            "PUT": "PUT",
            "DELETE": "DELETE",
            "PATCH": "PATCH",
            "OPTIONS": "OPTIONS",
            "HEAD": "HEAD",
        }

        http_method = "POST"
        for method in http_methods:
            if method in source_code:
                http_method = method
                break

        request_body = {}
        if pydantic_model_name and http_method in ["POST", "PUT", "PATCH"]:
            pydantic_schema = get_pydantic_model_schema(pydantic_model_name, module)
            if pydantic_schema:
                request_body = {
                    "description": "Request body",
                    "required": True,
                    "content": {"application/json": {"schema": pydantic_schema}},
                }

        params = []
        if http_method in ["GET", "DELETE", "OPTIONS", "HEAD"]:
            signature = inspect.signature(func)
            for param_name, param in signature.parameters.items():
                if (
                    param.default is inspect.Parameter.empty
                    and "kwargs" not in param_name
                ):
                    params.append(
                        {
                            "name": param_name,
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    )

        responses = {
            "200": {
                "description": "Successful response",
                "content": {"application/json": {"schema": {"type": "object"}}},
            }
        }

        tags = [module_name]

        if path not in swagger["paths"]:
            swagger["paths"][path] = {}

        swagger["paths"][path][http_method.lower()] = {
            "summary": func_name.title().replace("_", " "),
            "tags": tags,
            "parameters": params,
            "requestBody": request_body if request_body else None,
            "responses": responses,
            "security": [{"basicAuth": []}],
        }
    except Exception as e:
        frappe.log_error(
            f"Error processing function {func_name} in module {module_name}: {str(e)}"
        )


def load_module_from_file(file_path):
    module_name = os.path.basename(file_path).replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
#  Hauptfunktion
# ---------------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def generate_swagger_json():
    """Erzeugt swagger.json aus allen api/-Ordnern der installierten Apps
    sowie aus der DocType-Liste in den Swagger Settings."""

    swagger_settings = frappe.get_single("Swagger Settings")

    swagger = {
        "openapi": "3.0.0",
        "info": {
            "title": f"{swagger_settings.app_name} API",
            "version": "1.0.0",
        },
        "paths": {},
        "components": {},
    }

    if swagger_settings.token_based_basicauth or swagger_settings.bearerauth:
        swagger["components"]["securitySchemes"] = {}
        swagger["security"] = []

    if swagger_settings.token_based_basicauth:
        swagger["components"]["securitySchemes"]["basicAuth"] = {
            "type": "http",
            "scheme": "basic",
        }
        swagger["security"].append({"basicAuth": []})

    if swagger_settings.bearerauth:
        swagger["components"]["securitySchemes"]["bearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
        swagger["security"].append({"bearerAuth": []})

    # ------------------------------------------------------------------
    #  1. Generische Endpunkte aus api/-Ordnern
    # ------------------------------------------------------------------
    frappe_bench_dir = frappe.utils.get_bench_path()
    file_paths = []

    for app in frappe.get_installed_apps():
        try:
            api_dir = os.path.join(frappe_bench_dir, "apps", app, app, "api")
            if os.path.exists(api_dir) and os.path.isdir(api_dir):
                for root, dirs, files in os.walk(api_dir):
                    for file in files:
                        if file.endswith(".py"):
                            file_paths.append((app, os.path.join(root, file)))
        except Exception as e:
            frappe.log_error(f"Error processing app '{app}': {str(e)}")
            continue

    for app, file_path in file_paths:
        try:
            if os.path.isfile(file_path) and app in str(file_path):
                module = load_module_from_file(file_path)
                module_name = os.path.basename(file_path).replace(".py", "")
                for func_name, func in inspect.getmembers(module, inspect.isfunction):
                    process_function(app, module_name, func_name, func, swagger, module)
        except Exception as e:
            frappe.log_error(f"Error loading or processing file {file_path}: {str(e)}")

    # ------------------------------------------------------------------
    #  2. DocType-spezifische Endpunkte via /api/resource/{DocType}
    # ------------------------------------------------------------------
    doctype_entries = swagger_settings.get("doctype_list") or []
    for row in doctype_entries:
        doctype_name = (row.get("doctype_name") if isinstance(row, dict) else getattr(row, "doctype_name", None))
        if doctype_name:
            generate_doctype_resource_paths(swagger, doctype_name)

    # ------------------------------------------------------------------
    #  3. Datei schreiben
    # ------------------------------------------------------------------
    www_dir = os.path.join(frappe_bench_dir, "apps", "swagger", "swagger", "www")
    os.makedirs(www_dir, exist_ok=True)

    file_path = os.path.join(www_dir, "swagger.json")
    with open(file_path, "w") as swagger_file:
        json.dump(swagger, swagger_file, indent=4)

    frappe.msgprint("Swagger JSON erfolgreich generiert.")
