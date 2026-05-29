import cv2
import numpy as np
import time
import requests
import json
import base64
import asyncio
import websockets
from datetime import datetime
import os

from cau_hinh import (
    BACKEND_API_URL,
    DUONG_DAN_MO_HINH_XE,
    DUONG_DAN_MO_HINH_MU_BAO_HIEM,
    LAN_DUONG,
    HUONG_DI_HOP_LE,
    VACH_DUNG_DO,
    VUNG_DO_TOC_DO,
    ve_vung_giam_sat
)
from bo_theo_doi import BoTheoDoi
from bo_nhan_dien import BoNhanDienGiaoThong
from nhan_dien_bien_so import BoNhanDienBienSo

# Thiết lập thư mục lưu trữ ảnh tạm thời trước khi upload
THU_MUC_TAM = "tam_uploads"
os.makedirs(THU_MUC_TAM, exist_ok=True)

class LuongXuLyGiaoThong:
    def __init__(self, nguon_video):
        self.nguon_video = nguon_video
        self.bo_nhan_dien = BoNhanDienGiaoThong(DUONG_DAN_MO_HINH_XE, DUONG_DAN_MO_HINH_MU_BAO_HIEM)
        self.bo_theo_doi = BoTheoDoi()
        self.bo_ocr = BoNhanDienBienSo()
        
        # Lưu các vi phạm đã báo cáo để tránh trùng lặp: {(track_id, loai_vi_pham): True}
        self.vi_pham_da_bao_cao = set()
        
        # Quản lý thời gian đo tốc độ: {track_id: thoi_gian_qua_vach_bat_dau}
        self.thoi_gian_toc_do = {}
        
        # Biến trạng thái đèn giao thông mô phỏng (GREEN, YELLOW, RED)
        self.den_giao_thong = "GREEN"
        self.thoi_gian_den = time.time()
        self.chu_ky_den = {"GREEN": 15, "YELLOW": 3, "RED": 15}

    def cap_nhat_den_giao_thong(self):
        """Mô phỏng chu kỳ đèn giao thông tự động."""
        thoi_gian_qua = time.time() - self.thoi_gian_den
        if thoi_gian_qua > self.chu_ky_den[self.den_giao_thong]:
            if self.den_giao_thong == "GREEN":
                self.den_giao_thong = "YELLOW"
            elif self.den_giao_thong == "YELLOW":
                self.den_giao_thong = "RED"
            else:
                self.den_giao_thong = "GREEN"
            self.thoi_gian_den = time.time()

    def kiem_tra_di_diem_trong_da_giac(self, diem, da_giac):
        """Kiểm tra một điểm (x, y) có nằm trong đa giác hay không."""
        return cv2.pointPolygonTest(da_giac, (diem[0], diem[1]), False) >= 0

    def kiem_tra_cat_duong(self, p1, p2, vach):
        """Kiểm tra đường di chuyển từ p1 đến p2 có cắt qua vạch hay không."""
        # vach dạng [(x1, y1), (x2, y2)]
        v1, v2 = vach
        
        # Thuật toán tính giao điểm của 2 đoạn thẳng
        def ccw(A, B, C):
            return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])
            
        return ccw(p1, v1, v2) != ccw(p2, v1, v2) and ccw(p1, p2, v1) != ccw(p1, p2, v2)

    def gui_vi_pham_api(self, loai_vi_pham, loai_phuong_tien, bien_so, toc_do, anh_xe, anh_bien=None):
        """Gửi sự kiện vi phạm về FastAPI Server bằng HTTP POST."""
        try:
            # Lưu ảnh tạm thời
            path_anh_xe = os.path.join(THU_MUC_TAM, f"xe_{int(time.time())}.jpg")
            cv2.imwrite(path_anh_xe, anh_xe)
            
            files = {
                "anh_bang_chung": ("anh_xe.jpg", open(path_anh_xe, "rb"), "image/jpeg")
            }
            
            path_anh_bien = None
            if anh_bien is not None:
                path_anh_bien = os.path.join(THU_MUC_TAM, f"bien_{int(time.time())}.jpg")
                cv2.imwrite(path_anh_bien, anh_bien)
                files["anh_bien_so"] = ("anh_bien.jpg", open(path_anh_bien, "rb"), "image/jpeg")
                
            data = {
                "loai_vi_pham": loai_vi_pham,
                "loai_phuong_tien": loai_phuong_tien,
                "bien_so": bien_so,
                "toc_do_do_duoc": toc_do if toc_do else None
            }
            
            res = requests.post(BACKEND_API_URL, data=data, files=files, timeout=5)
            
            # Đóng file và xóa ảnh tạm
            for f in files.values():
                f[1].close()
            if os.path.exists(path_anh_xe):
                os.remove(path_anh_xe)
            if path_anh_bien and os.path.exists(path_anh_bien):
                os.remove(path_anh_bien)
                
            if res.status_code == 200:
                print(f"-> Đã ghi nhận vi phạm: {loai_vi_pham} - Xe: {loai_phuong_tien} - Biển số: {bien_so}")
            else:
                print(f"Lỗi gửi API: {res.text}")
        except Exception as e:
            print(f"Lỗi kết nối API Backend: {e}")

    def lay_bien_so_gia_lap(self, track_id):
        """Tạo biển số giả lập nhất quán theo ID nếu OCR không đọc được."""
        # Định dạng biển số VN: e.g., 29A1-12345
        tinh = [29, 30, 59, 43, 75, 37, 18][track_id % 7]
        chu = ["A", "B", "C", "D", "F", "K", "X"][track_id % 7]
        so_duoi = f"{track_id * 137 % 100000:05d}"
        return f"{tinh}{chu}1-{so_duoi[:3]}.{so_duoi[3:]}"

    async def chay_he_thong(self):
        # Mở kết nối WebSocket tới Backend
        url_ws = "ws://localhost:8000/ws/nhap-luong-ai"
        print(f"Đang kết nối tới Backend WebSocket tại {url_ws}...")
        
        cap = cv2.VideoCapture(self.nguon_video)
        if not cap.isOpened():
            print(f"Không thể mở nguồn video: {self.nguon_video}")
            return
            
        print("Đầu vào Video đã sẵn sàng. Bắt đầu luồng xử lý...")
        
        async with websockets.connect(url_ws) as websocket:
            print("Đã kết nối thành công WebSocket.")
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    # Nếu hết video, lặp lại video từ đầu (cho mục đích demo liên tục)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                    
                # Chuẩn hóa kích thước khung hình
                frame = cv2.resize(frame, (1280, 720))
                thoi_gian_hien_tai = time.time()
                
                # Cập nhật trạng thái đèn giao thông mô phỏng
                self.cap_nhat_den_giao_thong()
                
                # Chạy nhận dạng YOLOv8
                results = self.bo_nhan_dien.chay_nhan_dien(frame)
                
                # Trích xuất thông tin tracking
                doi_tuong_theo_doi = self.bo_theo_doi.trich_xuat_ket_qua_track(results)
                
                # Tạo một bản sao để vẽ thông tin lên màn hình
                frame_ve = frame.copy()
                frame_ve = ve_vung_giam_sat(frame_ve)
                
                # Vẽ đèn giao thông giả lập góc trên bên phải
                mau_den = (0, 255, 0) if self.den_giao_thong == "GREEN" else (0, 255, 255) if self.den_giao_thong == "YELLOW" else (0, 0, 255)
                cv2.circle(frame_ve, (1200, 50), 20, mau_den, -1)
                cv2.putText(frame_ve, f"LIGHT: {self.den_giao_thong}", (1100, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, mau_den, 2)
                
                for dt in doi_tuong_theo_doi:
                    track_id = dt["id"]
                    x1, y1, x2, y2 = dt["toa_do"]
                    lop_id = dt["lop"]
                    trong_tam = dt["trong_tam"]
                    cx, cy = trong_tam
                    
                    ten_lop_tieng_anh = self.bo_nhan_dien.mo_hinh_xe.names[lop_id]
                    
                    # Cập nhật lịch sử vị trí di chuyển
                    self.bo_theo_doi.cap_nhat_vi_tri(track_id, cx, cy, thoi_gian_hien_tai)
                    lich_su = self.bo_theo_doi.lay_lich_su(track_id)
                    
                    vi_pham_hien_tai = []
                    toc_do_tinh_duoc = None
                    
                    # 1. KIỂM TRA ĐI SAI LÀN ĐƯỜNG
                    di_dung_lan = True
                    for ten_lan, thong_tin_lan in LAN_DUONG.items():
                        # Nếu xe nằm trong đa giác làn này
                        in_lane = self.kiem_tra_di_diem_trong_da_giac(trong_tam, thong_tin_lan["da_giac"])
                        if in_lane:
                            if lop_id not in thong_tin_lan["phuong_tien_cho_phep"]:
                                di_dung_lan = False
                                
                    if not di_dung_lan:
                        vi_pham_hien_tai.append("Đi sai làn đường")

                    # 2. KIỂM TRA ĐI NGƯỢC CHIỀU
                    if len(lich_su) >= 10:
                        cy_cu = lich_su[0][1]
                        cy_moi = trong_tam[1]
                        # Hướng đi đúng là "di_xuong" (Y tăng dần)
                        # Nếu xe di chuyển ngược lại rõ rệt (Y giảm dần đáng kể)
                        if HUONG_DI_HOP_LE["huong"] == "di_xuong" and (cy_cu - cy_moi) > 40:
                            vi_pham_hien_tai.append("Đi ngược chiều")
                        elif HUONG_DI_HOP_LE["huong"] == "di_len" and (cy_moi - cy_cu) > 40:
                            vi_pham_hien_tai.append("Đi ngược chiều")

                    # 3. KIỂM TRA VƯỢT ĐÈN ĐỎ
                    if len(lich_su) >= 2 and self.den_giao_thong == "RED":
                        p_truoc = (lich_su[-2][0], lich_su[-2][1])
                        p_sau = trong_tam
                        if self.kiem_tra_cat_duong(p_truoc, p_sau, VACH_DUNG_DO["duong_vach"]):
                            vi_pham_hien_tai.append("Vượt đèn đỏ")

                    # 4. KIỂM TRA CHẠY QUÁ TỐC ĐỘ
                    # Đo từ lúc qua Vạch Bắt Đầu đến Vạch Kết Thúc
                    if len(lich_su) >= 2:
                        p_truoc = (lich_su[-2][0], lich_su[-2][1])
                        p_sau = trong_tam
                        
                        # Qua vạch bắt đầu
                        if self.kiem_tra_cat_duong(p_truoc, p_sau, VUNG_DO_TOC_DO["vach_bat_dau"]):
                            self.thoi_gian_toc_do[track_id] = thoi_gian_hien_tai
                            
                        # Qua vạch kết thúc
                        if self.kiem_tra_cat_duong(p_truoc, p_sau, VUNG_DO_TOC_DO["vach_ket_thuc"]):
                            if track_id in self.thoi_gian_toc_do:
                                t_dau = self.thoi_gian_toc_do[track_id]
                                duration = thoi_gian_hien_tai - t_dau
                                if duration > 0:
                                    # Vận tốc v = s / t * 3.6
                                    s = VUNG_DO_TOC_DO["khoang_cach_met"]
                                    toc_do_tinh_duoc = (s / duration) * 3.6
                                    # Lưu vết tốc độ vào dict vị trí cuối cùng
                                    dt["toc_do"] = toc_do_tinh_duoc
                                    
                                    if toc_do_tinh_duoc > VUNG_DO_TOC_DO["gioi_han_toc_do"]:
                                        vi_pham_hien_tai.append("Chạy quá tốc độ")

                    # 5. KIỂM TRA KHÔNG ĐỘI MŨ BẢO HIỂM (Chỉ kiểm tra xe máy - motorcycle: class 3)
                    if lop_id == 3:
                        doi_mu = self.bo_nhan_dien.kiem_tra_mu_bao_hiem(frame, x1, y1, x2, y2, track_id)
                        if not doi_mu:
                            vi_pham_hien_tai.append("Không đội mũ bảo hiểm")

                    # XỬ LÝ KHI PHÁT HIỆN CÓ VI PHẠM
                    for loi in vi_pham_hien_tai:
                        khoa_vp = (track_id, loi)
                        if khoa_vp not in self.vi_pham_da_bao_cao:
                            # Đánh dấu đã báo cáo để không bị lặp lại liên tục
                            self.vi_pham_da_bao_cao.add(khoa_vp)
                            
                            # Cắt vùng ảnh xe vi phạm
                            anh_xe_crop = frame[max(0, y1):min(720, y2), max(0, x1):min(1280, x2)]
                            
                            # Thử nhận diện biển số từ nửa dưới của vùng xe (nơi thường có biển số)
                            chieu_cao = y2 - y1
                            y_ocr_start = max(0, y1 + int(chieu_cao * 0.5))
                            anh_bien_crop = frame[y_ocr_start:min(720, y2), max(0, x1):min(1280, x2)]
                            
                            # Gọi module OCR
                            bien_so_ocr = self.bo_ocr.doc_bien_so(anh_bien_crop)
                            # Nếu OCR không đọc được chữ, dùng cơ chế giả lập biển số VN nhất quán theo ID
                            if bien_so_ocr == "Chưa xác định" or len(bien_so_ocr) < 4:
                                bien_so_ocr = self.lay_bien_so_gia_lap(track_id)
                                
                            # Gửi sự kiện vi phạm về Server FastAPI thông qua HTTP API
                            self.gui_vi_pham_api(
                                loai_vi_pham=loi,
                                loai_phuong_tien=ten_lop_tieng_anh,
                                bien_so=bien_so_ocr,
                                toc_do=toc_do_tinh_duoc,
                                anh_xe=anh_xe_crop,
                                anh_bien=anh_bien_crop if bien_so_ocr != "Chưa xác định" else None
                            )

                    # Vẽ khung hình hộp của xe
                    mau_khung = (0, 0, 255) if vi_pham_hien_tai else (0, 255, 0)
                    cv2.rectangle(frame_ve, (x1, y1), (x2, y2), mau_khung, 2)
                    
                    # Vẽ text thông tin
                    nhan_hien_thi = f"ID: {track_id} | {ten_lop_tieng_anh.upper()}"
                    if toc_do_tinh_duoc:
                        nhan_hien_thi += f" | {int(toc_do_tinh_duoc)} km/h"
                    if vi_pham_hien_tai:
                        nhan_hien_thi += f" | {vi_pham_hien_tai[0]}"
                        
                    cv2.putText(frame_ve, nhan_hien_thi, (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, mau_khung, 2)

                # Mã hóa frame đã vẽ thành JPEG
                _, buffer = cv2.imencode('.jpg', frame_ve)
                base64_image = base64.b64encode(buffer).decode('utf-8')
                
                # Gửi gói dữ liệu lên WebSocket dưới dạng JSON
                goi_tin_ws = {
                    "hinh_anh": f"data:image/jpeg;base64,{base64_image}",
                    "den_tin_hieu": self.den_giao_thong
                }
                
                await websocket.send(json.dumps(goi_tin_ws))
                
                # Giới hạn tốc độ khung hình (FPS) cho phù hợp
                await asyncio.sleep(0.03) # ~30 FPS

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=str, default="giao_thong_mau.mp4", help="Đường dẫn file video hoặc link stream")
    args = parser.parse_args()
    
    # Đợi máy chủ FastAPI sẵn sàng chạy trước
    time.sleep(2)
    
    duong_dan_video = args.video
    # Tạo file video mẫu giả lập nếu không tìm thấy file video thật
    if not os.path.exists(duong_dan_video):
        print(f"Cảnh báo: Không tìm thấy file {duong_dan_video}. Bạn cần chuẩn bị file video hoặc tải video demo.")
    
    luong_chinh = LuongXuLyGiaoThong(duong_dan_video)
    try:
        asyncio.run(luong_chinh.chay_he_thong())
    except KeyboardInterrupt:
        print("Đã dừng AI Pipeline.")
