import argparse
import uvicorn

def main():
    parser = argparse.ArgumentParser(description="Scheduler CLI.")
    parser.add_argument("--port", type=int, default=8000, help="API server port.")
    parser.add_argument("--host", default="0.0.0.0", help="API server host.")
    args = parser.parse_args()
    uvicorn.run("main:app", host=args.host, port=args.port, reload=True)
