"""Install this wheel into a temporary CPU environment, then cross both RPCs."""
import json
import os
from pathlib import Path
import subprocess
import sys
import venv

from tests.test_rpc_config import core_config


def test_installed_wheel_factory_in_actor_and_selector_interpreters(tmp_path):
    repo=Path(__file__).resolve().parents[1]
    wheels=tmp_path/"wheels"
    subprocess.run([sys.executable,"-m","pip","wheel",str(repo),"--no-deps","--no-build-isolation",
                    "--wheel-dir",str(wheels)],check=True,capture_output=True,text=True)
    envroot=tmp_path/"environment"
    venv.EnvBuilder(with_pip=False,system_site_packages=True).create(envroot)
    python=envroot/("Scripts/python.exe" if os.name=="nt" else "bin/python")
    subprocess.run([str(python),"-m","pip","install","--no-deps","--no-index",str(next(wheels.glob("*.whl")))],
                   check=True,capture_output=True,text=True)
    outside=tmp_path/"outside"; outside.mkdir()
    environment=os.environ.copy()
    environment.pop("PYTHONPATH",None); environment.pop("PYTHONHOME",None)
    site=Path(subprocess.check_output([str(python),"-c","import sysconfig; print(sysconfig.get_path('purelib'))"],
                                     cwd=outside,env=environment,text=True).strip())
    (site/"egrs_cpu_fake.py").write_bytes((repo/"testsupport/installed_backend.py").read_bytes())
    script='''
import json,sys
from pathlib import Path
import egrs,numpy as np
assert Path(egrs.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
from egrs.policy import make_policy
from egrs.sidecar import inspect_sidecar
from egrs.datacli import main as data_main
assert data_main(['catalog'])==0
core=json.loads(sys.argv[1])
output=Path(sys.argv[2])
runtime={'python_executable':sys.executable,'startup_timeout_seconds':30,'predict_timeout_seconds':15}
config={'core':core,'output_dir':str(output),'variant':'no_lora','history':True,
  'goal_change_capability':'custom_hook',
  'actor':{'policy_factory':'egrs_cpu_fake:actor','runtime':runtime,'execution':{'random_seed':7}},
  'selector':{'factory':'egrs_cpu_fake:selector','runtime':runtime}}
policy=make_policy(config)
try:
    policy.reset()
    observation={'agentview_image':np.zeros((8,8,3),dtype=np.uint8),
      'robot0_eye_in_hand_image':np.zeros((8,8,3),dtype=np.uint8)}
    a=policy.predict(observation,'please put cup on plate')
    b=policy.predict(observation,'please put cup on plate')
    assert np.all(a==0) and np.all(b==1), 'goal-change hook failed inside actor worker'
finally:
    policy.close()
report=inspect_sidecar(output/'episode-000001.jsonl')
assert report['status']=='partial' and report['actor_calls']==2
assert report['images']==6 and report['supplied_images']==6
print('INSTALLED_WORKERS_OK')
'''
    result=subprocess.run([str(python),"-c",script,json.dumps(core_config()),str(tmp_path/"run")],
                          cwd=outside,env=environment,capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+result.stderr
    assert "INSTALLED_WORKERS_OK" in result.stdout
