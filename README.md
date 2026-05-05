# swagger-erpnext

**Dynamic Swagger UI for ERPNext** — forked from [omkardarves/swagger](https://github.com/omkardarves/swagger) and extended with:

- automatische CSRF-Token-Injektion für alle schreibenden Requests
- DocType-spezifische Endpunkte mit vollständigen Feldschemata (per Settings konfigurierbar)
- eine fertige ERPNext-App (`erpnext_api_docs`) mit generischen CRUD-Endpunkten für jeden DocType

#### License: MIT

---

## Repository-Struktur

```
swagger-erpnext/
├── swagger/                          # Swagger-UI-Engine (diese App)
│   ├── www/
│   │   ├── swagger.html              # Swagger-UI-Seite (CSRF-Token automatisch gesetzt)
│   │   └── swagger.py               # Frappe get_context() – liest CSRF-Token aus der Session
│   ├── swagger_generator.py         # Baut swagger.json aus api/-Ordnern + DocType-Liste
│   └── swagger_ui/
│       └── doctype/
│           ├── swagger_settings/    # Einstellungs-DocType (App-Name, Auth, DocType-Liste)
│           ├── swagger_doctype_entry/  # Child-Table für die DocType-Liste
│           └── api_error_log/       # Fehlerprotokoll-DocType
│
└── apps/
    └── erpnext_api_docs/            # Eigene ERPNext-App – generische DocType-CRUD-API
        ├── setup.py / pyproject.toml / requirements.txt
        └── erpnext_api_docs/
            ├── hooks.py
            ├── api/
            │   └── doctype.py       # @frappe.whitelist() CRUD-Endpunkte
            └── basemodels/
                └── doctype.py       # Pydantic-v2-Modelle
```

---

## Features

- **Automatische Swagger-UI-Generierung** — scannt die `api/`-Ordner aller installierten Apps und erzeugt eine OpenAPI-3.0-Spezifikation
- **CSRF-Token-Injektion** — der Frappe-Session-Token wird serverseitig beim Seitenrendering gelesen und via `requestInterceptor` in jeden nicht-GET-Request eingebaut; kein manuelles Kopieren nötig
- **DocType-spezifische Endpunkte** — in den Settings einfach DocType-Namen eintragen; der Generator erzeugt daraus vollständig typisierte OpenAPI-Pfade mit allen Feldern, Typen und Pflichtfeldern
- **Generische CRUD-API** — `erpnext_api_docs` liefert fünf einsatzbereite Endpunkte, die mit jedem ERPNext-DocType funktionieren
- **Pydantic-v2-Validierung** — Request-Bodies werden per `@validate_request(Model)` validiert
- **Docker-ready** — `Dockerfile.swagger` baut ein Image auf Basis von `frappe/erpnext:version-16`

---

## Setup

### 1. `swagger`-App installieren

```bash
bench get-app --branch main https://github.com/boehand/swagger-erpnext
bench --site <deine-site> install-app swagger
```

### 2. `erpnext_api_docs`-App installieren

```bash
# App aus dem apps/-Unterordner dieses Repos registrieren
bench get-app erpnext_api_docs /pfad/zum/repo/apps/erpnext_api_docs
bench --site <deine-site> install-app erpnext_api_docs
```

### 3. Swagger JSON generieren

- Im Frappe Desk den DocType **Swagger Settings** öffnen
- **App Name** setzen, Auth-Modus wählen, DocType-Liste befüllen (siehe unten)
- Auf **Generate Swagger JSON** klicken

### 4. Swagger UI öffnen

`https://<deine-site>/swagger` — die UI lädt mit bereits gesetztem CSRF-Token.

---

## DocType-spezifische Endpunkte konfigurieren

Im Abschnitt **„DocType-spezifische Endpunkte"** der Swagger Settings gibt es eine Tabelle, in die beliebig viele ERPNext-DocTypes eingetragen werden können:

| Feld | Beschreibung |
|------|-------------|
| **DocType** | Name des gewünschten DocTypes, z.B. `Customer`, `Sales Invoice`, `Item` |

Nach dem Klick auf **Generate Swagger JSON** erzeugt der Generator für jeden Eintrag fünf vollständig ausformulierte Endpunkte auf der **nativen Frappe REST-API** (`/api/resource/…`):

| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| `GET` | `/api/resource/{DocType}` | Liste – mit Filtern, Feldauswahl, Limit, Paginierung |
| `POST` | `/api/resource/{DocType}` | Anlegen – nur schreibbare Felder, Pflichtfelder markiert |
| `GET` | `/api/resource/{DocType}/{name}` | Einzeldatensatz |
| `PUT` | `/api/resource/{DocType}/{name}` | Aktualisieren |
| `DELETE` | `/api/resource/{DocType}/{name}` | Löschen |

Da dies echte Frappe-REST-Pfade sind, funktioniert **„Try it out"** in der Swagger UI direkt — der CSRF-Token wird automatisch mitgesendet.

### Was wird aus den Feldern?

Der Generator liest alle Felder des DocTypes per `frappe.get_meta()` und baut daraus OpenAPI-Schemas:

- **Feldtypen** werden gemappt: `Data` → `string`, `Int` → `integer`, `Currency` → `number`, `Check` → `integer enum [0,1]`, `Date` → `string (format: date)`, `Select` → `string` mit automatischem `enum` aus den Options, usw.
- **Pflichtfelder** (`reqd = 1`) erscheinen in `required`
- **Read-only-Felder** erscheinen nur im Response-Schema, nicht im Write-Body
- **Metafelder** (`name`, `owner`, `creation`, `modified` …) werden automatisch als `readOnly` ins Response-Schema aufgenommen
- **Technische Felder** (Section Break, Column Break, Table-Kindtabellen) werden übersprungen

Jeder DocType bekommt in der Swagger UI einen eigenen **Tag** (eingeklappte Gruppe) und einen `$ref`-Eintrag in `components/schemas`.

### Beispiel: Konfiguration für ERPNext-Grunddaten

Typische Einträge, um die ERPNext-API besser zu verstehen:

```
Customer
Supplier
Item
Sales Order
Purchase Order
Sales Invoice
Purchase Invoice
Payment Entry
Delivery Note
Stock Entry
```

---

## Generische CRUD-Endpunkte (`erpnext_api_docs`)

Diese Endpunkte akzeptieren jeden DocType als Parameter — praktisch wenn man schnell etwas testen möchte, ohne die Settings anzupassen.

| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| `POST` | `/api/method/erpnext_api_docs.api.doctype.create_document` | Dokument anlegen |
| `GET` | `/api/method/erpnext_api_docs.api.doctype.get_document` | Einzeldokument abrufen |
| `GET` | `/api/method/erpnext_api_docs.api.doctype.list_documents` | Liste mit Filtern |
| `PUT` | `/api/method/erpnext_api_docs.api.doctype.update_document` | Dokument aktualisieren |
| `DELETE` | `/api/method/erpnext_api_docs.api.doctype.delete_document` | Dokument löschen |
| `GET` | `/api/method/erpnext_api_docs.api.doctype.list_doctypes` | Verfügbare DocTypes |

Alle Endpunkte erfordern eine authentifizierte Session (`allow_guest=False`) und respektieren das Frappe-Berechtigungssystem.

---

## CSRF-Token — wie es funktioniert

Frappe schützt jeden schreibenden API-Aufruf mit einem session-gebundenen CSRF-Token. Die ursprüngliche Implementierung hat den Token-Header auf `null` gesetzt (also entfernt), was den Check umgangen hat.

Der neue Ansatz:

1. **`swagger/www/swagger.py`** — eine Frappe-`get_context()`-Funktion liest `frappe.local.session.data.csrf_token` beim Seitenrendering und übergibt ihn ans Jinja-Template. `no_cache = 1` sorgt dafür, dass der Token immer aktuell ist.
2. **`swagger/www/swagger.html`** — der Token wird beim Rendern in eine JS-Variable geschrieben und via `requestInterceptor` für alle `POST`-, `PUT`-, `PATCH`- und `DELETE`-Calls gesetzt.

---

## Eigene App-Endpunkte hinzufügen

Einen `api/`-Ordner in der eigenen App anlegen und Funktionen mit `swagger.validate_http_method(...)` ergänzen:

```python
# myapp/myapp/api/customer.py
import frappe
import swagger
from swagger.validator import validate_request
from pydantic import BaseModel

class CustomerModel(BaseModel):
    customer_name: str
    customer_type: str = "Company"

@frappe.whitelist(allow_guest=False)
@validate_request(CustomerModel)
def create_customer(validated_data: CustomerModel = None):
    swagger.validate_http_method("POST")
    doc = frappe.get_doc({"doctype": "Customer", **validated_data.model_dump()})
    doc.insert()
    frappe.db.commit()
    return {"status": "success", "data": doc.as_dict()}
```

Nach dem nächsten Klick auf **Generate Swagger JSON** erscheint der neue Endpunkt automatisch in der UI.

---

## Docker

```bash
docker build -f Dockerfile.swagger -t erpnext-swagger .
```

Das Dockerfile erweitert `frappe/erpnext:version-16`, installiert die `swagger`-App via `bench get-app` und kopiert `apps/erpnext_api_docs` aus dem Build-Kontext.

---

## Contributing

Contributions sind willkommen — Issue öffnen oder Pull Request einreichen.
