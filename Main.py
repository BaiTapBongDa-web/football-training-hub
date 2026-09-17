from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from google import genai
import os

# ========================================
# 1. ĐỌC GEMINI API KEY
# ========================================

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError(
        "❌ Không tìm thấy GEMINI_API_KEY trong file .env"
    )

client = genai.Client(api_key=API_KEY)


# ========================================
# 2. KHỞI TẠO FLASK
# ========================================

app = Flask(__name__)


# ========================================
# 3. CẤU HÌNH FOOTBALL AI COACH
# ========================================

SYSTEM_PROMPT = """
Bạn là Football AI Coach — trợ lý huấn luyện bóng đá
của một hệ thống giáo trình huấn luyện bóng đá.

Nhiệm vụ của bạn:

- Luôn trả lời bằng tiếng Việt.
- Giải thích rõ ràng, dễ hiểu.
- Hỗ trợ huấn luyện viên xây dựng buổi tập.
- Gợi ý bài tập kỹ thuật, chiến thuật và thể lực.
- Hỗ trợ xây dựng giáo án theo số cầu thủ và thời lượng.
- Có thể phân tích cách tổ chức một bài tập bóng đá.
- Khi tạo giáo án, hãy chia thời gian thành các phần hợp lý.
- Ưu tiên câu trả lời thực tế, dễ áp dụng trên sân.
- Nếu thông tin chưa đủ, hãy hỏi thêm thay vì tự bịa.
- Không tự nhận là một HLV chuyên nghiệp ngoài đời.

Phong cách:

- Ngắn gọn.
- Thực tế.
- Dễ hiểu.
- Giống một trợ lý HLV bóng đá.
- Có thể sử dụng emoji bóng đá vừa phải.
"""


# ========================================
# 4. MỞ WEBSITE
# ========================================

@app.route("/")
def home():
    return send_from_directory(
        os.path.dirname(os.path.abspath(__file__)),
        "TrangWebLenYTuongBaiTapBongDaCT (2).html"
    )


# ========================================
# 5. API CHAT GEMINI
# ========================================

@app.route("/api/chat", methods=["POST"])
def chat():

    try:
        # Nhận dữ liệu từ website
        data = request.get_json(silent=True) or {}

        message = str(
            data.get("message", "")
        ).strip()

        print()
        print("========================================")
        print("📩 TIN NHẮN TỪ WEBSITE:")
        print(message)
        print("========================================")

        # Kiểm tra tin nhắn
        if not message:
            return jsonify({
                "reply": "Bạn chưa nhập câu hỏi."
            }), 200

        # ========================================
        # TẠO PROMPT
        # ========================================

        prompt = f"""
{SYSTEM_PROMPT}

Câu hỏi của người dùng:

{message}
"""

        # ========================================
        # GỌI GEMINI 3.6 FLASH
        # ========================================

        print("🤖 Đang gửi câu hỏi tới Gemini 3.6 Flash...")

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )

        # ========================================
        # NHẬN CÂU TRẢ LỜI
        # ========================================

        reply_text = response.text

        if not reply_text:
            reply_text = "Gemini không trả về nội dung."

        print("✅ Gemini 3.6 Flash đã trả lời.")
        print("========================================")
        print()

        return jsonify({
            "reply": reply_text
        }), 200


    # ========================================
    # 6. XỬ LÝ LỖI
    # ========================================

    except Exception as e:

        import traceback

        print()
        print("========================================")
        print("❌ GEMINI ERROR")
        print("========================================")
        print("Lỗi:", str(e))
        traceback.print_exc()
        print("========================================")
        print()

        return jsonify({
            "error": "Không thể kết nối Gemini.",
            "detail": str(e)
        }), 500


# ========================================
# 7. CHẠY SERVER
# ========================================

if __name__ == "__main__":

    print()
    print("========================================")
    print("⚽ FOOTBALL AI COACH")
    print("========================================")
    print("✅ Gemini API Key: Đã đọc")
    print("🤖 Model: gemini-3.6-flash")
    print("🌐 Website: http://127.0.0.1:5000")
    print("========================================")
    print()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )

