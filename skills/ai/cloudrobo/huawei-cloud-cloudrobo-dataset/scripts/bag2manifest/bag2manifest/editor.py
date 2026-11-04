"""Shared ordered-vector editor for state, action and extra features."""
from __future__ import annotations
import copy
import json
import re
import uuid
import gradio as gr
from . import derive

GRIPPER = re.compile(r'gripper|finger|hand|jaw|claw|suction|width|inner_joint|outer_joint|knuckle', re.I)


def path_of(item):
    return item.get('locator', '') if isinstance(item, dict) else str(item)


def prepare(items):
    result = []
    for value in items or []:
        item = copy.deepcopy(value) if isinstance(value, dict) else {'locator': value}
        item.setdefault('_ui_id', uuid.uuid4().hex)
        if 'role' not in item and GRIPPER.search(str(item.get('locator', '')) + ' '.join(item.get('inputs', []))):
            item['role'] = 'gripper'
        result.append(item)
    return result


def label(item):
    return derive.item_id(item) if 'expr' in item or 'strategy' in item else path_of(item)


def reconcile_refs(previous, current, actions):
    """Keep action references bound to a state dimension through move/delete/undo."""
    positions = {v.get('_ui_id'): i for i, v in enumerate(current or []) if isinstance(v, dict)}
    result = copy.deepcopy(actions or [])
    for item in result:
        if not isinstance(item, dict) or item.get('strategy') != 'next_state':
            continue
        identity = item.get('_state_ref_id')
        index = item.get('state_index', -1)
        if identity is None and isinstance(index, int) and 0 <= index < len(previous or []):
            old = previous[index]
            identity = old.get('_ui_id') if isinstance(old, dict) else None
            if identity:
                item['_state_ref_id'] = identity
        if identity:
            item['state_index'] = positions.get(identity, -1)
    return result


def commit(profile, vec, sel, source, picked, expr, name, gripper, interpolation,
           fallback_text, normalize, norm_mode, norm_min, norm_max, states=None):
    from .webapp import field_index, _new_expr_item
    if not profile:
        raise gr.Error('请先分析 bag')
    vec = prepare(vec)
    picked = list(picked or [])
    adding = not isinstance(sel, int) or not 0 <= sel < len(vec)
    if source == 'field':
        if not picked or (not adding and len(picked) != 1):
            raise gr.Error('修改一维时选择一个字段；新增时可以批量选择')
        if any(key not in field_index(profile) for key in picked):
            raise gr.Error('所选字段在样例中不存在')
        items = [{'locator': key} for key in picked]
    elif source == 'expr':
        item = _new_expr_item(picked, expr, name, False)
        if normalize:
            if norm_mode == 'sample':
                item['normalize'] = True
            elif norm_min is None or norm_max is None or norm_min >= norm_max:
                raise gr.Error('归一化区间必须满足 min < max')
            else:
                item['normalize'] = [float(norm_min), float(norm_max)]
        items = [item]
    elif source == 'next_state':
        try: index = int(picked[0])
        except (ValueError, IndexError, TypeError): raise gr.Error('请选择要引用的状态维度')
        if not 0 <= index < len(states or []): raise gr.Error('状态引用已失效，请重新选择')
        items = [{'strategy': 'next_state', 'state_index': index,
                  '_state_ref_id': states[index]['_ui_id']}]
    else:
        raise gr.Error('未知字段来源')
    fallback = None
    if str(fallback_text or '').strip():
        try: fallback = json.loads(fallback_text)
        except (ValueError, TypeError) as exc: raise gr.Error('缺失默认值请填写数值或 JSON 数值数组') from exc
        values = fallback if isinstance(fallback, list) else [fallback]
        import math
        if not values or any(not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x) for x in values):
            raise gr.Error('缺失默认值必须是有限数值或数值数组')
        if isinstance(fallback, list) and len(fallback) != 1:
            raise gr.Error('当前按单维编辑；默认值数组长度应为1')
    for item in items:
        if name and len(items) == 1: item['name'] = name.strip()
        if gripper: item['role'] = 'gripper'
        if interpolation != 'default': item['interpolation'] = interpolation
        if fallback is not None: item['default'] = fallback
    if adding:
        existing = {path_of(item) for item in vec if 'locator' in item}
        if source == 'field' and any(path_of(item) in existing for item in items):
            raise gr.Error('列表已包含所选字段，请编辑已有维度')
        new = vec + prepare(items)
        return new, len(vec), copy.deepcopy(vec)
    if source == 'field' and any(i != sel and path_of(v) == path_of(items[0]) for i,v in enumerate(vec)):
        raise gr.Error('列表已包含这个字段')
    items[0]['_ui_id'] = vec[sel]['_ui_id']
    old = copy.deepcopy(vec)
    vec[sel] = items[0]
    return vec, sel, old


