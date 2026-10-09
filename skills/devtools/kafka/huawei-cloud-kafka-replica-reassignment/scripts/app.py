#!/usr/bin/env python3
"""
Flask Web UI for Kafka Replica Reassignment Tool.

Features:
- Upload topic.xlsx / broker.xlsx
- Download blank templates
- Configure params (replica count, disk threshold, JSON strategy)
- Run three-stage pipeline with inter-stage checks
- View generated report
"""

import json
import os
import shutil
import sys

import tempfile
import threading
import time

# The skill package may be read-only after install, and no compile cache belongs in it:
# disable bytecode writing so execution never creates __pycache__ under scripts/.
sys.dont_write_bytecode = True

from flask import Flask, request, jsonify, send_file, render_template, send_from_directory

# Add scripts dir to path for imports
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

import tabio
from stage1_allocate import run as run_stage1
from stage2_merge import run as run_stage2
from stage3_json import run as run_stage3
from validate import run_all_stage_validation, format_checks
from report import generate_report
from generate_templates import generate_all_templates


app = Flask(__name__, template_folder=os.path.join(os.path.dirname(SCRIPTS_DIR), 'templates'))

# Skill version marker: bump whenever scripts change; exposed via /api/status so the UI can
# confirm the running service loaded the latest code (old processes do not hot-reload).
SKILL_VERSION = '1.0.3'

# Global state
# Runtime artifacts must land outside the skill package: the skill dir is usually
# read-only after install (writes would fail), and even when writable, leaving uploads and
# outputs inside the package pollutes it (audits flag work/ as runtime residue). Default to
# the system temp dir; use KAFKA_REASSIGN_WORK_DIR to pin a location.
PACKAGE_DIR = os.path.dirname(SCRIPTS_DIR)
WORK_DIR = os.environ.get('KAFKA_REASSIGN_WORK_DIR') or os.path.join(
    tempfile.gettempdir(), 'kafka-replica-reassignment-work')
UPLOAD_DIR = os.path.join(WORK_DIR, 'uploads')
OUTPUT_DIR = os.path.join(WORK_DIR, 'output')
ASSETS_DIR = os.path.join(PACKAGE_DIR, 'assets')
TEMPLATE_FALLBACK_DIR = os.path.join(WORK_DIR, 'templates')

# Ensure dirs exist
for d in [WORK_DIR, UPLOAD_DIR, OUTPUT_DIR]:
    os.makedirs(d, exist_ok=True)

# Pipeline state
pipeline_state = {
    'status': 'idle',  # idle, running, completed, failed
    'params': {
        'replica_count': 2,
        'disk_threshold': 70,
        'json_strategy': 'size_10g',
        'json_strategy_param': 10,
    },
    'stages': {
        'stage1': {'status': 'pending', 'result': None, 'validation': None},
        'stage2': {'status': 'pending', 'result': None, 'validation': None},
        'stage3': {'status': 'pending', 'result': None, 'validation': None},
    },
    'report_path': None,
    'log': [],
    'start_time': None,
    'uploads': {
        'topic_uploaded': False,
        'topic_filename': None,
        'broker_uploaded': False,
        'broker_filename': None,
    },
    'end_time': None,
}


def log(msg):
    """Add a log entry with timestamp."""
    ts = time.strftime('%H:%M:%S')
    pipeline_state['log'].append(f'[{ts}] {msg}')
    # Keep last 200 entries
    if len(pipeline_state['log']) > 200:
        pipeline_state['log'] = pipeline_state['log'][-200:]


def reset_pipeline():
    """Reset pipeline state for a new run."""
    pipeline_state['status'] = 'idle'
    pipeline_state['stages'] = {
        'stage1': {'status': 'pending', 'result': None, 'validation': None},
        'stage2': {'status': 'pending', 'result': None, 'validation': None},
        'stage3': {'status': 'pending', 'result': None, 'validation': None},
    }
    pipeline_state['report_path'] = None
    pipeline_state['log'] = []
    pipeline_state['start_time'] = None
    pipeline_state['end_time'] = None
    pipeline_state['uploads'] = {
        'topic_uploaded': False,
        'topic_filename': None,
        'broker_uploaded': False,
        'broker_filename': None,
    }
