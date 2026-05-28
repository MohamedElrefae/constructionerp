# Searchable Dropdown Module Hooks
# Registers assets and API endpoints

app_name = "searchable_dropdown"
app_title = "Searchable Dropdown"
app_publisher = "Construction ERP"
app_description = "Enhanced dropdown search for ERPNext"
app_version = "1.0.0"

# Include JS/CSS in desk
desk_include_js = [
    "/assets/construction/js/searchable_dropdown/utils.js",
    "/assets/construction/js/searchable_dropdown/searchable_dropdown.js",
]

desk_include_css = [
    "/assets/construction/css/searchable_dropdown.css",
]

# Whitelist APIs
whitelisted_methods = {
    "construction.searchable_dropdown.api.search.searchable_link_search": {"allow_guest": False}
}
