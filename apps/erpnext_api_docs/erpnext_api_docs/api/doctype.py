"""
Generic REST API endpoints for all ERPNext DocTypes.

The swagger app scans this directory (erpnext_api_docs/api/) and generates
the Swagger UI from the functions defined here.

Functions are intentionally thin and delegate to Frappe's built-in REST
mechanisms. Their main purpose is to expose @frappe.whitelist() callables
that the swagger generator can discover and document.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import frappe
from frappe import _

# The 'swagger' module must be imported directly so the generator can find
# the 'swagger.validate_http_method(...)' signature via its regex scan.
try:
    import swagger
    from swagger.utils import validate_request
    HAS_SWAGGER_HELPERS = True
except Exception:
    HAS_SWAGGER_HELPERS = False

    def validate_request(model):  # type: ignore
        """Fallback decorator used when the swagger app is not yet installed."""
        def deco(fn):
            return fn
        return deco

    class DummySwagger:
        @staticmethod
        def validate_http_method(_method):
            pass
        @staticmethod
        def log_api_error():
            frappe.log_error(frappe.get_traceback(), "erpnext_api_docs error")

    swagger = DummySwagger()


from erpnext_api_docs.basemodels.doctype import (
    DocTypeCreateModel,
    DocTypeUpdateModel,
    DocTypeListFilterModel,
    DocTypeDeleteModel,
)


# =============================================================================
#  CREATE
# =============================================================================
@frappe.whitelist(allow_guest=False)
@validate_request(DocTypeCreateModel)
def create_document(validated_data: DocTypeCreateModel = None, **kwargs):
    """
    Create a new document of any DocType.

    POST /api/method/erpnext_api_docs.api.doctype.create_document

    Body (JSON):
        {
            "doctype": "Customer",
            "data": {
                "customer_name": "ACME Corp",
                "customer_type": "Company"
            }
        }

    Returns:
        {"status": "success", "data": <created_doc>}
    """
    try:
        swagger.validate_http_method("POST")

        if validated_data is None:
            payload = _get_request_body()
            validated_data = DocTypeCreateModel(**payload)

        doc_dict = {"doctype": validated_data.doctype, **validated_data.data}
        new_doc = frappe.get_doc(doc_dict)
        new_doc.insert()
        frappe.db.commit()

        return {
            "status": "success",
            "message": f"{validated_data.doctype} created",
            "data": new_doc.as_dict(),
        }
    except frappe.PermissionError as e:
        frappe.local.response["http_status_code"] = 403
        return {"status": "error", "message": _("Permission denied"), "details": str(e)}
    except Exception as e:
        swagger.log_api_error()
        frappe.local.response["http_status_code"] = 400
        return {"status": "error", "message": str(e)}


# =============================================================================
#  READ (single)
# =============================================================================
@frappe.whitelist(allow_guest=False)
def get_document(doctype: str, name: str):
    """
    Fetch a single document by its name.

    GET /api/method/erpnext_api_docs.api.doctype.get_document?doctype=Customer&name=CUST-0001

    Returns:
        {"status": "success", "data": <doc>}
    """
    try:
        swagger.validate_http_method("GET")

        doc = frappe.get_doc(doctype, name)
        doc.check_permission("read")
        return {"status": "success", "data": doc.as_dict()}
    except frappe.DoesNotExistError:
        frappe.local.response["http_status_code"] = 404
        return {"status": "error", "message": f"{doctype} '{name}' not found"}
    except frappe.PermissionError:
        frappe.local.response["http_status_code"] = 403
        return {"status": "error", "message": "Permission denied"}
    except Exception as e:
        swagger.log_api_error()
        frappe.local.response["http_status_code"] = 400
        return {"status": "error", "message": str(e)}


# =============================================================================
#  LIST
# =============================================================================
@frappe.whitelist(allow_guest=False)
def list_documents(
    doctype: str,
    filters: Optional[str] = None,
    fields: Optional[str] = None,
    limit: int = 20,
    start: int = 0,
    order_by: str = "modified desc",
):
    """
    List documents of a given DocType with optional filtering.

    GET /api/method/erpnext_api_docs.api.doctype.list_documents
        ?doctype=Customer
        &filters=[["customer_type","=","Company"]]
        &fields=["name","customer_name"]
        &limit=20

    `filters` and `fields` are JSON-encoded strings.

    Returns:
        {"status": "success", "data": [...], "count": int}
    """
    try:
        swagger.validate_http_method("GET")

        parsed_filters = _parse_json(filters) if filters else None
        parsed_fields = _parse_json(fields) if fields else ["name"]

        results = frappe.get_list(
            doctype,
            filters=parsed_filters,
            fields=parsed_fields,
            limit_start=int(start),
            limit_page_length=int(limit),
            order_by=order_by,
            ignore_permissions=False,
        )

        return {
            "status": "success",
            "data": results,
            "count": len(results),
        }
    except frappe.PermissionError:
        frappe.local.response["http_status_code"] = 403
        return {"status": "error", "message": "Permission denied"}
    except Exception as e:
        swagger.log_api_error()
        frappe.local.response["http_status_code"] = 400
        return {"status": "error", "message": str(e)}


# =============================================================================
#  UPDATE
# =============================================================================
@frappe.whitelist(allow_guest=False)
@validate_request(DocTypeUpdateModel)
def update_document(validated_data: DocTypeUpdateModel = None, **kwargs):
    """
    Update fields of an existing document.

    PUT /api/method/erpnext_api_docs.api.doctype.update_document

    Body (JSON):
        {
            "doctype": "Customer",
            "name": "CUST-0001",
            "data": {
                "customer_name": "ACME Corporation"
            }
        }

    Returns:
        {"status": "success", "data": <updated_doc>}
    """
    try:
        swagger.validate_http_method("PUT")

        if validated_data is None:
            payload = _get_request_body()
            validated_data = DocTypeUpdateModel(**payload)

        doc = frappe.get_doc(validated_data.doctype, validated_data.name)
        for key, value in validated_data.data.items():
            doc.set(key, value)
        doc.save()
        frappe.db.commit()

        return {
            "status": "success",
            "message": f"{validated_data.doctype} '{validated_data.name}' updated",
            "data": doc.as_dict(),
        }
    except frappe.DoesNotExistError:
        frappe.local.response["http_status_code"] = 404
        return {"status": "error", "message": "Document not found"}
    except frappe.PermissionError:
        frappe.local.response["http_status_code"] = 403
        return {"status": "error", "message": "Permission denied"}
    except Exception as e:
        swagger.log_api_error()
        frappe.local.response["http_status_code"] = 400
        return {"status": "error", "message": str(e)}


# =============================================================================
#  DELETE
# =============================================================================
@frappe.whitelist(allow_guest=False)
def delete_document(doctype: str, name: str):
    """
    Delete a document by its name.

    DELETE /api/method/erpnext_api_docs.api.doctype.delete_document?doctype=Customer&name=CUST-0001

    Returns:
        {"status": "success", "message": "..."}
    """
    try:
        swagger.validate_http_method("DELETE")
        frappe.delete_doc(doctype, name)
        frappe.db.commit()
        return {
            "status": "success",
            "message": f"{doctype} '{name}' deleted",
        }
    except frappe.DoesNotExistError:
        frappe.local.response["http_status_code"] = 404
        return {"status": "error", "message": f"{doctype} '{name}' not found"}
    except frappe.PermissionError:
        frappe.local.response["http_status_code"] = 403
        return {"status": "error", "message": "Permission denied"}
    except Exception as e:
        swagger.log_api_error()
        frappe.local.response["http_status_code"] = 400
        return {"status": "error", "message": str(e)}


# =============================================================================
#  LIST AVAILABLE DOCTYPES
# =============================================================================
@frappe.whitelist(allow_guest=False)
def list_doctypes(module: Optional[str] = None, limit: int = 1000):
    """
    Return all DocTypes the current user has read access to.

    GET /api/method/erpnext_api_docs.api.doctype.list_doctypes
        ?module=Selling
        &limit=100

    Returns:
        {"status": "success", "data": [{"name":..., "module":...}, ...]}
    """
    try:
        swagger.validate_http_method("GET")
        filters: Dict[str, Any] = {"is_virtual": 0, "issingle": 0, "istable": 0}
        if module:
            filters["module"] = module

        rows = frappe.get_all(
            "DocType",
            fields=["name", "module", "description"],
            filters=filters,
            order_by="module asc, name asc",
            limit_page_length=int(limit),
        )
        return {"status": "success", "data": rows, "count": len(rows)}
    except Exception as e:
        swagger.log_api_error()
        return {"status": "error", "message": str(e)}


# =============================================================================
#  HELPERS
# =============================================================================
def _parse_json(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return value


def _get_request_body() -> Dict[str, Any]:
    if hasattr(frappe.local, "form_dict") and frappe.local.form_dict:
        return dict(frappe.local.form_dict)
    if hasattr(frappe.local, "request") and frappe.local.request:
        try:
            return frappe.local.request.get_json(force=True, silent=True) or {}
        except Exception:
            return {}
    return {}
