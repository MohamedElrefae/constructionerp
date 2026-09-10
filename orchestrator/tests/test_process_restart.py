"""Kill the coordinator while an external synthetic worker is in flight."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from core import utc, write_json
from engine import Engine
from test_engine import Stub


def test_kill_and_resume_keeps_external_job_single_dispatch(configured, tmp_path):
    root, config = configured
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config))
    driver = tmp_path / "coordinator.py"
    worker = tmp_path / "synthetic_worker.py"
    worker.write_text("""import json,sys,time
from pathlib import Path
job=json.loads(Path(sys.argv[1]).read_text());d=Path(job['runtime'])
while not (d/'release').exists():time.sleep(.05)
body=job['spec']['envelope'];body['session_id']='synthetic-'+job['job_id']
(d/'stdout.jsonl').write_text(json.dumps({'body':body,'wire':{'plan_text':'Synthetic restart plan','explanation':'SYNTHETIC'}}))
from core import write_json,utc
write_json(d/'terminal.json',dict(job_id=job['job_id'],phase='TERMINAL',exit_code=0,timeout=False,started_utc=utc(),finished_utc=utc()),immutable=True)
""")
    driver.write_text("""import json,sys,subprocess,os
from pathlib import Path
from engine import Engine
config=json.loads(Path(sys.argv[1]).read_text())
def launch(job):
 p=Path(job['runtime'])/'fixture-job.json';p.write_text(json.dumps(job))
 subprocess.Popen([sys.executable,sys.argv[2],str(p)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
e=Engine(config['root'],launcher=launch);e.initialize(config);e.run()
os._exit(137)
""")
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
    p = subprocess.run([sys.executable, str(driver), str(config_file), str(worker)], env=env, timeout=10)
    assert p.returncode == 137
    stub = Stub(delayed=True)
    e = Engine(root, launcher=stub)
    job_id = e.view()["active_jobs"][0]
    job = e.store.job(job_id)
    assert e.run()["active_jobs"] == [job_id]
    assert not stub.starts
    (Path(job["runtime"]) / "release").touch()
    deadline = time.monotonic() + 5
    while not (Path(job["runtime"]) / "terminal.json").exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert (Path(job["runtime"]) / "terminal.json").exists()
    e.run()
    assert job_id not in stub.starts
    assert len([event for event in e.store.events() if event["event_id"] == "result-" + job_id]) == 1
    e.close()
