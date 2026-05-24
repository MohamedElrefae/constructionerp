frappe.provide("construction.sidebar");

$(document).on("sidebar_setup", function (event, data) {
    var sidebar = data.sidebar;
    var wrapper = $(sidebar.wrapper)[0];
    if (!wrapper) return;

    // Capture phase fires BEFORE Frappe's bubble-phase toggle handler.
    // We collapse old sections first, then Frappe opens the clicked one — no flash.
    wrapper.addEventListener("click", function (e) {
        var section = e.target.closest(".sidebar-item-container.section-item");
        if (!section) return;

        // Don't act on link clicks (Frappe skips toggling for links too)
        if (e.target.closest("a")) return;

        var allSections = wrapper.querySelectorAll(".sidebar-item-container.section-item");
        for (var i = 0; i < allSections.length; i++) {
            var other = allSections[i];
            if (other === section) continue;
            var $use = $(other).find(".drop-icon use");
            if ($use.attr("href") === "#icon-chevron-down") {
                $use.attr("href", "#icon-chevron-right");
                $(other).find(".nested-container").addClass("hidden");
            }
        }
    }, true);
});