def run_pipeline_thread(topic_path, broker_path, params):
    """Run the full pipeline in a background thread."""
    try:
        pipeline_state['status'] = 'running'
        pipeline_state['start_time'] = time.time()
        pipeline_state['params'] = params
        log(f'Pipeline started with params: {json.dumps(params, ensure_ascii=False)}')

        # Clear the output directory. Guard by prefix: only delete output inside our own
        # work dir, so even a mispointed WORK_DIR env var never removes an unrelated dir.
        out_abs = os.path.abspath(OUTPUT_DIR)
        if out_abs.startswith(os.path.abspath(WORK_DIR) + os.sep) and os.path.exists(out_abs):
            shutil.rmtree(out_abs)
        os.makedirs(out_abs, exist_ok=True)

        # === Stage 1 ===
        pipeline_state['stages']['stage1']['status'] = 'running'
        log('阶段一开始：分配新副本')
        s1_result = run_stage1(
            topic_path, broker_path, OUTPUT_DIR,
            replica_count=params['replica_count'],
            disk_threshold=params['disk_threshold']
        )
        pipeline_state['stages']['stage1']['result'] = s1_result
        log(f'阶段一完成: status={s1_result["status"]}, new_replicas={s1_result.get("stats", {}).get("new_replicas_assigned", 0)}')

        if s1_result['status'] != 'PASS':
            pipeline_state['stages']['stage1']['status'] = 'failed'
            log(f'阶段一失败: {s1_result.get("error", "")}')
            pipeline_state['status'] = 'failed'
            return

        # Stage 1 validation
        from validate import validate_stage1
        s1_checks = validate_stage1(s1_result, OUTPUT_DIR, params['disk_threshold'])
        s1_text, s1_pass = format_checks('阶段一', s1_checks)
        pipeline_state['stages']['stage1']['validation'] = {
            'checks': [{'check': c[0], 'status': c[1], 'detail': c[2]} for c in s1_checks],
            'summary': s1_text,
            'pass': s1_pass,
        }
        log(f'阶段一校验: {"PASS" if s1_pass else "FAIL"}')

        if not s1_pass:
            pipeline_state['stages']['stage1']['status'] = 'validation_failed'
            pipeline_state['status'] = 'failed'
            log('阶段一校验未通过，流水线停止')
            return

        pipeline_state['stages']['stage1']['status'] = 'completed'

        # === Stage 2 ===
        pipeline_state['stages']['stage2']['status'] = 'running'
        log('阶段二开始：合并总表')
        main_csv = os.path.join(OUTPUT_DIR, tabio.MAIN_NAME)
        new_csv = os.path.join(OUTPUT_DIR, tabio.NEW_NAME)
        s2_result = run_stage2(main_csv, new_csv, OUTPUT_DIR, params['replica_count'])
        pipeline_state['stages']['stage2']['result'] = s2_result
        log(f'阶段二完成: status={s2_result["status"]}, merged_rows={s2_result.get("stats", {}).get("merged_rows", 0)}')

        if s2_result['status'] != 'PASS':
            pipeline_state['stages']['stage2']['status'] = 'failed'
            pipeline_state['status'] = 'failed'
            return

        # Stage 2 validation
        from validate import validate_stage2
        s2_checks = validate_stage2(s2_result, OUTPUT_DIR)
        s2_text, s2_pass = format_checks('阶段二', s2_checks)
        pipeline_state['stages']['stage2']['validation'] = {
            'checks': [{'check': c[0], 'status': c[1], 'detail': c[2]} for c in s2_checks],
            'summary': s2_text,
            'pass': s2_pass,
        }
        log(f'阶段二校验: {"PASS" if s2_pass else "FAIL"}')

        if not s2_pass:
            pipeline_state['stages']['stage2']['status'] = 'validation_failed'
            pipeline_state['status'] = 'failed'
            log('阶段二校验未通过，流水线停止')
            return

        pipeline_state['stages']['stage2']['status'] = 'completed'

        # === Stage 3 ===
        pipeline_state['stages']['stage3']['status'] = 'running'
        log('阶段三开始：转 JSON')
        all_csv = os.path.join(OUTPUT_DIR, tabio.ALL_NAME)

        # Parse strategy param
        sp = params.get('json_strategy_param', 10)
        if params['json_strategy'] == 'custom':
            sp = params.get('custom_config', {'big_size': 10, 'small_batch': 10})
        elif params['json_strategy'] == 'topic_count':
            sp = int(sp)
        elif params['json_strategy'] == 'size_10g':
            sp = float(sp)   # threshold may be fractional; int() would silently truncate 10.5 to 10

        s3_result = run_stage3(
            all_csv, OUTPUT_DIR,
            replica_count=params['replica_count'],
            strategy=params['json_strategy'],
            strategy_param=sp
        )
        pipeline_state['stages']['stage3']['result'] = s3_result
        log(f'阶段三完成: status={s3_result["status"]}, files={s3_result.get("stats", {}).get("files_generated", 0)}')

        if s3_result['status'] != 'PASS':
            pipeline_state['stages']['stage3']['status'] = 'failed'
            pipeline_state['status'] = 'failed'
            return

        # Stage 3 validation (already done in stage3_json.py)
        from validate import validate_stage3
        s3_checks = validate_stage3(s3_result)
        s3_text, s3_pass = format_checks('阶段三', s3_checks)
        pipeline_state['stages']['stage3']['validation'] = {
            'checks': [{'check': c[0], 'status': c[1], 'detail': c[2]} for c in s3_checks],
            'summary': s3_text,
            'pass': s3_pass,
        }
        log(f'阶段三校验: {"PASS" if s3_pass else "FAIL"}')

        if not s3_pass:
            pipeline_state['stages']['stage3']['status'] = 'validation_failed'
            pipeline_state['status'] = 'failed'
            log('阶段三校验未通过，流水线停止')
            return

        pipeline_state['stages']['stage3']['status'] = 'completed'

        # === Generate Report ===
        log('生成复核报告')
        all_validation = {
            'stage1': pipeline_state['stages']['stage1']['validation'],
            'stage2': pipeline_state['stages']['stage2']['validation'],
            'stage3': pipeline_state['stages']['stage3']['validation'],
        }
        report_path = os.path.join(OUTPUT_DIR, 'report.html')
        generate_report(s1_result, s2_result, s3_result, all_validation, params, report_path)
        pipeline_state['report_path'] = report_path
        log(f'报告已生成: {report_path}')

        pipeline_state['status'] = 'completed'
        pipeline_state['end_time'] = time.time()
        log('Pipeline 完成！')

    except Exception as e:
        import traceback
        log(f'Pipeline 异常: {str(e)}')
        log(traceback.format_exc())
        pipeline_state['status'] = 'failed'


