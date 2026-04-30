"""
Dependency Audit Script for frappe_desk_theme Uninstall
Scans all app directories for references to "frappe_desk_theme"
"""

import json
import os
import re
from pathlib import Path


def scan_for_references(root_dir, pattern="frappe_desk_theme"):
	"""
	Scan all Python, JavaScript, and JSON files for references to frappe_desk_theme

	Returns:
	    dict: {
	        "python_files": [...],
	        "javascript_files": [...],
	        "json_files": [...],
	        "total_references": int
	    }
	"""
	results = {"python_files": [], "javascript_files": [], "json_files": [], "total_references": 0}

	# File extensions to scan
	extensions = {".py": "python_files", ".js": "javascript_files", ".json": "json_files"}

	# Regex pattern for case-insensitive search
	pattern_re = re.compile(pattern, re.IGNORECASE)

	for root, dirs, files in os.walk(root_dir):
		# Skip common directories
		skip_dirs = {".git", "__pycache__", "node_modules", ".pytest_cache", ".hypothesis", ".venv", "venv"}
		dirs[:] = [d for d in dirs if d not in skip_dirs]

		for file in files:
			file_path = os.path.join(root, file)
			ext = os.path.splitext(file)[1]

			if ext not in extensions:
				continue

			try:
				with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
					content = f.read()

					if pattern_re.search(content):
						# Count occurrences
						count = len(pattern_re.findall(content))
						results[extensions[ext]].append({"file": file_path, "count": count})
						results["total_references"] += count
			except Exception as e:
				print(f"Error reading {file_path}: {e}")

	return results


def generate_report(results):
	"""Generate a human-readable report of findings"""
	print("\n" + "=" * 80)
	print("FRAPPE_DESK_THEME DEPENDENCY AUDIT REPORT")
	print("=" * 80 + "\n")

	print(f"Total References Found: {results["total_references"]}\n")

	if results["python_files"]:
		print("Python Files:")
		for item in results["python_files"]:
			print(f"  - {item["file"]} ({item["count"]} references)")

	if results["javascript_files"]:
		print("\nJavaScript Files:")
		for item in results["javascript_files"]:
			print(f"  - {item["file"]} ({item["count"]} references)")

	if results["json_files"]:
		print("\nJSON Files:")
		for item in results["json_files"]:
			print(f"  - {item["file"]} ({item["count"]} references)")

	if results["total_references"] == 0:
		print("✓ No references to frappe_desk_theme found!")
		print("Safe to proceed with uninstall.")
	else:
		print("\n⚠ WARNING: References to frappe_desk_theme found!")
		print("These must be resolved before uninstalling the app.")

	print("\n" + "=" * 80 + "\n")

	return results["total_references"] == 0


if __name__ == "__main__":
	import sys

	# Scan from current directory or provided path
	scan_path = sys.argv[1] if len(sys.argv) > 1 else "."

	print(f"Scanning {scan_path} for frappe_desk_theme references...")
	results = scan_for_references(scan_path)
	is_safe = generate_report(results)

	sys.exit(0 if is_safe else 1)