def mutate(vec, sel, operation, defaults=None):
    old = copy.deepcopy(vec or [])
    new = prepare(vec)
    if operation == 'reset': return prepare(defaults), 0 if defaults else -1, old
    if not isinstance(sel, int) or not 0 <= sel < len(new): raise gr.Error('请先选择一维')
    if operation == 'delete':
        new.pop(sel); sel = min(sel, len(new)-1)
    else:
        target = sel + (-1 if operation == 'up' else 1)
        if 0 <= target < len(new): new[sel],new[target] = new[target],new[sel]; sel = target
    return new, sel, old


def plot_preview(profile, states, vec, selected, picked, normalize, comparison):
    from .webapp import aug_index, _series_fig
    if not profile: return None
    ids = list(picked or [])
    by_id = {v.get('_ui_id'): v for v in vec or [] if isinstance(v, dict)}
    chosen = list(vec or []) if not ids else [by_id[i] if i in by_id else vec[int(i)]
        for i in ids if i in by_id or str(i).isdigit() and 0 <= int(i) < len(vec)]
    index = aug_index(profile, states, vec)
    keys = [derive.item_id(v) if 'expr' in v or 'strategy' in v else path_of(v) for v in chosen]
    dash = []
    if comparison is not None and str(comparison).isdigit() and int(comparison) < len(states or []):
        item = states[int(comparison)]
        key = derive.item_id(item) if 'expr' in item else path_of(item)
        if key in index:
            alias = '状态对比 · ' + key
            index[alias] = index[key]; keys.append(alias); dash.append(alias)
    return _series_fig(index, keys, normalize, '样例曲线预览', dash_ids=dash)


