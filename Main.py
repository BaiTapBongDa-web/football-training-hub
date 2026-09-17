from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from google import genai
from google.genai import types
import os
import threading
import traceback


# =========================================================
# 1. LOAD ENVIRONMENT
# =========================================================

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError(
        "Không tìm thấy GEMINI_API_KEY trong file .env"
    )


# =========================================================
# 2. GEMINI CLIENT
# =========================================================

retry_options = types.HttpRetryOptions(
    attempts=4,
    initial_delay=1,
    max_delay=20,
    exp_base=2,
    jitter=1,
    http_status_codes=[
        408,
        429,
        500,
        502,
        503,
        504,
    ],
)

http_options = types.HttpOptions(
    retry_options=retry_options,
    timeout=90000,
)

client = genai.Client(
    api_key=API_KEY,
    http_options=http_options,
)


# =========================================================
# 3. FLASK APP
# =========================================================

app = Flask(__name__)

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

HTML_FILE = "index.html"


# =========================================================
# 4. CHỈ CHO 1 REQUEST GEMINI CHẠY CÙNG LÚC
# =========================================================

gemini_lock = threading.Lock()


# =========================================================
# 5. SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
Bạn là Football AI Coach — trợ lý huấn luyện bóng đá
của Football Training Hub.

Bạn hỗ trợ:
- kỹ thuật bóng đá
- chuyền và nhận bóng
- kiểm soát bóng
- rê bóng
- dứt điểm
- phòng thủ
- thủ môn
- thể lực
- chiến thuật
- pressing
- xây dựng giáo án tập luyện

Bạn phải:
- trả lời bằng tiếng Việt
- dễ hiểu
- thực tế
- ngắn gọn nhưng đủ ý
- ưu tiên hướng dẫn có thể áp dụng trên sân
- hỏi lại khi thiếu thông tin quan trọng

Người dùng có thể hỏi tự nhiên như:
hello
hi
xin chào
bạn làm được gì?
hoặc bất kỳ câu hỏi nào liên quan đến bóng đá.
""".strip()


# =========================================================
# 6. TRANG CHỦ
# =========================================================

@app.route("/")
def home():

    html_path = os.path.join(
        BASE_DIR,
        HTML_FILE
    )

    print("📁 HTML:", html_path)
    print(
        "📁 Tồn tại:",
        os.path.exists(html_path)
    )

    if not os.path.exists(html_path):
        return """
        <h1>❌ Không tìm thấy index.html</h1>
        <p>
            Hãy kiểm tra GitHub xem
            index.html có nằm cùng thư mục với Main.py không.
        </p>
        """, 404

    return send_from_directory(
        BASE_DIR,
        HTML_FILE
    )


# =========================================================
# 7. HEALTH CHECK
# =========================================================

@app.route("/health")
def health():

    return jsonify({
        "status": "ok",
        "service": "Football Training Hub",
        "gemini_model": "gemini-3.6-flash"
    }), 200


# =========================================================
# 8. GEMINI CHAT
# =========================================================

@app.route("/api/chat", methods=["POST"])
def chat():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        message = str(
            data.get("message", "")
        ).strip()

        print("\n" + "=" * 60)
        print("👤 USER:", message)

        # -------------------------------------------------
        # Empty message
        # -------------------------------------------------

        if not message:

            return jsonify({
                "reply": "Bạn chưa nhập câu hỏi."
            }), 200


        # -------------------------------------------------
        # Giới hạn độ dài input
        # tránh request quá lớn
        # -------------------------------------------------

        if len(message) > 2000:

            return jsonify({
                "error": "Câu hỏi quá dài.",
                "detail": "Vui lòng rút gọn câu hỏi xuống dưới 2000 ký tự."
            }), 400


        # -------------------------------------------------
        # PROMPT
        # -------------------------------------------------

        prompt = f"""
{SYSTEM_PROMPT}

Câu hỏi của người dùng:

{message}
""".strip()


        # -------------------------------------------------
        # CHỈ 1 REQUEST GEMINI TẠI 1 THỜI ĐIỂM
        # -------------------------------------------------

        acquired = gemini_lock.acquire(
            timeout=5
        )

        if not acquired:

            return jsonify({
                "error": "Hệ thống đang xử lý một câu hỏi khác.",
                "detail": "Hãy đợi vài giây rồi thử lại."
            }), 429


        try:

            print(
                "🤖 Gọi Gemini 3.6 Flash..."
            )

            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt
            )

            reply = getattr(
                response,
                "text",
                None
            )

            if not reply:

                print(
                    "⚠️ Gemini không trả text."
                )

                return jsonify({
                    "error": "Gemini không trả về nội dung.",
                    "detail": "Vui lòng thử lại."
                }), 503


            print(
                "✅ Gemini trả lời thành công."
            )

            return jsonify({
                "reply": reply
            }), 200


        finally:

            gemini_lock.release()


    except Exception as e:

        error_text = str(e)

        print("\n❌ GEMINI ERROR")
        print(error_text)

        traceback.print_exc()


        # =================================================
        # 429
        # =================================================

        if (
            "429" in error_text
            or "RESOURCE_EXHAUSTED" in error_text
            or "quota_exceeded" in error_text
            or "too_many_requests" in error_text
        ):

            return jsonify({
                "error": "Gemini đang giới hạn số lượt gọi.",
                "detail": (
                    "Có thể bạn đã vượt giới hạn request "
                    "hoặc quota. Hãy chờ một lúc rồi thử lại."
                )
            }), 429


        # =================================================
        # 503
        # =================================================

        if (
            "503" in error_text
            or "UNAVAILABLE" in error_text
            or "service_unavailable" in error_text
        ):

            return jsonify({
                "error": "Gemini đang tạm thời quá tải.",
                "detail": (
                    "Hệ thống đã tự retry. "
                    "Hãy thử lại sau một lúc."
                )
            }), 503


        # =================================================
        # 504
        # =================================================

        if (
            "504" in error_text
            or "DEADLINE_EXCEEDED" in error_text
        ):

            return jsonify({
                "error": "Gemini phản hồi quá lâu.",
                "detail": (
                    "Hãy thử gửi câu hỏi ngắn hơn."
                )
            }), 504


        # =================================================
        # LỖI KHÁC
        # =================================================

        return jsonify({
            "error": "Gemini gặp lỗi.",
            "detail": error_text
        }), 500


# =========================================================
# 9. RUN SERVER
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    print("")
    print("=" * 60)
    print("⚽ FOOTBALL TRAINING HUB")
    print("🤖 MODEL: gemini-3.6-flash")
    print("🌐 PORT:", port)
    print("🔒 GEMINI LOCK: ENABLED")
    print("🔁 SDK RETRY: ENABLED")
    print("=" * 60)

    app.run(
        host="0.0.0.0",
        port=port
    )
