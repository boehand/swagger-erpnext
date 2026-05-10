import importlib
import sys

import frappe
from frappe.model.document import Document


class SwaggerSettings(Document):
    def _set_defaults(self):
        # Frappe initializes child-table defaults here, which requires both:
        #   (a) the "Swagger DocType Entry" row to exist in the DocType table, and
        #   (b) its Python controller module to be importable.
        # After a code update without bench migrate, either can be missing.
        # We reload the DocTypes if (a) is missing, and recover from a failed
        # controller import (stale module/meta cache after a code update) if
        # (b) fails — both without requiring a manual migrate or restart.
        if not frappe.db.exists("DocType", "Swagger DocType Entry"):
            self._sync_swagger_schema()

        try:
            super()._set_defaults()
        except ImportError as e:
            if "Swagger DocType Entry" not in str(e):
                raise
            self._sync_swagger_schema()
            super()._set_defaults()

    @staticmethod
    def _sync_swagger_schema():
        frappe.reload_doc("swagger_ui", "doctype", "swagger_doctype_entry", force=True)
        frappe.reload_doc("swagger_ui", "doctype", "swagger_settings", force=True)
        frappe.db.commit()

        # Drop cached meta for both DocTypes so the next access reads from disk.
        frappe.clear_cache(doctype="Swagger Settings")
        frappe.clear_cache(doctype="Swagger DocType Entry")

        # Drop the cached controller class — Frappe stores a Document fallback
        # when import_controller fails the first time, and that fallback would
        # be returned on the retry without these evictions.
        site_controllers = getattr(frappe.local, "site_controllers", None)
        if isinstance(site_controllers, dict):
            site_controllers.pop("Swagger DocType Entry", None)

        # Tell Python's import machinery to re-scan the filesystem.  Without
        # this, importlib.import_module silently keeps using the cached parent
        # package contents and never sees the new submodule on disk.
        importlib.invalidate_caches()

        # Evict any partially-loaded swagger.swagger_ui.doctype.* entries from
        # sys.modules so the next import_module call rebuilds them from disk.
        for mod_name in [m for m in sys.modules if m.startswith("swagger.swagger_ui.doctype")]:
            del sys.modules[mod_name]
