import frappe


def after_install():
    """Sync Swagger DocTypes immediately after bench install-app."""
    _sync_schema()


def boot_session(bootinfo):
    """Auto-sync Swagger schema on first desk login after a code update.

    Runs once per login. The existence check makes subsequent calls a single
    DB lookup so there is no meaningful overhead on normal usage.
    """
    if not frappe.db.exists("DocType", "Swagger DocType Entry"):
        _sync_schema()


def _sync_schema():
    """Reload Swagger DocType definitions from disk into the database.

    Calling frappe.reload_doc() is equivalent to running bench migrate for
    these two DocTypes only — it creates the child table and updates the
    field list for Swagger Settings without requiring a full site migration.
    """
    try:
        frappe.reload_doc("swagger_ui", "doctype", "swagger_doctype_entry", force=True)
        frappe.reload_doc("swagger_ui", "doctype", "swagger_settings", force=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Swagger schema sync failed")
