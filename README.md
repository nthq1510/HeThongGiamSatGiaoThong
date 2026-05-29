# Hệ thống Giám sát và Phát hiện Vi phạm Giao thông Thời gian thực (Traffic AI Guard)

> **Đồ án tốt nghiệp ngành Khoa học Máy tính**
> 
> Hệ thống ứng dụng Trí tuệ nhân tạo (AI) và Thị giác máy tính (Computer Vision) để tự động hóa giám sát, phát hiện các hành vi vi phạm luật giao thông từ camera đường phố thời gian thực.

---

## 📸 Giao diện Dashboard Quản trị

Hệ thống được trang bị giao diện **Dark Mode Glassmorphism** hiện đại hiển thị luồng video AI, cảnh báo thời gian thực và lịch sử vi phạm:

* Màn hình chính hiển thị video live stream đã được vẽ Bounding Box nhận diện, làn đường đa giác, vạch dừng ảo.
* Cột cảnh báo nhấp nháy đỏ kèm âm thanh còi bíp tức thì khi phát hiện vi phạm.
* Bảng tra cứu lịch sử vi phạm chi tiết cho phép xem ảnh chụp bằng chứng, thông tin biển số xe trích xuất qua OCR và duyệt xử phạt.

---

## 🛠️ Kiến trúc Hệ thống (3-Tier Architecture)

Dự án được xây dựng theo mô hình Microservices tách biệt 3 thành phần chính:

```
[Camera/Video đầu vào]
       │
       ▼
 1. Động cơ AI (bo_xu_ly_ai) ────(HTTP POST / WebSockets)────► 2. Backend API (backend_api)
       │                                                              │
       │                                                          (SQLite)
       ▼                                                              │
[Vẽ Bounding Box & Phân tích lỗi]                                      ▼
       │                                                 3. Dashboard UI (giao_dien_web)
       └─────────────────────────(Luồng Live Video)───────────────────┘
```

1. **AI Engine (`bo_xu_ly_ai/`)**:
   * **YOLOv8 (Nano)**: Nhận diện nhanh phương tiện giao thông (Ô tô, Xe máy, Xe tải, Xe buýt).
   * **ByteTrack**: Theo dõi (tracking) hành trình xe qua mã ID vật lý duy nhất.
   * **EasyOCR**: Trích xuất biển số xe từ vùng ảnh cắt tự động khi có vi phạm.
   * **Logic Toán học**: Tự động phát hiện 5 lỗi vi phạm phổ biến.

2. **Backend API (`backend_api/`)**:
   * **FastAPI**: Đóng vai trò máy chủ trung chuyển nhẹ, xử lý kết nối bất đồng bộ hiệu năng cao.
   * **WebSockets**: Phát sóng dữ liệu cảnh báo và luồng video trực tiếp từ AI Engine lên Dashboard.
   * **SQLite & SQLAlchemy**: Lưu trữ thông tin hồ sơ vi phạm lâu dài.

3. **Frontend Dashboard (`giao_dien_web/`)**:
   * **ReactJS & Vite**: Giao diện người dùng mượt mà, phản hồi nhanh.
   * **Vanilla CSS**: Thiết kế hiệu ứng kính (Glassmorphic) cao cấp và tương thích responsive.

---

## 🚦 5 Lỗi Vi phạm Được Hỗ trợ

* **Đi ngược chiều**: So sánh hướng di chuyển tọa độ Y của xe qua các khung hình, báo lỗi khi đi ngược chiều quy định của làn đường.
* **Đi sai làn đường**: Kiểm tra xem trọng tâm phương tiện có nằm trong đa giác (polygon) làn đường không phù hợp hay không (ví dụ: ô tô chạy vào làn xe máy).
* **Vượt đèn đỏ**: Thiết lập vạch dừng ảo; nếu trạng thái đèn ảo chuyển sang đỏ và xe đè qua vạch dừng sẽ kích hoạt vi phạm.
* **Chạy quá tốc độ**: Đo thời gian xe di chuyển qua hai vạch ảo cách nhau 15 mét thực tế, tính toán vận tốc tức thời và so sánh với giới hạn tốc độ.
* **Không đội mũ bảo hiểm**: Crop vùng đầu người điều khiển xe máy và phát hiện sự hiện diện của mũ bảo hiểm (Giả lập heuristic thông minh cho bản demo).

---

## 🚀 Hướng dẫn Cài đặt & Vận hành

### Yêu cầu Hệ thống
* Hệ điều hành: macOS (đã tối ưu hóa GPU Apple Silicon MPS) hoặc Windows/Linux.
* Python 3.9+ và NodeJS 18+.

### Cách 1: Khởi chạy nhanh bằng 1 câu lệnh (Khuyên dùng)
Mở Terminal tại thư mục gốc của dự án và chạy lệnh:
```bash
python3 chay_nhanh.py
```
*Hệ thống sẽ tự động kích hoạt môi trường ảo `venv`, chạy song song FastAPI Backend (cổng 8000), Frontend Vite (cổng 5173), khởi động AI Engine xử lý video giao thông mẫu và in thông báo sẵn sàng.*

Sau đó, truy cập trình duyệt tại địa chỉ: **[http://localhost:5173](http://localhost:5173)**.

### Cách 2: Khởi chạy thủ công từng thành phần
Mở 3 cửa sổ/tab Terminal riêng biệt tại thư mục gốc dự án:

1. **Khởi chạy Backend API**:
   ```bash
   source venv/bin/activate
   cd backend_api
   uvicorn chinh:app --reload --port 8000
   ```
2. **Khởi chạy Frontend Dashboard**:
   ```bash
   cd giao_dien_web
   npm run dev
   ```
3. **Khởi chạy AI Engine**:
   ```bash
   source venv/bin/activate
   cd bo_xu_ly_ai
   python3 luong_chinh.py --video ../giao_thong_mau.mp4
   ```

Để tắt toàn bộ hệ thống đang chạy nhanh, nhấn tổ hợp phím **`Ctrl + C`** ở cửa sổ terminal chính.

---

## ⚙️ Hướng dẫn Cá nhân hóa Đồ án

Để thay đổi thông tin phù hợp với video giám sát mới của bạn, hãy chỉnh sửa các cấu hình trong:
* **Thay thế video mẫu**: Đổi tên video thực tế của bạn thành `giao_thong_mau.mp4` đặt ở thư mục gốc, hoặc chạy dòng lệnh AI chỉ định video khác:
  ```bash
  python3 luong_chinh.py --video /duong_dan/video_cua_ban.mp4
  ```
* **Căn chỉnh làn đường & Vạch ảo**: Mở tệp [bo_xu_ly_ai/cau_hinh.py](file:///Users/quangnguyentamhuu/Desktop/HeThongGiamSatGiaoThong/bo_xu_ly_ai/cau_hinh.py) để cập nhật tọa độ đa giác làn đường (`LAN_DUONG`), vạch dừng đèn đỏ (`VACH_DUNG_DO`) và giới hạn tốc độ tối đa (`gioi_han_toc_do`).

---

## 📄 Tài liệu Phụ lục Đồ án
Tài liệu hướng dẫn kỹ thuật chi tiết từng hàm, thuật toán toán học đằng sau và các câu hỏi đáp bảo vệ đồ án tốt nghiệp được lưu trữ tại:
* **[huong_dan_van_hanh_chi_tiet.pdf](file:///Users/quangnguyentamhuu/Desktop/HeThongGiamSatGiaoThong/huong_dan_van_hanh_chi_tiet.pdf)**
