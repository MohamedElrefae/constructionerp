from . import __version__ as app_version

app_name = "construction"
app_title = "Construction ERP"
app_publisher = "Mohamed Elrefae"
app_description = "Construction ERP App for BOQ, Cost Estimation, and Project Management"
app_email = "melrefa3@hotmail.com"
app_license = "MIT"

module_app = {
    "construction": "construction",
}

# Doctype-specific JavaScript files
# Paths are relative to the app module folder (construction/construction/)
doctype_js = {
    "BOQ Header": "construction/doctype/boq_header/boq_header.js"
}

doctype_tree_js = {
    "BOQ Structure": "construction/doctype/boq_structure/boq_structure_tree.js"
}

# Global JS includes (raw asset path — loaded directly, not bundled)
app_include_js = [
    "/assets/construction/js/print_settings_dialog.js",
    "/assets/construction/js/construction_export_menu.js"
]

# Fixtures — exported records that ship with the app
fixtures = [
    {"dt": "Workspace", "filters": [["module", "=", "construction"]]}
]

