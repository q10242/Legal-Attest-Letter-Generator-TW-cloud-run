import uvicorn
from fastapi import FastAPI, Request

app = FastAPI()


@app.get("/")
async def index(request: Request):
    """
    首頁
    """
    return {"msg": "Hello ", "code": 0}


def main():
    # 啟動主應用程式
    uvicorn.run("server:app",
                host="0.0.0.0",
                port=8070)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        raise e
