import frappe
from frappe.model.document import Document


class SwaggerSettings(Document):
    def _set_defaults(self):
        # Frappe initializes child-table defaults here, which requires both:
        #   (a) the "Swagger DocType Entry" row to exist in the DocType table, and
        #   (b) its Python controller to be importable.
        # After a code update without bench migrate, either can be missing.
        # We reload the DocTypes if (a) is missing, and recover from a failed
        # controller import (stale module/meta cache) if (b) fails — both
        # without requiring a manual migrate or restart.
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
        # Drop cached meta and any cached controller class so the next import
        # picks up the freshly synced module.
        frappe.clear_cache(doctype="Swagger Settings")
        frappe.clear_cache(doctype="Swagger DocType Entry")
        site_controllers = getattr(frappe.local, "site_controllers", None)
        if isinstance(site_controllers, dict):
            site_controllers.pop("Swagger DocType Entry", None)
