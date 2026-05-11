import json
import os

import frappe

no_cache = 1


def get_context(context):
    csrf_token = ""
    try:
        session_data = getattr(frappe.local, "session", None)
        if session_data and hasattr(session_data, "data"):
            csrf_token = session_data.data.get("csrf_token", "") or ""
    except Exception:
        pass
    context.csrf_token = csrf_token

    # Load the swagger spec and embed it inline so the page works
    # regardless of how Frappe/nginx serves static files.
    file_path = frappe.get_site_path("public", "files", "swagger.json")
    if not os.path.exists(file_path):
        try:
            from swagger.swagger_generator import generate_swagger_json
            generate_swagger_json()
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Swagger: auto-generate on page load failed")

    try:
        with open(file_path) as f:
            context.swagger_spec = json.load(f)
    except Exception:
        context.swagger_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {},
        }
