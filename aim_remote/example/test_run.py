#### UPLOAD REPO TO REMOTE SERVER FUNCTION ####
# This function is used to upload the Aim repository to the remote server. 
# You will need to incorporate this function and imports into your own training run script.
from pathlib import Path
import shutil, httpx, os, json
from datetime import datetime

# Create .env file with the following 2 keys in your script directory or remove the .dotenv import 
# and load_dotenv lines and set/use env vars directly
import dotenv
dotenv.load_dotenv()
AIM_CLIENT_REQUEST_HEADERS = json.loads(os.environ['AIM_CLIENT_REQUEST_HEADERS'])
AIM_REMOTE_SERVER_URL = os.environ['AIM_REMOTE_SERVER_URL'] #https://aim-upload-lrg.matdmiller.com/upload

def upload_repo():
    server_url = AIM_REMOTE_SERVER_URL
    repo_path = Path('.aim')
    if not repo_path.exists(): raise ValueError(f"AIM repo not found at {repo_path}")
    zip_filepath = repo_path.resolve().parent/'aim_repo.zip'
    if zip_filepath.exists(): zip_filepath.unlink()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    upload_filename = f'aim_repo_{timestamp}.zip'
    shutil.make_archive(str(zip_filepath.with_suffix('')), 'zip', str(repo_path))

    with open(zip_filepath, 'rb') as f:
        response = httpx.post(server_url, files={'file': (upload_filename, f)}, headers=AIM_CLIENT_REQUEST_HEADERS, timeout=1200)
        response.raise_for_status()
    print(f'File upload: {upload_filename} success!\nHTTP RESPONSE:\n{response.text}')

    print('repo_path', repo_path, 'zip_filepath', zip_filepath, 'upload_filename', upload_filename, 'zip_filepath.exists()', zip_filepath.exists())
#### END UPLOAD REPO TO REMOTE SERVER FUNCTION ####


from aim import Run

run = Run(repo='.aim', experiment='aim_remote_test') ### Set the repo location to the .aim directory in the current folder

run["hparams"] = {
    "learning_rate": 0.001,
    "batch_size": 32
}

for i in range(50):
    run.track(i, name='loss', step=i, context={ "subset":"train" })
    run.track(i, name='acc', step=i, context={ "subset":"train" })

run.close() ## Close the run to ensure all data is flushed to the Aim repo before uploading

upload_repo() ### Upload the repo to the server