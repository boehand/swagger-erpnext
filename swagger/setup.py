import os

import frappe

# Module-level flag: True once swagger.json has been generated in this
# worker process.  Resets to False on every worker restart (bench restart),
# so the first boot_session after a restart always regenerates the file.
_swagger_generated_for_process = False


def after_install():
    """Sync schema and generate swagger.json immediately after bench install-app."""
    _sync_schema()
    _generate_swagger()


def boot_session(bootinfo):
    """On the first desk login after a worker restart, sync the schema (if
    needed) and regenerate swagger.json once for the lifetime of this process.
    """
    global _swagger_generated_for_process

    if not frappe.db.exists("DocType", "Swagger DocType Entry"):
        _sync_schema()

    if not _swagger_generated_for_process:
        _generate_swagger()
        _swagger_generated_for_process = True


def _sync_schema():
    """Reload Swagger DocType definitions from disk into the database."""
    try:
        frappe.reload_doc("swagger_ui", "doctype", "swagger_doctype_entry", force=True)
        frappe.reload_doc("swagger_ui", "doctype", "swagger_settings", force=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Swagger schema sync failed")


def _generate_swagger():
    """Generate swagger.json, silently skipping if settings are not yet ready."""
    try:
        from swagger.swagger_generator import generate_swagger_json
        generate_swagger_json()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Swagger auto-generation failed")
