import frappe
from frappe.model.document import Document


class SwaggerSettings(Document):
    def _set_defaults(self):
        # If Swagger DocType Entry is missing from the DB the schema was never
        # synced after the code update. Reload both DocTypes from disk now so
        # that (a) the child-table exists and (b) the doctype_list field is
        # visible on the form — all without requiring bench migrate or re-login.
        if not frappe.db.exists("DocType", "Swagger DocType Entry"):
            frappe.reload_doc("swagger_ui", "doctype", "swagger_doctype_entry", force=True)
            frappe.reload_doc("swagger_ui", "doctype", "swagger_settings", force=True)
            frappe.db.commit()
            # Refresh the cached meta so _set_defaults sees the updated fields
            frappe.clear_cache(doctype="Swagger Settings")
        super()._set_defaults()
