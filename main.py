from fastapi import FastAPI, Request
import docker
import tempfile
import os

app = FastAPI()


LANG_CONFIG = {
    "python": {
        "image": "python:3.10-slim",
        "command": "python /usr/src/app/script.py"
    },
    "javascript": {
        "image": "node:20",
        "command": "node /usr/src/app/script.js"
    },
    "typescript": {
        "image": "node:20-slim",
        # compile ts, then run js
        "command": "sh -c 'npm install -g typescript && tsc /usr/src/app/script.ts && node /usr/src/app/script.js'"
    },
    "java": {
        "image": "openjdk:17-slim",
        # compile then run
        "command": "sh -c 'javac /usr/src/app/Main.java && java -cp /usr/src/app Main'"
    },
    "c": {
        "image": "gcc:13",
        # compile and run C code
        "command": "sh -c 'gcc /usr/src/app/main.c -o /usr/src/app/main && /usr/src/app/main'"
    },
    "cpp": {
        "image": "gcc:13",
        # compile and run C++ code
        "command": "sh -c 'g++ /usr/src/app/main.cpp -o /usr/src/app/main && /usr/src/app/main'"
    }
}
import time 

def run_user_code(code: str, language: str, user_input: str = "") -> dict:
    client = docker.APIClient()

    if language not in LANG_CONFIG:
        return {"output": "", "error": f"Unsupported language: {language}", "execution_time": 0}

    image = LANG_CONFIG[language]["image"]
    command = LANG_CONFIG[language]["command"]

    with tempfile.TemporaryDirectory() as tmpdir:
        filename = {
    "python": "script.py",
    "javascript": "script.js",
    "typescript": "script.ts",
    "java": "Main.java",
    "c": "main.c",
    "cpp": "main.cpp"
}.get(language)

        if not filename:
            return {"output": "", "error": "Unsupported language", "execution_time": 0}

        code_path = os.path.join(tmpdir, filename)
        with open(code_path, "w") as f:
            f.write(code)

        start_time = time.perf_counter()

        try:
            container = client.create_container(
                image=image,
                command=command,
                host_config=client.create_host_config(
                    binds=[f"{tmpdir}:/usr/src/app:rw"],
                    network_mode="none",
                    mem_limit='100m',
                    cpu_period=100000,
                    cpu_quota=50000,
                ),
                stdin_open=True,
                tty=False
            )

            client.start(container=container.get('Id'))

            if user_input:
                # Send input and close stdin
                sock = client.attach_socket(container=container.get('Id'), params={'stdin': 1, 'stream': 1})
                sock._sock.send(user_input.encode())
                sock._sock.shutdown(1)  # shutdown writing to indicate EOF

            # Wait container to finish
            result = client.wait(container=container.get('Id'))

            # Get logs
            logs = client.logs(container=container.get('Id'), stdout=True, stderr=True).decode()

            end_time = time.perf_counter()
            return {"output": logs, "execution_time": end_time - start_time, "error": ""}

        except docker.errors.APIError as e:
            end_time = time.perf_counter()
            return {"output": "", "error": str(e), "execution_time": end_time - start_time}


@app.post("/run")
async def run_code(request: Request):
    data = await request.json()
    code = data.get("code", "")
    language = data.get("language", "").lower()
    user_input = data.get("input", "")

    if not code or not language:
        return {"error": "Missing code or language"}

    result = run_user_code(code, language, user_input)

    return result
@app.post("/run")
async def run_code(request: Request):
    data = await request.json()
    code = data.get("code", "")
    language = data.get("language", "").lower()
    user_input = data.get("input", "")  # Optional input

    if not code or not language:
        return {"error": "Missing code or language"}

    output = run_user_code(code, language, user_input)

    return {"output": output}
