import os,sys,json,hashlib
from pathlib import Path
LAB=Path(__file__).resolve().parent
os.environ['FRAPPE_BENCH_ROOT']=str(LAB);os.chdir(LAB/'sites')
sys.path[:0]=[str(LAB/'apps/construction'),str(LAB/'apps/erpnext')]
import frappe,construction
site='f31upgrade.localhost'
frappe.init(site);frappe.connect();frappe.set_user('Administrator')
command=sys.argv[1]
if command=='scope-on':
    settings=frappe.get_single('Construction Settings');before=settings.enable_scope_context
    settings.enable_scope_context=1;settings.save();frappe.db.commit()
    print('Lab scope posture:',before,'->',frappe.db.get_single_value('Construction Settings','enable_scope_context'))
elif command=='files':
    result={}
    for row in frappe.get_all('File',fields=['name','file_url','is_private','attached_to_doctype','attached_to_name']):
        url=row.file_url or ''
        path=None
        if url.startswith('/private/files/'):path=LAB/'sites'/site/'private/files'/url.removeprefix('/private/files/')
        elif url.startswith('/files/'):path=LAB/'sites'/site/'public/files'/url.removeprefix('/files/')
        result[row.name]={'url':url,'private':row.is_private,'parent_type':row.attached_to_doctype,'parent_name':row.attached_to_name,'exists':path.exists() if path else None,'sha256':hashlib.sha256(path.read_bytes()).hexdigest() if path and path.is_file() else None}
    (LAB/'artifacts'/sys.argv[2]).write_text(json.dumps(result,indent=2))
    print('Recorded file hashes:',len(result),'missing local files:',sum(r['exists'] is False for r in result.values()))
frappe.db.rollback();frappe.destroy()