@app.route('/')
def index():
    """Main UI page."""
    return render_template('index.html')


def ensure_templates():
    """Return (topic_template, broker_template).

    Templates ship as package assets and are normally read from assets/ directly. They are
    only generated on the fly when the assets are missing, and generation writes only to
    the working directory — the installed skill package may be read-only; writing into it
    would error or leave files inside the package.
    """
    topic_path = os.path.join(ASSETS_DIR, 'topic_template.xlsx')
    broker_path = os.path.join(ASSETS_DIR, 'broker_template.xlsx')

    if os.path.exists(topic_path) and os.path.exists(broker_path):
        return topic_path, broker_path

    os.makedirs(TEMPLATE_FALLBACK_DIR, exist_ok=True)
    gen_topic = os.path.join(TEMPLATE_FALLBACK_DIR, 'topic_template.xlsx')
    gen_broker = os.path.join(TEMPLATE_FALLBACK_DIR, 'broker_template.xlsx')
    if not (os.path.exists(gen_topic) and os.path.exists(gen_broker)):
        generate_all_templates(TEMPLATE_FALLBACK_DIR)

    if not os.path.exists(gen_topic) or not os.path.exists(gen_broker):
        raise FileNotFoundError(
            f"模板不可用：包内 {topic_path} 缺失，且无法在 {TEMPLATE_FALLBACK_DIR} 生成")

    return gen_topic, gen_broker


