REPORT_PROMPT = """\
Bạn là chuyên gia mạng lõi viễn thông (Core Network Engineer). \
Hãy viết báo cáo công nghệ mới cho {week_label} từ các bài viết được thu thập dưới đây.

DỮ LIỆU ĐẦU VÀO:
{items}

YÊU CẦU ĐỊNH DẠNG:
1. Dòng đầu: tiêu đề "📡 BÁO CÁO CÔNG NGHỆ MẠNG LÕI — {week_label}"
2. Phần TỔNG QUAN (tiếng Việt, 2-3 câu)
3. Các mục theo domain (chỉ ghi mục nếu có nội dung):
   - ## 5G Core (5GC)
   - ## IMS / VoNR
   - ## Autonomous Networks
   - ## EPC / 4G Evolution
   Mỗi bài: tiêu đề tiếng Anh, nguồn, tóm tắt kỹ thuật 3-5 câu tiếng Anh
4. Mục "## 🔗 Tài liệu đáng chú ý" — danh sách links

Viết báo cáo:"""

SUMMARIZE_PROMPT = """\
Bạn là chuyên gia mạng lõi viễn thông. \
Hãy tóm tắt tài liệu kỹ thuật sau phục vụ nghiên cứu công nghệ mạng lõi 4G/5G.

TÊN FILE: {filename}
NỘI DUNG:
{content}

YÊU CẦU:
1. Tổng quan (tiếng Việt, 3-5 câu)
2. Điểm kỹ thuật chính (tiếng Anh, bullet points)
3. Mức độ liên quan: 5GC / IMS / EPC / Autonomous / Không liên quan trực tiếp

Tóm tắt:"""
