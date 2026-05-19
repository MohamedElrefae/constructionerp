import os
import glob
import re

base_dir = '/home/mohamed/construction-erp/frappe-bench/apps/construction/construction'
template_dir = os.path.join(base_dir, 'theme_templates')

for filepath in glob.glob(os.path.join(template_dir, '*.css.j2')):
    with open(filepath, 'r') as f:
        content = f.read()

    # Remove ' !important' or '!important' globally
    content = re.sub(r'\s*!important\b', '', content)

    with open(filepath, 'w') as f:
        f.write(content)

print("Removed !important from all jinja templates")