@app.route('/api/templates/<name>')
def download_template(name):
    """Download a template file. Generates on-the-fly if missing."""
    try:
        topic_path, broker_path = ensure_templates()
    except Exception as e:
        return jsonify({'error': f'Failed to generate templates: {str(e)}'}), 500

    if name == 'topic':
        if not os.path.exists(topic_path):
            return jsonify({'error': f'topic_template.xlsx not found at {topic_path}'}), 404
        return send_file(topic_path, as_attachment=True, download_name='topic_template.xlsx')
    elif name == 'broker':
        if not os.path.exists(broker_path):
            return jsonify({'error': f'broker_template.xlsx not found at {broker_path}'}), 404
        return send_file(broker_path, as_attachment=True, download_name='broker_template.xlsx')
    else:
        return jsonify({'error': 'Unknown template'}), 404


@app.route('/api/upload', methods=['POST'])
def upload_files():
    """Upload topic.xlsx or broker.xlsx independently.

    Accepts a single file with field name 'topic' or 'broker'.
    Each file is saved separately; both must be present before running the pipeline.
    Does NOT reset pipeline state on each upload — only resets when /api/run is called.
    """
    # Accept either 'topic' or 'broker' field
    topic_file = request.files.get('topic')
    broker_file = request.files.get('broker')

    if not topic_file and not broker_file:
        return jsonify({'error': 'No file provided. Use field name "topic" or "broker".'}), 400

    uploaded = {}

    if topic_file:
        topic_path = os.path.join(UPLOAD_DIR, 'topic.xlsx')
        topic_file.save(topic_path)
        uploaded['topic'] = topic_file.filename
        pipeline_state['uploads']['topic_uploaded'] = True
        pipeline_state['uploads']['topic_filename'] = topic_file.filename
        log(f'Topic file uploaded: {topic_file.filename}')

    if broker_file:
        broker_path = os.path.join(UPLOAD_DIR, 'broker.xlsx')
        broker_file.save(broker_path)
        uploaded['broker'] = broker_file.filename
        pipeline_state['uploads']['broker_uploaded'] = True
        pipeline_state['uploads']['broker_filename'] = broker_file.filename
        log(f'Broker file uploaded: {broker_file.filename}')

    # Use in-memory flags, not file existence on disk
    topic_ready = pipeline_state['uploads']['topic_uploaded']
    broker_ready = pipeline_state['uploads']['broker_uploaded']

    return jsonify({
        'status': 'ok',
        'message': 'File(s) uploaded successfully',
        'uploaded': uploaded,
        'topic_ready': topic_ready,
        'broker_ready': broker_ready,
        'all_ready': topic_ready and broker_ready,
    })


@app.route('/api/upload-status')
def upload_status():
    """Check which files have been uploaded (in-memory state, not file existence)."""
    topic_ready = pipeline_state['uploads']['topic_uploaded']
    broker_ready = pipeline_state['uploads']['broker_uploaded']
    result = {
        'topic_ready': topic_ready,
        'broker_ready': broker_ready,
        'all_ready': topic_ready and broker_ready,
    }
    if topic_ready:
        result['topic_filename'] = pipeline_state['uploads']['topic_filename']
    if broker_ready:
        result['broker_filename'] = pipeline_state['uploads']['broker_filename']
    return jsonify(result)


