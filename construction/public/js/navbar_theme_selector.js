/**
 * Navbar Theme Selector for ERPNext — Construction ERP
 * VERSION: 1.0 — Persistent Navbar Dropdown
 * 
 * This file overrides the navbar template to include a persistent theme selector
 * that works like the search bar and notification icons - server-side rendered.
 */

// Override the navbar template to include theme selector
frappe.templates['navbar'] = `
<header class="navbar navbar-expand" data-html-block="header">
	<div class="container">
		<a class="navbar-brand" href="/app">
			<img class="navbar-logo" src="{{ frappe.boot.app_logo_url }}">
		</a>
		<ul class="nav navbar-nav">
			<li class="nav-item">
				<a class="nav-link" href="#" onclick="return false;">
					<span class="notifications-icon">
						<svg class="icon icon-md"><use href="#icon-notification"></use></svg>
					</span>
				</a>
			</li>
			
			<!-- Theme Selector Dropdown -->
			<li class="nav-item dropdown" id="theme-selector-dropdown">
				<a class="nav-link dropdown-toggle" href="#" data-toggle="dropdown" aria-expanded="false" onclick="return false;">
					<span id="theme-selector-icon">🌙</span>
					<span class="theme-selector-label" id="theme-selector-label">Construction Dark</span>
				</a>
				<ul class="dropdown-menu dropdown-menu-right" role="menu">
					<li>
						<a class="dropdown-item" href="#" onclick="window.switchTheme('light'); return false;">
							<span class="theme-icon">☀️</span> Light
						</a>
					</li>
					<li>
						<a class="dropdown-item" href="#" onclick="window.switchTheme('dark'); return false;">
							<span class="theme-icon">🌙</span> Dark
						</a>
					</li>
					<li class="dropdown-divider"></li>
					<li>
						<a class="dropdown-item" href="#" onclick="window.switchTheme('construction_light'); return false;">
							<span class="theme-icon">🏗️</span> Construction Light
						</a>
					</li>
					<li>
						<a class="dropdown-item" href="#" onclick="window.switchTheme('construction_dark'); return false;">
							<span class="theme-icon">🏗️</span> Construction Dark
						</a>
					</li>
				</ul>
			</li>
			
			<li class="nav-item dropdown dropdown-navbar-user dropdown-mobile">
				<a class="nav-link dropdown-toggle" data-toggle="dropdown" href="#" onclick="return false;">
					<span class="user-image"></span>
					<span class="full-name"></span>
					<span class="user-avatar"></span>
					<span class="user-initials"></span>
				</a>
				<ul class="dropdown-menu dropdown-menu-right" role="menu">
					<li><a class="dropdown-item" href="/app/user-profile">Profile</a></li>
					<li class="dropdown-divider"></li>
					<li><a class="dropdown-item" href="/?cmd=web_logout">Logout</a></li>
				</ul>
			</li>
		</ul>
	</div>
</header>
`;

// Theme switcher function
window.switchTheme = function(theme) {
    console.log('[Theme Selector] Switching to:', theme);
    
    // Map theme names
    var themeMap = {
        'light': 'light',
        'dark': 'dark',
        'construction_light': 'construction_light',
        'construction_dark': 'construction_dark'
    };
    
    var targetTheme = themeMap[theme] || theme;
    
    // Set theme attributes
    document.documentElement.setAttribute('data-theme', targetTheme);
    
    // Set modern theme attribute for construction themes
    if (targetTheme.includes('construction')) {
        document.documentElement.setAttribute('data-modern-theme', targetTheme);
    } else {
        document.documentElement.removeAttribute('data-modern-theme');
    }
    
    // Update UI
    updateThemeSelectorUI(targetTheme);
    
    // Persist to server
    frappe.call({
        method: 'frappe.core.doctype.user.user.switch_theme',
        args: { theme: targetTheme },
        callback: function(r) {
            console.log('[Theme Selector] Saved to server');
        },
        error: function() {
            console.log('[Theme Selector] Failed to save to server, using localStorage');
            localStorage.setItem('theme', targetTheme);
        }
    });
    
    // Apply CSS
    applyThemeCSS(targetTheme);
};

// Update the theme selector UI
function updateThemeSelectorUI(theme) {
    var icon = document.getElementById('theme-selector-icon');
    var label = document.getElementById('theme-selector-label');
    
    if (!icon || !label) return;
    
    var themeConfig = {
        'light': { icon: '☀️', label: 'Light' },
        'dark': { icon: '🌙', label: 'Dark' },
        'construction_light': { icon: '🏗️', label: 'Construction Light' },
        'construction_dark': { icon: '🏗️', label: 'Construction Dark' }
    };
    
    var config = themeConfig[theme] || themeConfig['dark'];
    icon.textContent = config.icon;
    label.textContent = config.label;
}

// Apply theme CSS
function applyThemeCSS(theme) {
    // Remove old dynamic CSS
    var oldCss = document.getElementById('construction-theme-css');
    if (oldCss) oldCss.remove();
    
    // Construction themes use inline CSS from modern_theme_loader
    if (theme.includes('construction')) {
        var css = document.createElement('style');
        css.id = 'construction-theme-css';
        // CSS will be injected by modern_theme_loader if available
        document.head.appendChild(css);
    }
}

// Initialize on page load
$(document).on('page-change', function() {
    // Update UI based on current theme
    var currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    updateThemeSelectorUI(currentTheme);
});

// Initial update
frappe.after_ajax(function() {
    var currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    updateThemeSelectorUI(currentTheme);
});

console.log('[Theme Selector] Navbar override loaded');