def build_editor(kind, profile, states, strategy=None):
    """Identical layout and event model; action has one extra source type."""
    from .webapp import field_choices, state_topic_choices, field_index, expr_hint
    title = {'state':'状态','action':'动作','extra':'其他特征'}[kind]
    vec=states if kind=='state' else gr.State([]); selected=gr.State(-1); undo=gr.State(None)
    with gr.Row(equal_height=False, elem_classes='vector-workspace'):
        with gr.Column(scale=4,min_width=320):
            gr.Markdown('#### 输出维度\n顺序就是最终输出顺序；索引从0开始。')
            with gr.Row(elem_classes='vector-toolbar'):
                add=gr.Button('＋新增',size='sm',min_width=70); up=gr.Button('↑上移',size='sm',min_width=70,interactive=False)
                down=gr.Button('↓下移',size='sm',min_width=70,interactive=False); delete=gr.Button('删除',size='sm',min_width=70,interactive=False)
            with gr.Row():
                back=gr.Button('撤销上次修改',size='sm',min_width=70,interactive=False)
                reset=gr.Button('恢复自动推断' if kind!='extra' else '清空维度',size='sm',min_width=70)
            rows=gr.Radio(label=f'{title}维度',choices=[],value=None,elem_classes='vector-list')
        with gr.Column(scale=5,min_width=350):
            summary=gr.Markdown('点击“新增”，或选择左侧一维进行编辑。')
            choices=[('原始字段','field'),('计算公式','expr')]
            if kind=='action': choices.append(('下一帧状态','next_state'))
            source=gr.Radio(choices,value='field',label='字段来源')
            with gr.Group() as fields_group:
                topic=gr.Dropdown(choices=[('全部话题','*')],value='*',label='话题筛选')
                fields=gr.Dropdown(label='搜索并选择字段（公式输入按选择顺序绑定 f0、f1…）',choices=[],value=[],multiselect=True,filterable=True)
            with gr.Group(visible=False) as formula_group:
                mapping=gr.Markdown()
                formula=gr.Textbox(label='计算公式',placeholder='例如 abs(f0) + abs(f1)')
                normalization=gr.Checkbox(label='写入公式归一化配置',value=False)
                with gr.Row(visible=False) as norm_group:
                    norm_mode=gr.Radio([('样例范围','sample'),('指定区间','fixed')],value='sample',label='区间来源')
                    lo=gr.Number(label='min',value=0); hi=gr.Number(label='max',value=1)
            with gr.Group(visible=False) as next_group:
                reference=gr.Dropdown(label='引用状态维度（跟随状态移动）',choices=[],value=None)
                gr.Markdown('动作取该状态维度的下一帧；末帧复制。删除被引用状态后必须重新选择。')
            name=gr.Textbox(label='输出名称（可选）')
            role=gr.Checkbox(label='这是夹爪维度（role: gripper）',value=False)
            defaults=gr.Markdown("当前默认插值：**linear**（普通存储动作；夹爪为 nearest）。" if kind=="action" else "当前默认插值：**nearest**。")
            with gr.Accordion('高级字段设置',open=False):
                interpolation=gr.Radio([('默认','default'),'nearest','linear','front'],value='default',label='字段插值')
                fallback=gr.Textbox(label='无消息时的默认值（可选）',placeholder='0.0 或 [0.0]；留空使用算子默认')
            with gr.Row():
                save=gr.Button('添加维度',variant='primary'); cancel=gr.Button('取消 / 还原编辑',size='sm',min_width=70)
            preview_formula=gr.Button('预览未保存的公式',visible=False)
    gr.Markdown('#### 曲线预览\n默认显示当前表单全部字段，新增、删除或修改后自动更新。点击图例可隐藏曲线；显示归一化仅影响曲线。以下为降采样样例，尚未执行转换器的时间对齐。')
    with gr.Row():
        plotted=gr.Dropdown(label='曲线筛选（留空显示表单全部字段）',choices=[],value=[],multiselect=True)
        normalized=gr.Checkbox(label='归一化显示曲线（不修改配置）',value=False)
        compare=gr.Dropdown(label='叠加状态维度',choices=[],value=None,visible=kind=='action')
    plot=gr.Plot(label=f'{title}样例曲线')

    def filter_fields(p,t,values):
        options=field_choices(p) if p else []
        allowed=[(label,key) for label,key in options if t=='*' or field_index(p)[key]['topic']==t]
        keys={key for _,key in allowed}
        return gr.update(choices=allowed,value=[v for v in values or [] if v in keys])
    topic.input(filter_fields,[profile,topic,fields],[fields])
    fields.change(expr_hint,[fields],[mapping],queue=False)
    def init(p):
        return gr.update(choices=[('全部话题','*')]+state_topic_choices(p),value='*'),gr.update(choices=field_choices(p) if p else [],value=[])
    profile.change(init,[profile],[topic,fields])
    def load(p,items,sel):
        from .webapp import render_vec
        valid=isinstance(sel,int) and 0<=sel<len(items or [])
        item=items[sel] if valid else {}
        mode='expr' if 'expr' in item else 'next_state' if 'strategy' in item else 'field'
        values=item.get('inputs',[]) if mode=='expr' else [path_of(item)] if valid and mode=='field' else []
        norm=item.get('normalize'); interval=norm if isinstance(norm,list) else [0,1]
        message=f'**正在编辑索引 {sel}：** `{label(item)}`' if valid else '**新增维度** · 原始字段可批量添加，公式产生一维。'
        return (message,gr.update(value=mode),gr.update(choices=field_choices(p) if p else [],value=values),
                gr.update(value='*'),item.get('expr',''),item.get('name',''),item.get('role')=='gripper',
                item.get('interpolation') or 'default',json.dumps(item['default']) if 'default' in item else '',
                bool(norm), 'fixed' if isinstance(norm,list) else 'sample',interval[0],interval[1],
                gr.update(value=str(item.get('state_index')) if mode=='next_state' and item.get('state_index',-1)>=0 else None),
                gr.update(value='保存修改' if valid else '添加维度'),
                gr.update(visible=mode!='next_state'),gr.update(visible=mode=='expr'),
                gr.update(visible=mode=='next_state'),gr.update(visible=mode=='expr'),gr.update(visible=bool(norm)))
    editor_outputs=[summary,source,fields,topic,formula,name,role,interpolation,fallback,normalization,norm_mode,lo,hi,reference,save,fields_group,formula_group,next_group,preview_formula,norm_group]
    def select(value): return int(value) if value is not None else -1
    rows.input(select,[rows],[selected]).then(load,[profile,vec,selected],editor_outputs)
    add.click(lambda:-1,None,[selected]).then(load,[profile,vec,selected],editor_outputs)
    cancel.click(load,[profile,vec,selected],editor_outputs)
    def layout(mode): return gr.update(visible=mode!='next_state'),gr.update(visible=mode=='expr'),gr.update(visible=mode=='next_state'),gr.update(visible=mode=='expr')
    source.change(layout,[source],[fields_group,formula_group,next_group,preview_formula],queue=False)
    normalization.change(lambda v:gr.update(visible=v),[normalization],[norm_group],queue=False)
    def default_hint(gripper,method):
        actual='nearest' if kind!='action' or gripper else 'linear'
        return f'当前插值：**{actual if method=="default" else method}**。' + ('来源为下一帧状态时，按状态引用处理。' if kind=='action' else '')
    role.change(default_hint,[role,interpolation],[defaults],queue=False)
    interpolation.change(default_hint,[role,interpolation],[defaults],queue=False)
    def update_list(p,items,sel,history,filters):
        from .webapp import render_vec
        details=render_vec(p,items) if p else []
        options=[]
        for i,item in enumerate(items or []):
            span=f'[{details[i][3]}, {details[i][4]}]' if details[i][3] is not None else '范围未知'
            flags=' · '+details[i][2] if details[i][2] else ''
            options.append((f'{i} · {label(item)}{flags} · {span}',i))
        valid=isinstance(sel,int) and 0<=sel<len(items or [])
        return (gr.update(choices=options,value=sel if valid else None),gr.update(interactive=valid and sel>0),
                gr.update(interactive=valid and sel<len(items)-1),gr.update(interactive=valid),gr.update(interactive=history is not None),
                gr.update(choices=[(f'{i}: {label(v)}',v['_ui_id']) for i,v in enumerate(items or [])],
                          value=[key for key in filters or [] if any(v.get('_ui_id')==key for v in items or [])]))
    for trigger in (vec,selected,undo):
        trigger.change(update_list,[profile,vec,selected,undo,plotted],[rows,up,down,delete,back,plotted],queue=False)
    vec.change(load,[profile,vec,selected],editor_outputs)
    selected.change(load,[profile,vec,selected],editor_outputs)
    def apply(p,items,sel,mode,values,expression,nm,grip,interp,fb,norm,nmode,mn,mx,ref,st,act_strategy):
        if kind=='action' and act_strategy!='stored': raise gr.Error('编辑动作维度时请先选择存储指令 stored')
        return commit(p,items,sel,mode,[ref] if mode=='next_state' else values,expression,nm,grip,interp,fb,norm,nmode,mn,mx,st)
    constant_strategy=gr.State('stored')
    save.click(apply,[profile,vec,selected,source,fields,formula,name,role,interpolation,fallback,normalization,norm_mode,lo,hi,reference,states,strategy if strategy is not None else constant_strategy],[vec,selected,undo])
    for button,operation in ((up,'up'),(down,'down'),(delete,'delete')):
        button.click(lambda v,s,op=operation:mutate(v,s,op),[vec,selected],[vec,selected,undo])
    def reset_items(p,items,sel):
        from .webapp import default_choices
        initial=default_choices(p)[kind] if kind!='extra' and p else []
        return mutate(items,sel,'reset',initial)
    reset.click(reset_items,[profile,vec,selected],[vec,selected,undo])
    back.click(lambda current,history:(copy.deepcopy(history or []),0 if history else -1,copy.deepcopy(current)),[vec,undo],[vec,selected,undo])
    def ref_options(items,current):
        options=[(f'{i}: {label(v)}',str(i)) for i,v in enumerate(items or [])]
        valid={value for _,value in options}
        return gr.update(choices=options,value=current if current in valid else None),gr.update(choices=options,value=None)
    states.change(ref_options,[states,reference],[reference,compare],queue=False)
    for trigger in (vec,plotted,normalized,compare,states):
        trigger.change(plot_preview,[profile,states,vec,selected,plotted,normalized,compare],[plot])
    def draft(p,st,items,sel,values,expression,nm,norm):
        from .webapp import _new_expr_item
        item=_new_expr_item(values,expression,nm,False)
        draft_items=prepare(items)
        if isinstance(sel,int) and 0<=sel<len(draft_items): draft_items[sel]=prepare([item])[0]
        else: draft_items+=prepare([item])
        return plot_preview(p,st,draft_items,-1,[],norm,None)
    preview_formula.click(draft,[profile,states,vec,selected,fields,formula,name,normalized],[plot])
    return {'vec':vec,'selected':selected,'undo':undo,'rows':rows,'plot':plot,'source':source,'summary':summary,'reload':load,'editor_outputs':editor_outputs}
