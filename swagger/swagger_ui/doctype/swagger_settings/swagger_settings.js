frappe.ui.form.on("Swagger Settings", {
    refresh: function (frm) {
        // Hide the default "Add Row" button — the custom picker replaces it.
        let grid = frm.get_field("doctype_list").grid;
        grid.cannot_add_rows = true;
        grid.wrapper.find(".grid-add-row").hide();

        frm.add_custom_button(__("Add DocTypes"), function () {
            show_doctype_picker(frm);
        });

        frm.add_custom_button(__("Open Swagger UI"), function () {
            window.open("/swagger", "_blank");
        });

        // Render an inline Swagger UI iframe below the form fields.
        // Re-render on every refresh (Frappe clears the form body each time).
        let $existing = $(frm.wrapper).find(".swagger-iframe-section");
        if ($existing.length) {
            $existing.remove();
        }
        let $section = $(`
            <div class="swagger-iframe-section" style="margin-top:24px;padding:0 15px 24px;">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
                    <h5 style="margin:0;">${__("Swagger UI Preview")}</h5>
                    <button class="btn btn-xs btn-default swagger-reload-btn">${__("Reload")}</button>
                </div>
                <iframe src="/swagger"
                    style="width:100%;height:700px;border:1px solid var(--border-color,#d1d8dd);border-radius:4px;"
                    frameborder="0">
                </iframe>
            </div>
        `);
        $(frm.wrapper).find(".page-form, .form-page").first().append($section);

        $section.find(".swagger-reload-btn").on("click", function () {
            let $iframe = $section.find("iframe");
            $iframe.attr("src", $iframe.attr("src"));
        });
    },

    generate_swagger_json: function (frm) {
        // Always pass the current (possibly unsaved) doctype_list from the form
        // so the generated JSON matches what is visible on screen.
        let doctype_names = (frm.doc.doctype_list || [])
            .filter(r => r.doctype_name)
            .map(r => r.doctype_name);

        frappe.call({
            method: "swagger.swagger_generator.generate_swagger_json",
            args: { doctype_list: JSON.stringify(doctype_names) },
            freeze: true,
            freeze_message: __("Generating Swagger JSON…"),
            callback: function () {
                frappe.show_alert({
                    message: __("Swagger JSON generated successfully"),
                    indicator: "green",
                });
            },
        });
    },
});

// ---------------------------------------------------------------------------
//  DocType picker dialog
// ---------------------------------------------------------------------------

function show_doctype_picker(frm) {
    let all_doctypes = [];
    let selected = new Set(
        (frm.doc.doctype_list || []).map(r => r.doctype_name).filter(Boolean)
    );

    let d = new frappe.ui.Dialog({
        title: __("Add DocTypes"),
        size: "large",
        fields: [
            {
                fieldtype: "HTML",
                fieldname: "picker_html",
                options: `
                    <div style="display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;margin-bottom:10px;">
                        <div style="flex:1;min-width:140px;">
                            <label class="control-label" style="font-size:12px">${__("Module")}</label>
                            <select id="dt-module" class="form-control form-control-sm"></select>
                        </div>
                        <div style="flex:2;min-width:200px;">
                            <label class="control-label" style="font-size:12px">${__("Search")}</label>
                            <input id="dt-search" type="text" class="form-control form-control-sm"
                                   placeholder="${__("Filter by name…")}" autocomplete="off">
                        </div>
                        <div style="display:flex;gap:6px;padding-bottom:2px;">
                            <button id="dt-select-all" class="btn btn-xs btn-default">${__("Select All")}</button>
                            <button id="dt-clear" class="btn btn-xs btn-default">${__("Clear")}</button>
                        </div>
                    </div>
                    <div id="dt-list"
                         style="max-height:380px;overflow-y:auto;border:1px solid var(--border-color,#d1d8dd);border-radius:4px;padding:6px 10px;">
                        <p class="text-muted text-center">${__("Loading…")}</p>
                    </div>
                    <div id="dt-status" style="margin-top:6px;font-size:11px;color:var(--text-muted,#8d99a6);"></div>
                `,
            },
        ],
        primary_action_label: __("Add Selected"),
        primary_action: function () {
            let existing = new Set(
                (frm.doc.doctype_list || []).map(r => r.doctype_name)
            );
            selected.forEach(name => {
                if (!existing.has(name)) {
                    frm.add_child("doctype_list", { doctype_name: name });
                }
            });
            frm.refresh_field("doctype_list");
            d.hide();
        },
    });

    d.show();

    let $w = d.$body;

    // Populate module dropdown
    frappe.db.get_list("Module Def", {
        fields: ["name"],
        order_by: "name asc",
        limit: 0,
    }).then(mods => {
        let $sel = $w.find("#dt-module");
        $sel.append(`<option value="">${__("All Modules")}</option>`);
        mods.forEach(m => {
            let n = frappe.utils.escape_html(m.name);
            $sel.append(`<option value="${n}">${n}</option>`);
        });
    });

    // Load all non-child-table DocTypes
    frappe.db.get_list("DocType", {
        filters: { istable: 0 },
        fields: ["name", "module"],
        limit: 0,
        order_by: "name asc",
    }).then(data => {
        all_doctypes = data;
        render_list();
    });

    function visible_items() {
        let module = $w.find("#dt-module").val();
        let search = ($w.find("#dt-search").val() || "").toLowerCase().trim();
        return all_doctypes.filter(dt =>
            (!module || dt.module === module) &&
            (!search || dt.name.toLowerCase().includes(search))
        );
    }

    function render_list() {
        let items = visible_items();
        let $list = $w.find("#dt-list");

        if (!items.length) {
            $list.html(`<p class="text-muted text-center">${__("No DocTypes found")}</p>`);
        } else {
            let rows = items.map(dt => {
                let n = frappe.utils.escape_html(dt.name);
                let m = frappe.utils.escape_html(dt.module || "");
                let chk = selected.has(dt.name) ? "checked" : "";
                return `<label style="display:flex;align-items:center;gap:8px;padding:3px 2px;cursor:pointer;">
                    <input type="checkbox" class="dt-cb" value="${n}" ${chk} style="flex-shrink:0;">
                    <span style="flex:1">${n}</span>
                    <span class="text-muted" style="font-size:11px;">${m}</span>
                </label>`;
            });
            $list.html(rows.join(""));

            $list.find(".dt-cb").on("change", function () {
                $(this).is(":checked")
                    ? selected.add($(this).val())
                    : selected.delete($(this).val());
                update_status();
            });
        }

        update_status();
    }

    function update_status() {
        let items = visible_items();
        $w.find("#dt-status").text(
            __("{0} of {1} DocTypes shown · {2} selected", [
                items.length, all_doctypes.length, selected.size,
            ])
        );
    }

    // Event wiring
    $w.on("change", "#dt-module", render_list);
    $w.on("input", "#dt-search", frappe.utils.debounce(render_list, 250));
    $w.on("click", "#dt-select-all", function () {
        visible_items().forEach(dt => selected.add(dt.name));
        render_list();
    });
    $w.on("click", "#dt-clear", function () {
        visible_items().forEach(dt => selected.delete(dt.name));
        render_list();
    });
}