@app.route('/api/params', methods=['GET', 'POST'])
def handle_params():
    """Get or set pipeline parameters."""
    if request.method == 'GET':
        return jsonify(pipeline_state['params'])

    data = request.json
    pipeline_state['params'] = {
        'replica_count': int(data.get('replica_count', 2)),
        'disk_threshold': float(data.get('disk_threshold', 70)),
        'json_strategy': data.get('json_strategy', 'size_10g'),
        'json_strategy_param': data.get('json_strategy_param', 10),
    }
    if data.get('custom_config'):
        pipeline_state['params']['custom_config'] = data['custom_config']

    log(f'Params updated: {json.dumps(pipeline_state["params"], ensure_ascii=False)}')
    return jsonify({'status': 'ok', 'params': pipeline_state['params']})


@app.route('/api/run', methods=['POST'])
def run_pipeline():
    """Start the pipeline."""
    topic_path = os.path.join(UPLOAD_DIR, 'topic.xlsx')
    broker_path = os.path.join(UPLOAD_DIR, 'broker.xlsx')

    if not os.path.exists(topic_path) or not os.path.exists(broker_path):
        return jsonify({'error': 'Please upload topic and broker files first'}), 400

    if pipeline_state['status'] == 'running':
        return jsonify({'error': 'Pipeline is already running'}), 409

    reset_pipeline()

    # Get params from request or use defaults
    data = request.json or {}
    params = {
        'replica_count': int(data.get('replica_count', pipeline_state['params']['replica_count'])),
        'disk_threshold': float(data.get('disk_threshold', pipeline_state['params']['disk_threshold'])),
        'json_strategy': data.get('json_strategy', pipeline_state['params']['json_strategy']),
        'json_strategy_param': data.get('json_strategy_param', pipeline_state['params']['json_strategy_param']),
    }
    if data.get('custom_config'):
        params['custom_config'] = data['custom_config']

    pipeline_state['params'] = params

    # Run in background thread
    thread = threading.Thread(target=run_pipeline_thread, args=(topic_path, broker_path, params))
    thread.daemon = True
    thread.start()

    return jsonify({'status': 'started', 'message': 'Pipeline started'})


@app.route('/api/status')
def get_status():
    """Get current pipeline status."""
    return jsonify({
        'status': pipeline_state['status'],
        'stages': pipeline_state['stages'],
        'params': pipeline_state['params'],
        'log': pipeline_state['log'][-50:],  # Last 50 log entries
        'report_available': pipeline_state['report_path'] is not None,
        'elapsed': time.time() - pipeline_state['start_time'] if pipeline_state['start_time'] else 0,
        'skill_version': SKILL_VERSION,
    })


@app.route('/api/report')
def get_report():
    """Get the generated report HTML."""
    if pipeline_state['report_path'] and os.path.exists(pipeline_state['report_path']):
        return send_file(pipeline_state['report_path'])
    return jsonify({'error': 'Report not available'}), 404


@app.route('/api/download/<path:filename>')
def download_output(filename):
    """Download an output file."""
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


@app.route('/api/output-files')
def list_output_files():
    """List all output files."""
    files = []
    for root, dirs, filenames in os.walk(OUTPUT_DIR):
        for fname in filenames:
            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, OUTPUT_DIR)
            files.append({
                'name': rel_path,
                'size': os.path.getsize(fpath),
            })
    return jsonify({'files': files})


if __name__ == '__main__':
    # Generate templates on startup if they don't exist
    try:
        t_path, b_path = ensure_templates()
        print(f'Templates ready: {t_path}')
    except Exception as e:
        print(f'WARNING: Could not generate templates at startup: {e}')
        print('Templates will be generated on first download request.')

    # Clean up any leftover uploaded files from previous sessions
    for fname in ['topic.xlsx', 'broker.xlsx']:
        fpath = os.path.join(UPLOAD_DIR, fname)
        if os.path.exists(fpath):
            os.remove(fpath)
            print(f'Cleaned up leftover file: {fname}')

    port = int(os.environ.get('PORT', 5000))
    print(f'Work dir: {WORK_DIR}')
    print(f'Skill version: {SKILL_VERSION}')
    print(f'Starting Kafka Replica Reassignment UI on port {port}...')
    print(f'Open http://localhost:{port} in your browser')
    app.run(host='0.0.0.0', port=port, debug=False)
