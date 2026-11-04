"""Behavioral regression checks for unified field editing and stable references."""
from pathlib import Path
import sys
import tempfile
import subprocess
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bag2manifest.editor import prepare, commit, mutate, reconcile_refs, plot_preview
from bag2manifest.manifest import build_manifest, default_choices, validate_manifest, manifest_to_yaml
from bag2manifest.profiler import profile_bag, ProfileOptions
from bag2manifest.webapp import render_vec

bag=Path(tempfile.mkdtemp(prefix='b2m_editor_'))/'synth.mcap'
subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'tools/make_synth_bag.py'),'-o',str(bag),'--seconds','10'],check=True,stdout=subprocess.DEVNULL)
p=profile_bag(bag,ProfileOptions()); ch=default_choices(p)
st=prepare(ch['state']); ac=prepare(ch['action'])
assert render_vec(p,st)[0][3] is not None
ac,sel,history=commit(p,ac,-1,'next_state',['7'],'','gripper_exp',True,'default','',False,'sample',0,1,st)
assert ac[-1]['state_index']==7
moved,_,undo=mutate(st,7,'up'); ac=reconcile_refs(st,moved,ac)
assert ac[-1]['state_index']==6
removed,_,_=mutate(moved,6,'delete'); broken=reconcile_refs(moved,removed,ac)
assert broken[-1]['state_index']==-1
restored=reconcile_refs(removed,moved,broken); assert restored[-1]['state_index']==6
replaced,_,_=commit(p,moved,6,'expr',['/my_robot/gripper_state.width'],'f0 * 1000','gripper_mm',True,'nearest','0',False,'fixed',0,100,moved)
assert replaced[6]['_ui_id']==moved[6]['_ui_id']
restored=reconcile_refs(moved,replaced,restored); assert restored[-1]['state_index']==6
ch.update(state=replaced,action=restored)
plan=build_manifest(p,ch); errors=[i for i in validate_manifest(plan,p) if i['level']=='error']
assert not errors,errors
text=manifest_to_yaml(plan); assert '_ui_id' not in text and '_state_ref_id' not in text
assert plan['state'][0]['names_from']=='embedded'
assert plot_preview(p,replaced,restored,len(restored)-1,[],False,'0') is not None
ch['action']=broken
assert any(i['code']=='E114' for i in validate_manifest(build_manifest(p,ch),p))
# Modify an existing formula without appending another dimension.
current=prepare([{'expr':'f0','inputs':['/my_robot/gripper_state.width'],'name':'g'}])
changed,index,old=commit(p,current,0,'expr',['/my_robot/gripper_state.width'],'where(f0 > 0.04, 0, 100)','g',True,'nearest','100',False,'sample',0,1,st)
assert len(changed)==1 and changed[0]['expr'].startswith('where') and old==current
print('Unified editor: replacement, move, delete/undo, stable references and export checks passed')

# Empty curve filter means the whole form, regardless of which row is selected.
all_plot=plot_preview(p,st,st,0,[],False,None)
assert len(all_plot.data)==len(st)==8
assert len(plot_preview(p,st,st,7,[],False,None).data)==8
removed,_,_=mutate(st,7,'delete')
assert len(plot_preview(p,removed,removed,0,[],False,None).data)==7
added,_,_=commit(p,removed,-1,'field',['/my_robot/gripper_state.width'],'','',True,'default','',False,'sample',0,1,removed)
assert len(plot_preview(p,added,added,0,[],False,None).data)==8
# Explicit curve filters bind to dimensions by identity across reorder.
filtered=plot_preview(p,st,st,0,[st[7]['_ui_id']],False,None)
assert len(filtered.data)==1 and 'gripper' in filtered.data[0].hovertemplate
moved,_,_=mutate(st,7,'up')
assert len(plot_preview(p,moved,moved,0,[st[7]['_ui_id']],False,None).data)==1
assert len(plot_preview(p,st,ac,0,[],False,None).data)==len(ac)
print('All-field previews update on add/delete; row selection does not filter traces')
