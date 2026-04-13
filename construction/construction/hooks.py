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

doctype_js = {
    "BOQ Header": "construction/doctype/boq_header/boq_header.js"
}

doctype_tree_js = {
    "BOQ Structure": "construction/public/js/boq_structure_tree.js"
}
