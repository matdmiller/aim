import queue
from fastcore.parallel import threaded
from fasthtml.common import *
from pathlib import Path
import uuid, subprocess, shutil
from datetime import datetime
import os

# Setup paths
UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR', './upload'))
AIM_REPO = Path(os.getenv('AIM_REPO', './.aim'))
AIM_REMOTE_PORT = int(os.getenv('AIM_REMOTE_PORT', 8000))

UPLOAD_DIR.mkdir(exist_ok=True)

if not AIM_REPO.exists():
    print(subprocess.check_call('aim init'.split()))

app, rt = fast_app(key_fname=os.environ['SESSKEY_FNAME'])

uploads = queue.Queue()
running = True
processor_thread = None
def ts(): return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

@threaded
def process_uploads():
    print('process_uploads Thread started...')
    while running:
        try:
            upload_id = uploads.get(timeout=1)  # 1 sec timeout allows clean shutdown
            print(f'Processing upload {upload_id}...')
            with (UPLOAD_DIR/'processor.log').open('a') as f:
                f.write(f"{ts()} {upload_id} STARTED\n")
            upload_dir = UPLOAD_DIR/upload_id
            zip_file = next(upload_dir.glob('*.zip'))
            shutil.unpack_archive(zip_file, upload_dir/'.aim')
            aim_ls_cmd = f"aim runs --repo {upload_dir/'.aim'} ls"
            print('aim_ls_cmd:', aim_ls_cmd)
            run_id = ' '.join(subprocess.check_output(aim_ls_cmd.split()).decode().strip().split('Total')[0].split())
            print('run_id:', run_id)
            with (UPLOAD_DIR/'processor.log').open('a') as f:
                f.write(f"{ts()} {upload_id} run_id: {run_id}\n")
            aim_cp_cmd = f"aim runs --repo {upload_dir/'.aim'} cp --destination {AIM_REPO} {run_id}"
            print('aim_cp_cmd', aim_cp_cmd)
            subprocess.check_call(aim_cp_cmd.split())
            with (UPLOAD_DIR/'processor.log').open('a') as f:
                f.write(f"{ts()} {upload_id} SUCCESS\n")
        except queue.Empty:
            continue
    print('process_uploads Thread exited cleanly...')


def start_processor():
    global processor_thread
    if processor_thread is None or not processor_thread.is_alive():
        processor_thread = process_uploads()


@rt('/upload')
async def post(file: UploadFile):
    upload_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    filename, content = "",""
    try:
        upload_path = UPLOAD_DIR/upload_id
        upload_path.mkdir()
        content = await file.read()
        filename = file.filename
        if not (filename.startswith('aim_remote') and filename.endswith('.zip')):
            raise Exception(f"Invalid filename: {filename}")
        zip_path = upload_path/filename
        zip_path.write_bytes(content)
        with (UPLOAD_DIR/'upload.log').open('a') as f:
            f.write(f"{timestamp} {upload_id} {filename} {len(content)} SUCCESS\n")
        uploads.put(upload_id)
        return JSONResponse({"status": "success", "upload_id": upload_id})
    except Exception as e:
        with (UPLOAD_DIR/'upload.log').open('a') as f:
            f.write(f"{timestamp} {upload_id} {filename} {len(content)} ERROR\n{e}\n")
        return JSONResponse({"status": "error", "timestamp": str(timestamp), "upload_id": upload_id})


@rt('/shutdown')
def get():
    global running
    running = False
    if processor_thread:
        processor_thread.join(timeout=10)  # Wait up to 10 seconds for clean shutdown
    return "Shutting down processor..."

@rt('/upload_log')
def get():
    return Div(*[(P(line) for line in (UPLOAD_DIR/'upload.log').read_text().split('\n'))], style='border: 1px solid blue;')

@rt('/processor_log')
def get():
    return Div(*[(P(line) for line in (UPLOAD_DIR/'processor.log').read_text().split('\n'))], style='border: 1px solid blue;')

@rt('/')
def get():
    global running, processor_thread, uploads 
    return Titled('AIM Uploader Status',Div(
        Div(
            Button('Shutdown', hx_get='/shutdown', hx_confirm='Are you really sure you want to shutdown the processor? The server must be restarted to start it again.'),
            Button('Upload Log', hx_get='/upload_log', hx_target='#upload_log_content'),
            Div(id='upload_log_content'),
            Button('Processor Log', hx_get='/processor_log', hx_target='#processor_log_content'),
            Div(id='processor_log_content'),
            style='display: flex; flex-direction: column; gap: 8px;'
        ),
        P(f'Processor Thread Running: {processor_thread.is_alive() if processor_thread else False}'),
        P(f'Uploads Processor Queue: {uploads.qsize()}'),
        P(f'Uploaded files: {len(list(UPLOAD_DIR.glob("*")))}'),
        *[P(f'{f.name} {datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")}') 
          for f in sorted(UPLOAD_DIR.glob('*'), key=lambda f: f.stat().st_mtime, reverse=True)],
    ))


start_processor()
serve(port=AIM_REMOTE_PORT)