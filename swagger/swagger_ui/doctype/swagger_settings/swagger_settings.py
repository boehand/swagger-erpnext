import importlib
import sys

import frappe
from frappe.model.document import Document

_CONTROLLER_MODULE = "swagger.swagger_ui.doctype.swagger_doctype_entry.swagger_doctype_entry"


class SwaggerSettings(Document):
    def __init__(self, *args, **kwargs):
        # get_controller("Swagger DocType Entry") is called inside
        # super().__init__() when child-table rows are deserialised.
        # After a code update without bench migrate the controller module
        # may not yet be importable (Python cached the parent package before
        # the new submodule existed on disk).  Fix it here — before
        # super().__init__() — so the failure is transparent to Frappe.
        try:
            importlib.import_module(_CONTROLLER_MODULE)
        except ImportError:
            _sync_swagger_schema()
        super().__init__(*args, **kwargs)

    def _set_defaults(self):
        # Belt-and-suspenders: the same ImportError can surface again when
        # _set_defaults initialises defaults for new child-table rows.
        if not frappe.db.exists("DocType", "Swagger DocType Entry"):
            _sync_swagger_schema()
        try:
            super()._set_defaults()
        except ImportError as exc:
            if "Swagger DocType Entry" not in str(exc):
                raise
            _sync_swagger_schema()
            super()._set_defaults()


def _sync_swagger_schema():
    """Reload schema and clear all Python import caches for the child DocType."""
    frappe.reload_doc("swagger_ui", "doctype", "swagger_doctype_entry", force=True)
    frappe.reload_doc("swagger_ui", "doctype", "swagger_settings", force=True)
    frappe.db.commit()
    frappe.clear_cache(doctype="Swagger Settings")
    frappe.clear_cache(doctype="Swagger DocType Entry")

    site_controllers = getattr(frappe.local, "site_controllers", None)
    if isinstance(site_controllers, dict):
        site_controllers.pop("Swagger DocType Entry", None)

    # Tell Python's import machinery to re-scan the filesystem, then evict
    # any partially-cached swagger.swagger_ui.doctype.* entries so the next
    # importlib.import_module call rebuilds them from disk.
    importlib.invalidate_caches()
    for mod_name in [m for m in sys.modules if m.startswith("swagger.swagger_ui.doctype")]:
        del sys.modules[mod_name]
