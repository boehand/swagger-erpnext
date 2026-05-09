import frappe
from frappe.model.document import Document


class SwaggerSettings(Document):
    def _set_defaults(self):
        # Ensure Swagger DocType Entry exists in the DB before Frappe tries
        # to initialise child-table defaults for the doctype_list field.
        # This makes bench migrate unnecessary for existing installs that
        # pulled new code without running a full site migration.
        if not frappe.db.exists("DocType", "Swagger DocType Entry"):
            frappe.reload_doc("swagger_ui", "doctype", "swagger_doctype_entry", force=True)
            frappe.db.commit()
        super()._set_defaults()
