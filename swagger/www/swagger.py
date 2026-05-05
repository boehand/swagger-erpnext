import frappe

# Disable page caching so the CSRF token is always fresh for the current session.
no_cache = 1


def get_context(context):
    """Inject the current session's CSRF token into the Swagger UI template.

    Frappe rotates the CSRF token per session. By resolving it server-side at
    render time we avoid any client-side dance with cookies or extra API calls.
    """
    csrf_token = ""
    try:
        session_data = getattr(frappe.local, "session", None)
        if session_data and hasattr(session_data, "data"):
            csrf_token = session_data.data.get("csrf_token", "") or ""
    except Exception:
        pass
    context.csrf_token = csrf_token
