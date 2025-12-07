#!/usr/bin/env python

# the shebang only works if you are already in the uv's venv
# the easiest way to open up the venv is to just run 'uv run main.py' once
# then you can use the shebang on that terminal session

import uvicorn
if __name__ == "__main__":
    host = "localhost"
    port = 8080
    uvicorn.run("src.server:app",host=host, port=port, reload=True)