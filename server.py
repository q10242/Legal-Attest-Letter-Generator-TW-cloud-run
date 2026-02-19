import uvicorn, os, json, time, threading, socket
import tempfile
import shutil
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import random
import string
from lal_modules import core


app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    首頁
    """
    return templates.TemplateResponse("index.html", {
        "request": request,
    })


@app.get("/privacy-policy", response_class=HTMLResponse)
async def privacy_policy(request: Request):
    """
    隱私權政策頁面
    """
    return templates.TemplateResponse("privacy-policy.html", {
        "request": request,
    })


@app.get("/faq", response_class=HTMLResponse)
async def faq(request: Request):
    """
    常見問題頁面
    """
    return templates.TemplateResponse("faq.html", {
        "request": request,
    })


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    """
    關於我們頁面
    """
    return templates.TemplateResponse("about.html", {
        "request": request,
    })


@app.get("/terms", response_class=HTMLResponse)
async def terms(request: Request):
    """
    服務條款頁面
    """
    return templates.TemplateResponse("terms.html", {
        "request": request,
    })


@app.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    """
    聯絡我們頁面
    """
    return templates.TemplateResponse("contact.html", {
        "request": request,
    })


@app.get("/sitemap", response_class=HTMLResponse)
async def sitemap(request: Request):
    """
    網站地圖頁面
    """
    return templates.TemplateResponse("sitemap.html", {
        "request": request,
    })


@app.get("/_ops/db-tcp-test")
async def db_tcp_test():
    host = os.getenv("DB_HOST", "10.140.0.10")
    port = int(os.getenv("DB_PORT", "3306"))
    s = socket.socket()
    s.settimeout(4)
    try:
        s.connect((host, port))
        banner = s.recv(32)
        return {"ok": True, "host": host, "port": port, "banner": banner.decode("latin1", errors="ignore")}
    except Exception as e:
        return {"ok": False, "host": host, "port": port, "error": str(e)}
    finally:
        s.close()


@app.post("/generate")
async def generate(request: Request):
    """
    產生檔案
    """
    json_request = await request.json()
    json_request = json.loads(json_request)
    from_data = json_request["from"]
    to_data = json_request["to"]
    copy_data = json_request["copy"]
    text = json_request["text"]
    senders_addr = []
    senders = []
    receivers = []
    receivers_addr = []
    ccs = []
    cc_addr = []
    for i in range(len(from_data)):
        senders.append(str(from_data[i]["name"]))
        senders_addr.append(str(from_data[i]["address"]))
    for i in range(len(to_data)):
        receivers.append(str(to_data[i]["name"]))
        receivers_addr.append(str(to_data[i]["address"]))
    for i in range(len(copy_data)):
        ccs.append(str(copy_data[i]["name"]))
        cc_addr.append(str(copy_data[i]["address"]))
    if len(senders_addr) == 0:
        senders_addr.append("")
    if len(senders) == 0:
        senders.append("")
    
    if len(receivers) == 0:
        receivers.append("")
    
    if len(receivers_addr) == 0:
        receivers_addr.append("")
    if len(ccs) == 0:
        ccs.append("")
    if len(cc_addr) == 0:
        cc_addr.append("")

    if not text:
        return

    # 建立唯一暫存目錄
    temp_dir = tempfile.mkdtemp()
    output_filename = os.path.join(temp_dir, generate_random_string(4) + "_output.pdf")

    # 產生 PDF
    core.generate_text_and_letter(senders, senders_addr,
                                  receivers, receivers_addr,
                                  ccs, cc_addr,
                                  text)
    core.merge_text_and_letter(output_filename)
    core.clean_temp_files()
    print('Done. Filename: ', output_filename)
    
    def file_iterator(file_path):
        with open(file_path, "rb") as f:
            yield from f
        # 傳送完畢後刪除檔案與資料夾
        try:
            os.remove(file_path)
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"已刪除檔案與資料夾: {file_path}, {temp_dir}")
        except Exception as e:
            print(f"刪除檔案時發生錯誤: {str(e)}")

    return StreamingResponse(
        file_iterator(output_filename),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=letter.pdf"}
    )


# 這個函數已不再使用，但先保留在這裡
def delete_file_after_delay(file_path, delay_seconds):
    try:
        # 等待指定秒數
        time.sleep(delay_seconds)
        
        # 刪除指定檔案
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"已刪除檔案: {file_path}")
        else:
            print(f"檔案不存在: {file_path}")
    except Exception as e:
        print(f"刪除檔案時發生錯誤: {str(e)}")

def generate_random_string(length):
    characters = string.ascii_letters + string.digits  # 包含字母和数字的字符集
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string
def main():
    # 啟動主應用程式
    uvicorn.run("server:app",
                host="0.0.0.0",
                port=8080)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        raise e
