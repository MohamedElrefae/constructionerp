#!/usr/bin/env python3
"""Migration: Update Construction Dark/Light to enterprise blue/slate palette (Phase 2)"""

import frappe


def after_migrate():
    """Update Construction theme records with enterprise color palette."""

    # ─── Construction Dark (Enterprise) ───
    dark_theme = frappe.db.get_value("Construction Theme", "Construction Dark", "name")
    if dark_theme:
        frappe.db.set_value(
            "Construction Theme",
            "Construction Dark",
            {
                "accent_primary": "#2563EB",  # Blue primary
                "accent_primary_hover": "#3B82F6",  # Blue hover
                "body_bg": "#0F172A",  # Slate-900
                "border_color": "#334155",  # Slate-700
                "navbar_bg": "#1E293B",  # Slate-800
                "sidebar_bg": "#0F172A",  # Slate-900
                "surface_bg": "#1E293B",  # Slate-800
                "text_primary": "#F8FAFC",  # Slate-50
                "text_secondary": "#94A3B8",  # Slate-400
                "primary_btn_bg": "#2563EB",  # Blue
                "primary_btn_text": "#FFFFFF",
                "secondary_btn_bg": "#334155",
                "secondary_btn_text": "#F8FAFC",
                "success_color": "#10B981",  # Emerald
                "warning_color": "#F59E0B",  # Amber
                "error_color": "#EF4444",  # Red
                "preview_colors": '["#0F172A","#2563EB","#1E293B","#F8FAFC","#2563EB33"]',
            },
        )
        frappe.db.commit()
        print("✅ Construction Dark updated to enterprise blue/slate palette")
    else:
        print("⚠️  Construction Dark not found in database")

    # ─── Construction Light (Enterprise) ───
    light_theme = frappe.db.get_value("Construction Theme", "Construction Light", "name")
    if light_theme:
        frappe.db.set_value(
            "Construction Theme",
            "Construction Light",
            {
                "accent_primary": "#2563EB",  # Blue primary
                "accent_primary_hover": "#1D4ED8",  # Blue hover (darker)
                "body_bg": "#F8FAFC",  # Slate-50
                "border_color": "#E2E8F0",  # Slate-200
                "navbar_bg": "#FFFFFF",  # White
                "sidebar_bg": "#F8FAFC",  # Slate-50
                "surface_bg": "#FFFFFF",  # White
                "text_primary": "#0F172A",  # Slate-900
                "text_secondary": "#64748B",  # Slate-500
                "primary_btn_bg": "#2563EB",  # Blue
                "primary_btn_text": "#FFFFFF",
                "secondary_btn_bg": "#F1F5F9",
                "secondary_btn_text": "#0F172A",
                "success_color": "#10B981",  # Emerald
                "warning_color": "#F59E0B",  # Amber
                "error_color": "#EF4444",  # Red
                "preview_colors": '["#F8FAFC","#2563EB","#FFFFFF","#0F172A","#2563EB15"]',
            },
        )
        frappe.db.commit()
        print("✅ Construction Light updated to enterprise blue/slate palette")
    else:
        print("⚠️  Construction Light not found in database")

    # Clear CSS cache to force regeneration
    frappe.cache().delete_keys("construction_theme_css:*")
    print("✅ CSS cache cleared - themes will regenerate on next load")
    print("\nPhase 2 enterprise color palette applied!")
    print("  Primary:  #2563EB (Blue)")
    print("  Dark BG:  #0F172A (Slate-900)")
    print("  Light BG: #F8FAFC (Slate-50)")
