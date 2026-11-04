"""ROS Manifest 2.0 contract and Web callback regression checks."""
from pathlib import Path
import copy
import sys
import tempfile
import subprocess
from unittest import TestCase
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gradio as gr
import numpy as np
import yaml
from bag2manifest import derive
from bag2manifest.manifest import build_manifest, default_choices, validate_manifest, manifest_to_yaml
from bag2manifest.profiler import profile_bag, ProfileOptions
from bag2manifest.webapp import build_ui, do_generate_guided, do_revalidate, do_action_next_state

tmp = Path(tempfile.mkdtemp(prefix='b2m_v2_'))
bag = tmp / 'synth.mcap'
subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / 'tools/make_synth_bag.py'), '-o', str(bag), '--seconds', '10'], check=True, stdout=subprocess.DEVNULL)
p = profile_bag(bag, ProfileOptions())
ch = default_choices(p)
ch['action'].append({'strategy': 'next_state', 'state_index': 7, 'name': 'gripper_exp', 'role': 'gripper'})
plan = build_manifest(p, ch)
def codes(value):
    return {i['code'] for i in validate_manifest(value, p) if i['level'] == 'error'}
assert not codes(plan), codes(plan)
assert plan['state'][0]['names'] == [f'panda_joint{i}' for i in range(1, 8)]
assert plan['action']['fields'][0]['names'] == [f'action_{i}' for i in range(7)]
assert plan['source']['time']['tolerance_ms'] == 17
assert 'time' not in plan and 'segment' not in plan and 'quality' not in plan
assert yaml.safe_load(manifest_to_yaml(plan))['schema_version'] == '2.0'
assert np.array_equal(derive.eval_array('where(f0 > 0.1, 0, 100)', ['a'], {'a':[0,0.2]}), [100,0])
for expr in ('where(f0, 1)', 'f0.__class__', '__import__("os")', '0 < f0 < 1'):
    with TestCase().assertRaises(derive.ExprError, msg=expr):
        derive.check_expr(expr)
for changes, expected in [({'schema_version':'1.0'},'U060'), ({'source_type':'h5'},'U060'),
        ({'cameras':{}},'U060'), ({'state':['/joint_states.position']},'E106'),
        ({'action':{'strategy':'delta_state'}},'U001'), ({'action':{'strategy':'topic'}},'U001'),
        ({'source':{'bag_glob':'*.db3', 'segment':{'mode':'time_gap'}}},'M014'),
        ({'source':{'bag_glob':'*.db3', 'time':{'on_stale':'drop'}}},'M012'),
        ({'task':{'mode':'sidecar'}},'U021'), ({'curation':[]},'E127')]:
    bad=copy.deepcopy(plan); bad.update(changes); assert expected in codes(bad), (changes,codes(bad))
bad=copy.deepcopy(plan); bad['action']['fields'][-1]['state_index']=8; assert 'E114' in codes(bad)
bad=copy.deepcopy(plan); bad['action']['fields'][-1]['role']='arm'; assert 'E116' in codes(bad)
bad=copy.deepcopy(plan); bad['state'][0]['names_from']='explicit'; assert 'E115' in codes(bad)
bad=copy.deepcopy(plan); bad['state'][1]['normalize']=[0,1]; assert 'E119' in codes(bad)
fallback=copy.deepcopy(plan)
fallback['action']['fields']=[{'locator':'/absent.data','names':['j0','j1'], 'default':[0,1], 'interpolation':'front'},
                             {'expr':'where(f0 > 0.1, 0, 100)', 'inputs':['/empty.data[0]'], 'role':'gripper', 'default':100}]
assert not codes(fallback), codes(fallback)
fallback['action']['fields'][0]['default']=[0]; assert 'E120' in codes(fallback)
# Web: preserved wizard builds, mixed action callback works, invalid YAML cannot download.
app=build_ui(); assert len(app.config['components']) > 100
vec=do_action_next_state(p,ch['state'],default_choices(p)['action'],'stored',7,'gripper_exp',True)[0]
assert vec[-1]['state_index']==7
cams=[[c['enabled'],c['name'],c['topic'],c['depth'],'',''] for c in ch['cameras']]
args=(cams,ch['state'],'stored',vec,{},False,'demo/v2','unknown',30,'topic','',ch['task_topic'],
      'per_bag',30,'hold',0,'auto','*.mcap','auto',1000,100,200,'checks: {}')
text,report,files=do_generate_guided(p,True,*args)
assert files and yaml.safe_load(text)['curation']=={'checks':{}}
with TestCase().assertRaisesRegex(gr.Error, '检测到多个候选动作话题'):
    do_generate_guided(p,False,*args)
bad=copy.deepcopy(plan); bad['cameras']={}; assert do_revalidate(p,yaml.safe_dump(bad))[1] is None
assert do_revalidate(p,text)[1]
print('Manifest 2.0 and Web callback regression checks passed')
