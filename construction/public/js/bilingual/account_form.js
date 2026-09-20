// Construction bilingual pilot — Account form identity section (Stage 3).
//
// Loaded via doctype_js hook AFTER the vendor account.js. Extends the form:
// - Identity section: English name, Arabic name, code, live preview,
//   completeness, controlled Arabic edit.
// - Arabic-only edits go through the governed Construction API which can
//   never rename the document (server-enforced via the Account validate
//   hook, Version-audited, canonical Unicode policy applied server-side).
// - English/code changes go through ONE governed endpoint that requires a
//   reason, delegates to the standard ERPNext rename path, resolves the
//   post-rename identity server-side, and records the reason atomically.
// - Every visible string is wrapped in __() for localization governance.

frappe.ui.form.on("Account", {
  refresh(frm) {
    if (frm.is_new()) return;
    ct_bilingual_render_identity(frm);
  },
});

function ct_bilingual_render_identity(frm) {
  frappe.call({
    method: "construction.services.bilingual_service.get_account_identity",
    args: { name: frm.doc.name },
    quiet: true,
    callback(r) {
      const ident = r.message;
      if (!ident) return;
      ct_bilingual_upsert_section(frm, ident);
    },
  });
}

function ct_bilingual_upsert_section(frm, ident) {
  let wrap = frm.fields_dict.ct_bilingual_identity;
  if (!wrap) {
    const section = frm.dashboard.add_section(
      [
        '<div class="ct-bilingual-identity" style="margin-bottom:8px;">',
        '<div class="ct-bi-row"><b>' + __("English") + ':</b> <span class="ct-bi-en"></span></div>',
        '<div class="ct-bi-row"><b>' + __("Arabic") + ':</b> <span class="ct-bi-ar"></span> ',
        '<button class="btn btn-xs btn-default ct-bi-edit-ar">' + __("Edit Arabic") + "</button></div>",
        '<div class="ct-bi-row"><b>' + __("Code") + ':</b> <span class="ct-bi-code"></span></div>',
        '<div class="ct-bi-row"><b>' + __("Preview") + ':</b> <span class="ct-bi-preview"></span></div>',
        '<div class="ct-bi-row"><b>' + __("Completeness") + ':</b> <span class="ct-bi-complete"></span></div>',
        '<div class="ct-bi-row"><button class="btn btn-xs btn-default ct-bi-rename">' +
          __("Change English name / code (standard path)") +
          "</button></div>",
        "</div>",
      ].join("")
    );
    wrap = { $wrapper: section };
    frm.fields_dict.ct_bilingual_identity = wrap;
  }
  const $w = wrap.$wrapper;
  $w.find(".ct-bi-en").text(ident.english || "-");
  $w.find(".ct-bi-ar").text(ident.arabic || "-");
  $w.find(".ct-bi-code").text(ident.code || "-");
  const preview_parts = [];
  if (ident.code) preview_parts.push(ident.code);
  preview_parts.push(ident.arabic || ident.english || ident.identity);
  $w.find(".ct-bi-preview").text(preview_parts.join(" - "));
  const missing = (ident.completeness && ident.completeness.missing) || [];
  $w
    .find(".ct-bi-complete")
    .text(
      ident.completeness && ident.completeness.complete
        ? __("Complete")
        : __("Missing") + ": " + missing.join(", ")
    );

  $w.find(".ct-bi-edit-ar")
    .off("click")
    .on("click", function () {
      ct_bilingual_edit_arabic(frm, ident);
    });
  $w.find(".ct-bi-rename")
    .off("click")
    .on("click", function () {
      ct_bilingual_standard_rename(frm, ident);
    });
}

function ct_bilingual_edit_arabic(frm, ident) {
  frappe.prompt(
    {
      fieldname: "arabic_name",
      fieldtype: "Data",
      label: __("Account Name (Arabic)"),
      default: ident.arabic || "",
      reqd: 1,
    },
    function (values) {
      frappe.call({
        method: "construction.services.bilingual_service.set_account_name_ar",
        args: { name: frm.doc.name, arabic_name: values.arabic_name },
        callback() {
          frappe.show_alert({ message: __("Arabic name updated"), indicator: "green" });
          frm.reload_doc();
        },
      });
    },
    __("Edit Arabic name (identity is not renamed)")
  );
}

function ct_bilingual_standard_rename(frm, ident) {
  // One governed call: reason required, standard ERPNext path preserved,
  // post-rename identity resolved server-side, reason recorded atomically.
  frappe.prompt(
    [
      { fieldname: "account_name", fieldtype: "Data", label: __("New English account name"), default: ident.english || "", reqd: 1 },
      { fieldname: "account_number", fieldtype: "Data", label: __("New account number"), default: ident.code || "" },
      { fieldname: "reason", fieldtype: "Small Text", label: __("Reason (required, recorded)"), reqd: 1 },
    ],
    function (values) {
      frappe.call({
        method: "construction.services.bilingual_service.governed_rename_account",
        args: {
          name: frm.doc.name,
          account_name: values.account_name,
          account_number: values.account_number || null,
          reason: values.reason,
        },
        callback(r) {
          frappe.show_alert({
            message: __("Identity updated via the standard path; reason recorded"),
            indicator: "green",
          });
          const new_name = r.message && r.message.name;
          if (new_name && new_name !== frm.doc.name) {
            frappe.set_route("Form", "Account", new_name);
          } else {
            frm.reload_doc();
          }
        },
      });
    },
    __("Change English name / code (standard ERPNext path)")
  );
}
