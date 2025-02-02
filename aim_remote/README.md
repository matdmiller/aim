# AIM Remote (Upload)

AIM Remote is a simple HTTP server that allows you to upload Aim repositories to a remote server.

## Usage (Server)
To run the AIM Remote server, you can build the included Dockerfile and run it with the following command and substituting the appropriate paths for the upload, aim, and sesskey directories for your local setup or use docker volumes:

```bash
docker build -t aim_remote .
docker run -d -p 8000:8000 -v $(pwd)/upload:/data/upload -v $(pwd)/.aim:/data/.aim -v $(pwd)/sesskey:/data/sesskey aim_remote
```

## Usage (Client)
See the `example/test_run.py` file for an example of how to use the AIM Remote server. The comments in this file specify the specific lines you need to incorporate into your own training run script.

