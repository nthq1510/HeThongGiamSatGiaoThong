import cv2
import numpy as np

# Cấu hình API Backend
BACKEND_API_URL = "http://localhost:8000/api/vi-pham"

# Đường dẫn các mô hình YOLO
# yolov8n.pt là mô hình nano phát hiện phương tiện (car, motorcycle, bus, truck)
DUONG_DAN_MO_HINH_XE = "cac_mo_hinh/yolov8n.pt"
# yolov8n_helmet.pt hoặc mô hình tùy chỉnh phát hiện người đi xe máy có/không đội mũ bảo hiểm
# Ở bước phát triển ban đầu, chúng ta sẽ giả lập hoặc dùng bộ lọc YOLOv8 class 'person' + 'motorcycle'
DUONG_DAN_MO_HINH_MU_BAO_HIEM = "cac_mo_hinh/yolov8n.pt"  # Có thể dùng chung hoặc cập nhật sau

# Kích thước chuẩn hóa của Video Frame để tính tọa độ
KICH_THUOC_CHUAN = (1280, 720)

# 1. Cấu hình Làn đường (Wrong Lane Detection)
# Mỗi làn đường được xác định bằng một đa giác (Polygon) các điểm (x, y)
# và danh sách các phương tiện được phép đi vào làn đó.
LAN_DUONG = {
    "lan_o_to": {
        "ten": "Làn xe ô tô",
        "da_giac": np.array([[100, 720], [500, 300], [650, 300], [550, 720]], dtype=np.int32),
        "phuong_tien_cho_phep": [2, 5, 7]  # YOLO COCO classes: 2 (car), 5 (bus), 7 (truck)
    },
    "lan_xe_may": {
        "ten": "Làn xe máy",
        "da_giac": np.array([[550, 720], [650, 300], [750, 300], [900, 720]], dtype=np.int32),
        "phuong_tien_cho_phep": [3]  # YOLO COCO classes: 3 (motorcycle)
    }
}

# 2. Cấu hình Đi ngược chiều (Wrong-way Detection)
# Vector hướng di chuyển hợp lệ (từ xa lại gần hoặc ngược lại)
# Ta có thể định nghĩa hướng đi hợp lệ dưới dạng góc (Angle) hoặc tọa độ Y tăng dần/giảm dần
HUONG_DI_HOP_LE = {
    "huong": "di_xuong",  # di_xuong (Y tăng dần) hoặc di_len (Y giảm dần)
    "sai_so_goc": 45      # Độ lệch góc tối đa cho phép (độ)
}

# 3. Cấu hình Vạch dừng & Đèn đỏ (Red Light Violation)
VACH_DUNG_DO = {
    # Tọa độ hai điểm tạo thành đường thẳng vạch dừng: [(x1, y1), (x2, y2)]
    "duong_vach": [(200, 500), (1000, 500)],
    # Trạng thái đèn giao thông mặc định hoặc giả lập (RED, GREEN, YELLOW)
    "den_giao_thong_mac_dinh": "GREEN"
}

# 4. Cấu hình Đo tốc độ (Over-speeding Detection)
VUNG_DO_TOC_DO = {
    # Khoảng cách thực tế giữa Vạch Bắt Đầu và Vạch Kết Thúc (mét)
    "khoang_cach_met": 15.0,
    # Giới hạn tốc độ cho phép (km/h)
    "gioi_han_toc_do": 50.0,
    # Vạch Bắt đầu (Start Line): [(x1, y1), (x2, y2)]
    "vach_bat_dau": [(300, 400), (900, 400)],
    # Vạch Kết thúc (End Line): [(x1, y1), (x2, y2)]
    "vach_ket_thuc": [(200, 600), (1100, 600)]
}

# Tiện ích vẽ đa giác lên Frame để giám sát
def ve_vung_giam_sat(frame):
    # Vẽ các làn đường
    for ten_lan, thong_tin in LAN_DUONG.items():
        mau = (0, 255, 0) if "o_to" in ten_lan else (255, 255, 0)
        cv2.polylines(frame, [thong_tin["da_giac"]], True, mau, 2)
        cv2.putText(frame, thong_tin["ten"], tuple(thong_tin["da_giac"][0]), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, mau, 2)
        
    # Vẽ vạch dừng đèn đỏ
    cv2.line(frame, VACH_DUNG_DO["duong_vach"][0], VACH_DUNG_DO["duong_vach"][1], (0, 0, 255), 3)
    cv2.putText(frame, "VACH DUNG", VACH_DUNG_DO["duong_vach"][0], 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    
    # Vẽ vạch đo tốc độ
    cv2.line(frame, VUNG_DO_TOC_DO["vach_bat_dau"][0], VUNG_DO_TOC_DO["vach_bat_dau"][1], (255, 0, 255), 2)
    cv2.line(frame, VUNG_DO_TOC_DO["vach_ket_thuc"][0], VUNG_DO_TOC_DO["vach_ket_thuc"][1], (255, 0, 255), 2)
    cv2.putText(frame, "START SPEED ZONE", VUNG_DO_TOC_DO["vach_bat_dau"][0], 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
    cv2.putText(frame, "END SPEED ZONE", VUNG_DO_TOC_DO["vach_ket_thuc"][0], 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
    return frame
