import os
import uvicorn

port = os.getenv("SERVER_PORT", "5000")
workers_count = int(os.getenv("WORKERS_COUNT", "1"))

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(port), workers=workers_count)
