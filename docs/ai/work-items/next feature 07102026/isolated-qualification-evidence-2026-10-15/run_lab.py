import json
import os
import secrets
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent
os.environ["FRAPPE_BENCH_ROOT"] = str(LAB)
os.chdir(LAB / "sites")
sys.path.insert(0, str(LAB / "apps/erpnext"))
sys.path.insert(0, str(LAB / "apps/construction"))
import frappe

# Native bench command discovery imports apps before binding the site.
import construction

command = sys.argv[1]
site = sys.argv[2] if len(sys.argv) > 2 else None
secret_file = LAB / "run/credentials.json"
if command == "init-auth":
    import pymysql

    credentials = {"db_root": secrets.token_urlsafe(32), "admin": secrets.token_urlsafe(32)}
    conn = pymysql.connect(unix_socket=str(LAB / "run/mariadb.sock"), user="root", password="")
    with conn.cursor() as c:
        c.execute("ALTER USER 'root'@'localhost' IDENTIFIED BY %s", (credentials["db_root"],))
    conn.close()
    fd = os.open(secret_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(credentials, f)
    print("Isolated authentication configured; credentials retained locally, not displayed.")
elif command == "new":
    from frappe.installer import _new_site

    credentials = json.loads(secret_file.read_text())
    frappe.init(site, new_site=True)
    _new_site(
        db_name=None,
        site=site,
        db_root_username="root",
        db_root_password=credentials["db_root"],
        admin_password=credentials["admin"],
        db_socket=str(LAB / "run/mariadb.sock"),
        install_apps=["erpnext", "construction"],
        mariadb_user_host_login_scope="localhost",
    )
    print("Fresh installation completed:", site)
elif command == "restore-new":
    from frappe.installer import _new_site

    credentials = json.loads(secret_file.read_text())
    backup = Path(sys.argv[3]).resolve()
    frappe.init(site, new_site=True)
    _new_site(
        db_name=None,
        site=site,
        db_root_username="root",
        db_root_password=credentials["db_root"],
        admin_password=credentials["admin"],
        db_socket=str(LAB / "run/mariadb.sock"),
        source_sql=str(backup),
        mariadb_user_host_login_scope="localhost",
    )
    print("Restored isolated upgrade site:", site)
    cfg_path = LAB / "sites" / site / "site_config.json"
    cfg = json.loads(cfg_path.read_text())
    backup_cfg = json.loads(Path(sys.argv[4]).read_text()) if len(sys.argv) > 4 else {}
    if backup_cfg.get("encryption_key"):
        cfg["encryption_key"] = backup_cfg["encryption_key"]
    cfg.update({"pause_scheduler": 1, "disable_scheduler": 1, "mute_emails": 1, "maintenance_mode": 0})
    cfg_path.write_text(json.dumps(cfg, indent=2))
    cfg_path.chmod(0o600)
    from frappe.installer import extract_files

    for archive in sys.argv[5:]:
        frappe.destroy()
        copied = extract_files(site, archive)
        Path(copied).unlink()
    print("Files restored; outbound jobs/email disabled in lab.")
elif command == "restore-existing":
    from frappe.commands.site import _restore

    assert site == "f31upgrade.localhost"
    credentials = json.loads(secret_file.read_text())
    backup = LAB / "artifacts/recovery-backup"
    cfg_path = LAB / "sites" / site / "site_config.json"
    cfg = json.loads(cfg_path.read_text())
    assert cfg.get("db_socket") == str(LAB / "run/mariadb.sock")
    saved_cfg = json.loads(next(backup.glob("*site_config_backup.json")).read_text())
    cfg_path.write_text(json.dumps(saved_cfg, indent=2))
    cfg_path.chmod(0o600)
    frappe.init(site)
    import time

    started = time.monotonic()
    _restore(
        site=site,
        sql_file_path=str(next(backup.glob("*database.sql.gz"))),
        db_root_username="root",
        db_root_password=credentials["db_root"],
        admin_password=credentials["admin"],
        force=False,
        with_public_files=str(next(backup.glob("*-files.tar"))),
        with_private_files=str(next(backup.glob("*-private-files.tar"))),
    )
    elapsed = time.monotonic() - started
    (LAB / "artifacts/recovery-timing.json").write_text(
        json.dumps(
            {
                "database_files_restore_seconds": round(elapsed, 3),
                "scope": "native restore of isolated copied site; code already restored; excludes operator response time",
            },
            indent=2,
        )
    )
    print(
        "Restored backed-up lab database/files/configuration without compatibility force; seconds:",
        round(elapsed, 3),
    )
elif command == "snapshot":
    frappe.init(site)
    frappe.connect()
    frappe.set_user("Administrator")
    data = {
        "site": site,
        "apps": frappe.get_installed_apps(),
        "app_path": frappe.get_app_path("construction"),
        "counts": {},
        "settings": {},
        "schema": {},
    }
    for dt in [
        "BOQ Header",
        "BOQ Item",
        "BOQ Structure",
        "BOQ Cost Analysis",
        "BOQ Quantity Revision",
        "Variation Order",
        "File",
        "User",
        "Custom DocPerm",
    ]:
        if frappe.db.exists("DocType", dt):
            data["counts"][dt] = frappe.db.count(dt)
    if frappe.db.exists("DocType", "Construction Settings"):
        settings = frappe.get_single("Construction Settings")
        for key in [
            "enable_scope_context",
            "enable_boq_excel_import_preview",
            "enable_boq_excel_import_commit",
            "enable_stage_measurement_ui",
        ]:
            data["settings"][key] = settings.get(key)
    data["maintainer_role"] = bool(frappe.db.exists("Role", "Cost Database Maintainer"))
    data["company_custom_roles"] = frappe.get_all(
        "Custom DocPerm", filters={"parent": "Company"}, pluck="role"
    )
    data["workspaces"] = frappe.get_all(
        "Workspace", filters={"module": ["in", ["Construction", "construction"]]}, pluck="name"
    )
    data["sidebars"] = (
        frappe.get_all(
            "Sidebar",
            filters={"module": ["in", ["Construction", "construction"]]},
            fields=["name", "title", "standard"],
        )
        if frappe.db.exists("DocType", "Sidebar")
        else []
    )
    import hashlib

    data["business_hashes"] = {}
    for dt in [
        "BOQ Header",
        "BOQ Item",
        "BOQ Structure",
        "BOQ Cost Analysis",
        "BOQ Cost Analysis Detail",
        "BOQ Quantity Revision",
        "Variation Order",
        "VO Line",
    ]:
        if frappe.db.exists("DocType", dt):
            rows = frappe.get_all(dt, fields=["*"], order_by="name")
            for row in rows:
                for key in ["modified", "modified_by", "_user_tags", "_comments", "_assign", "_liked_by"]:
                    row.pop(key, None)
            data["business_hashes"][dt] = hashlib.sha256(
                json.dumps(rows, sort_keys=True, default=str).encode()
            ).hexdigest()
    data["headers"] = (
        frappe.get_all(
            "BOQ Header",
            fields=["name", "status", "project", "total_contract_value", "total_budgeted_cost"],
            order_by="name",
        )
        if frappe.db.exists("DocType", "BOQ Header")
        else []
    )
    data["analyses"] = (
        frappe.get_all(
            "BOQ Cost Analysis",
            fields=["name", "docstatus", "workflow_state"]
            if frappe.get_meta("BOQ Cost Analysis").has_field("workflow_state")
            else ["name", "docstatus", "analysis_status"],
            order_by="name",
        )
        if frappe.db.exists("DocType", "BOQ Cost Analysis")
        else []
    )
    for dt in ["CostItem", "PlantResource"]:
        data["schema"][dt] = {
            "doctype": bool(frappe.db.exists("DocType", dt)),
            "table": frappe.db.table_exists(dt),
        }
    (LAB / "artifacts" / sys.argv[3]).write_text(json.dumps(data, indent=2, default=str))
    frappe.db.rollback()
    frappe.destroy()
    print("Recorded non-secret state:", sys.argv[3])
elif command == "cli":
    from frappe.utils.bench_helper import main

    sys.argv = ["bench", "frappe", *sys.argv[2:]]
    main()
else:
    raise SystemExit("Unknown operation")
