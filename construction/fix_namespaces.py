import os
import glob
import re

base_dir = '/home/mohamed/construction-erp/frappe-bench/apps/construction/construction'

# 1. Update theme_templates/*.css.j2
template_dir = os.path.join(base_dir, 'theme_templates')
for filepath in glob.glob(os.path.join(template_dir, '*.css.j2')):
    with open(filepath, 'r') as f:
        content = f.read()

    # Replace data-modern-theme="{{ theme_name }}" with data-theme="{{ 'dark' if is_dark_mode else 'light' }}"
    # Some templates might use data-modern-theme="{{ normalized_key }}" or similar
    content = re.sub(r'\[data-modern-theme="\{\{\s*[^}]+\s*\}\}"\]', '[data-theme="{{ \'dark\' if is_dark_mode else \'light\' }}"]', content)

    with open(filepath, 'w') as f:
        f.write(content)

print("Updated jinja templates")

# 2. Update api/theme_api.py
api_path = os.path.join(base_dir, 'api', 'theme_api.py')
with open(api_path, 'r') as f:
    api_content = f.read()
api_content = api_content.replace('[data-modern-theme="{normalized_key}"]', '[data-theme="{ \'dark\' if is_dark else \'light\' }"]')
with open(api_path, 'w') as f:
    f.write(api_content)

print("Updated theme_api.py")

# 3. Update doctype/construction_theme/construction_theme.py
doctype_path = os.path.join(base_dir, 'doctype', 'construction_theme', 'construction_theme.py')
with open(doctype_path, 'r') as f:
    doctype_content = f.read()

old_block = 'css_block = f\'html[data-modern-theme="{identifier}"]{{\' + ";".join(variables) + ";}"'
new_block = 'mode = "dark" if is_dark_theme else "light"\n\t\tcss_block = f\'html[data-theme="{mode}"]{{\' + ";".join(variables) + ";}"'
doctype_content = doctype_content.replace(old_block, new_block)

with open(doctype_path, 'w') as f:
    f.write(doctype_content)

print("Updated construction_theme.py")
