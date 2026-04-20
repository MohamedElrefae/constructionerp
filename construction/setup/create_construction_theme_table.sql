-- Create Construction Theme table directly
-- Run this in MySQL/MariaDB

CREATE TABLE IF NOT EXISTS `tabConstruction Theme` (
    `name` VARCHAR(255) NOT NULL PRIMARY KEY,
    `theme_name` VARCHAR(255) NOT NULL,
    `emoji_icon` VARCHAR(10) DEFAULT '🎨',
    `is_active` TINYINT(1) DEFAULT 1,
    `theme_type` VARCHAR(50) NOT NULL,
    `is_system_theme` TINYINT(1) DEFAULT 0,
    `is_default_light` TINYINT(1) DEFAULT 0,
    `is_default_dark` TINYINT(1) DEFAULT 0,
    `accent_primary` VARCHAR(7),
    `accent_primary_hover` VARCHAR(7),
    `accent_secondary` VARCHAR(7),
    `navbar_bg` VARCHAR(7),
    `sidebar_bg` VARCHAR(7),
    `surface_bg` VARCHAR(7),
    `body_bg` VARCHAR(7),
    `text_primary` VARCHAR(7),
    `text_secondary` VARCHAR(7),
    `border_color` VARCHAR(7),
    `success_color` VARCHAR(7) DEFAULT '#28a745',
    `warning_color` VARCHAR(7) DEFAULT '#ffc107',
    `error_color` VARCHAR(7) DEFAULT '#dc3545',
    `preview_colors` TEXT,
    `contrast_ratio` FLOAT,
    `description` TEXT,
    `custom_css` LONGTEXT,
    `creation` DATETIME,
    `modified` DATETIME,
    `modified_by` VARCHAR(255),
    `owner` VARCHAR(255),
    `docstatus` TINYINT(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add indexes
CREATE INDEX IF NOT EXISTS `construction_theme_active` ON `tabConstruction Theme` (`is_active`);
CREATE INDEX IF NOT EXISTS `construction_theme_type` ON `tabConstruction Theme` (`theme_type`);
CREATE INDEX IF NOT EXISTS `construction_theme_system` ON `tabConstruction Theme` (`is_system_theme`);
