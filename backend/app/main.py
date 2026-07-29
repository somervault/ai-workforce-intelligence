from fastapi import FastAPI

app = FastAPI(
    title="AI Workforce Intelligence Platform",
    description="Enterprise AI platform for Digital Employee Twin and Workforce Analytics",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "message": "AI Workforce Intelligence Platform API is running 🚀"
    }