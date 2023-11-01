import uvicorn, os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse , FileResponse
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


@app.post("/generate", response_class=FileResponse)
async def generate(request: Request):
    """
    產生檔案
    """
    json_request = await request.json()
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
        senders.append(from_data[i]["name"])
        senders_addr.append(from_data[i]["address"])
    for i in range(len(to_data)):
        receivers.append(to_data[i]["name"])
        receivers_addr.append(to_data[i]["address"])
    for i in range(len(copy_data)):
        ccs.append(copy_data[i]["name"])
        cc_addr.append(copy_data[i]["address"])
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

    output_filename = ""+generate_random_string(4) + "_output.pdf"

    core.generate_text_and_letter(senders, senders_addr,
                                  receivers, receivers_addr,
                                  ccs, cc_addr,
                                  text)
    core.merge_text_and_letter(output_filename)
    core.clean_temp_files()
    response = FileResponse(output_filename, headers={"Content-Disposition": "attachment"})
    print('Done. Filename: ', output_filename)

    return response


def generate_random_string(length):
    characters = string.ascii_letters + string.digits  # 包含字母和数字的字符集
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string
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
