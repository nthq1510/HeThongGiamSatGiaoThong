import numpy as np

class BoTheoDoi:
    def __init__(self):
        # Lưu lịch sử tọa độ trọng tâm của từng ID để tính toán hướng đi và tốc độ
        # Cấu trúc: {id: [(cx, cy, timestamp), ...]}
        self.lich_su_vi_tri = {}

    def cap_nhat_vi_tri(self, track_id, cx, cy, thoi_gian):
        if track_id not in self.lich_su_vi_tri:
            self.lich_su_vi_tri[track_id] = []
        self.lich_su_vi_tri[track_id].append((cx, cy, thoi_gian))
        
        # Chỉ giữ lại 30 frame gần nhất để tránh tốn bộ nhớ
        if len(self.lich_su_vi_tri[track_id]) > 30:
            self.lich_su_vi_tri[track_id].pop(0)

    def lay_lich_su(self, track_id):
        return self.lich_su_vi_tri.get(track_id, [])

    def xoa_doi_tuong(self, track_id):
        if track_id in self.lich_su_vi_tri:
            del self.lich_su_vi_tri[track_id]

    @staticmethod
    def trich_xuat_ket_qua_track(results):
        """
        Trích xuất kết quả tracking từ kết quả trả về của Ultralytics YOLOv8.
        Trả về danh sách các đối tượng dạng dict.
        """
        doi_tuong_theo_doi = []
        
        # Kiểm tra xem có boxes nào được nhận diện không
        if results[0].boxes is None or results[0].boxes.id is None:
            return doi_tuong_theo_doi
            
        boxes = results[0].boxes.xyxy.cpu().numpy()
        ids = results[0].boxes.id.cpu().numpy().astype(int)
        clss = results[0].boxes.cls.cpu().numpy().astype(int)
        confs = results[0].boxes.conf.cpu().numpy()
        
        for box, track_id, cls, conf in zip(boxes, ids, clss, confs):
            x1, y1, x2, y2 = box
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
            
            doi_tuong_theo_doi.append({
                "id": int(track_id),
                "toa_do": [int(x1), int(y1), int(x2), int(y2)],
                "lop": int(cls),
                "do_tin_cay": float(conf),
                "trong_tam": (cx, cy)
            })
            
        return doi_tuong_theo_doi
