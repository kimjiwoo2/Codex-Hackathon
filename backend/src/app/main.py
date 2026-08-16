from fastapi import FastAPI

app = FastAPI(title="Codex Hackathon API", version="0.1.0")


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return the server availability for local checks and CI smoke tests."""
    return {"status": "ok"}
