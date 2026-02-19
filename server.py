import uvicorn, os, json, time, threading, hashlib, urllib.parse
import tempfile
import shutil
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import random
import string
import pymysql
from lal_modules import core


app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


def load_env_file(path: str):
    if not path or not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


load_env_file(os.getenv("ECPAY_SECRETS_FILE", "/home/kyjita/.openclaw/workspace/.keys/ecpay_secrets"))


def db_conn():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "10.140.0.10"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "legal_attest_app"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "legal_attest"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
        read_timeout=5,
        write_timeout=5,
        autocommit=True,
    )


def ensure_payment_table():
    sql = """
    CREATE TABLE IF NOT EXISTS donation_payments (
      id BIGINT PRIMARY KEY AUTO_INCREMENT,
      merchant_trade_no VARCHAR(32) NOT NULL UNIQUE,
      trade_no VARCHAR(64) NULL,
      amount INT NOT NULL,
      status VARCHAR(32) NOT NULL DEFAULT 'INIT',
      rtn_code VARCHAR(16) NULL,
      rtn_msg VARCHAR(255) NULL,
      payer_email VARCHAR(255) NULL,
      raw_callback LONGTEXT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)


def ecpay_encode(raw: str) -> str:
    s = urllib.parse.quote_plus(raw, safe='-_.!*()').lower()
    return (
        s.replace('%2d', '-')
         .replace('%5f', '_')
         .replace('%2e', '.')
         .replace('%21', '!')
         .replace('%2a', '*')
         .replace('%28', '(')
         .replace('%29', ')')
    )


def ecpay_check_mac(params: dict, hash_key: str, hash_iv: str) -> str:
    items = sorted((k, v) for k, v in params.items() if k != "CheckMacValue" and v is not None)
    query = "&".join([f"{k}={v}" for k, v in items])
    raw = f"HashKey={hash_key}&{query}&HashIV={hash_iv}"
    encoded = ecpay_encode(raw)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest().upper()


def gen_trade_no() -> str:
    return "DN" + datetime.now().strftime("%y%m%d%H%M%S") + ''.join(random.choice(string.digits) for _ in range(4))


@app.on_event("startup")
def startup_event():
    try:
        ensure_payment_table()
    except Exception as e:
        print(f"[WARN] ensure_payment_table failed: {e}")


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


@app.get("/donate")
async def donate(request: Request):
    merchant_id = os.getenv("ECPAY_MERCHANT_ID", "")
    hash_key = os.getenv("ECPAY_HASH_KEY", "")
    hash_iv = os.getenv("ECPAY_HASH_IV", "")
    if not merchant_id or not hash_key or not hash_iv:
        return HTMLResponse("ECPay 設定缺失", status_code=500)

    amount = int(os.getenv("DONATION_AMOUNT", "50"))
    trade_no = gen_trade_no()
    now_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    base_url = str(request.base_url).rstrip("/")
    return_url = os.getenv("ECPAY_NOTIFY_URL", f"{base_url}/ecpay/notify")
    order_result_url = os.getenv("ECPAY_ORDER_RESULT_URL", f"{base_url}/donate/result")

    choose_payment = os.getenv("ECPAY_CHOOSE_PAYMENT", "Credit")
    params = {
        "MerchantID": merchant_id,
        "MerchantTradeNo": trade_no,
        "MerchantTradeDate": now_str,
        "PaymentType": "aio",
        "TotalAmount": str(amount),
        "TradeDesc": "Donation",
        "ItemName": f"網站贊助NT${amount} x 1",
        "ReturnURL": return_url,
        "OrderResultURL": order_result_url,
        "ChoosePayment": choose_payment,
        "EncryptType": "1",
    }
    params["CheckMacValue"] = ecpay_check_mac(params, hash_key, hash_iv)

    try:
        with db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO donation_payments (merchant_trade_no, amount, status) VALUES (%s,%s,'INIT')",
                    (trade_no, amount),
                )
    except Exception as e:
        return HTMLResponse(f"建立訂單失敗: {e}", status_code=500)

    ecpay_env = os.getenv("ECPAY_ENV", "production").lower()
    action = "https://payment.ecpay.com.tw/Cashier/AioCheckOut/V5" if ecpay_env == "production" else "https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5"
    inputs = "\n".join([f'<input type="hidden" name="{k}" value="{v}">' for k, v in params.items()])
    html = f"""
    <html><body>
    <p>正在導向綠界付款頁，請稍候...</p>
    <form id='ecpay' method='post' action='{action}'>
      {inputs}
    </form>
    <script>document.getElementById('ecpay').submit();</script>
    </body></html>
    """
    return HTMLResponse(html)


@app.post("/ecpay/notify")
async def ecpay_notify(request: Request):
    form = await request.form()
    data = {k: str(v) for k, v in form.items()}

    merchant_id = os.getenv("ECPAY_MERCHANT_ID", "")
    hash_key = os.getenv("ECPAY_HASH_KEY", "")
    hash_iv = os.getenv("ECPAY_HASH_IV", "")

    if data.get("MerchantID") != merchant_id:
        return PlainTextResponse("0|MerchantID mismatch", status_code=400)

    recv_mac = data.get("CheckMacValue", "")
    calc_mac = ecpay_check_mac(data, hash_key, hash_iv)
    if recv_mac != calc_mac:
        return PlainTextResponse("0|CheckMacValue error", status_code=400)

    mtn = data.get("MerchantTradeNo", "")
    status = "PAID" if data.get("RtnCode") == "1" else "FAILED"

    try:
        with db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE donation_payments
                    SET trade_no=%s, status=%s, rtn_code=%s, rtn_msg=%s, payer_email=%s, raw_callback=%s
                    WHERE merchant_trade_no=%s
                    """,
                    (
                        data.get("TradeNo"),
                        status,
                        data.get("RtnCode"),
                        data.get("RtnMsg"),
                        data.get("PaymentTypeChargeFee", ""),
                        json.dumps(data, ensure_ascii=False),
                        mtn,
                    ),
                )
    except Exception as e:
        return PlainTextResponse(f"0|DB error: {e}", status_code=500)

    return PlainTextResponse("1|OK")


@app.api_route("/donate/result", methods=["GET", "POST"])
async def donate_result(request: Request):
    data = {}
    if request.method == "POST":
        form = await request.form()
        data = {k: str(v) for k, v in form.items()}
    else:
        data = {k: str(v) for k, v in request.query_params.items()}

    code = data.get("RtnCode")
    msg = "付款成功，感謝贊助！" if code == "1" else f"付款未完成：{data.get('RtnMsg', '可稍後查詢付款紀錄')}"
    return HTMLResponse(f"<html><body><h3>{msg}</h3><p><a href='/'>回首頁</a></p></body></html>")


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
