from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os
import json
import shutil
from typing import List, Dict

# Import cơ sở dữ liệu
from co_so_du_lieu.ket_noi import Base, engine, lay_db
from co_so_du_lieu.bang_du_lieu import ViPham

# Tạo bảng trong database khi khởi chạy ứng dụng
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hệ thống Giám sát Giao thông Thông minh - API")

# Cấu hình CORS để Frontend có thể gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thư mục lưu trữ hình ảnh tải lên làm bằng chứng
THU_MUC_ANH = "thu_muc_tinh"
THU_MUC_UPLOADS = os.path.join(THU_MUC_ANH, "uploads")
os.makedirs(THU_MUC_UPLOADS, exist_ok=True)

# Mount thư mục tĩnh để truy cập ảnh trực tiếp từ URL
app.mount("/static", StaticFiles(directory=THU_MUC_ANH), name="static")

# Quản lý các kết nối WebSockets
class ConnectionManager:
    def __init__(self):
        # Danh sách kết nối của các Client Frontend
        self.giao_dien_clients: List[WebSocket] = []
        # Kết nối của AI Engine
        self.ai_client: WebSocket = None

    async def connect_giao_dien(self, websocket: WebSocket):
        await websocket.accept()
        self.giao_dien_clients.append(websocket)
        print(f"Frontend Client connected. Total: {len(self.giao_dien_clients)}")

    def disconnect_giao_dien(self, websocket: WebSocket):
        if websocket in self.giao_dien_clients:
            self.giao_dien_clients.remove(websocket)
            print(f"Frontend Client disconnected. Total: {len(self.giao_dien_clients)}")

    async def connect_ai(self, websocket: WebSocket):
        await websocket.accept()
        self.ai_client = websocket
        print("AI Engine connected via WebSocket.")

    def disconnect_ai(self):
        self.ai_client = None
        print("AI Engine disconnected.")

    async def phat_song_video(self, data: str):
        # Phát luồng video từ AI Engine tới toàn bộ các Frontend Client
        for connection in self.giao_dien_clients:
            try:
                await connection.send_text(data)
            except Exception:
                # Nếu kết nối lỗi, bỏ qua (sẽ tự dọn dẹp khi disconnect)
                pass

    async def thong_bao_vi_pham(self, vi_pham_dict: dict):
        # Đẩy thông báo vi phạm mới lên cho Frontend
        payload = json.dumps({"kieu": "vi_pham_moi", "du_lieu": vi_pham_dict})
        for connection in self.giao_dien_clients:
            try:
                await connection.send_text(payload)
            except Exception:
                pass

manager = ConnectionManager()

# --- WEB SOCKETS ROUTERS ---

@app.websocket("/ws/nhap-luong-ai")
async def websocket_ai(websocket: WebSocket):
    await manager.connect_ai(websocket)
    try:
        while True:
            # Nhận dữ liệu frame ảnh (Base64) từ AI Engine
            data = await websocket.receive_text()
            # Đẩy tiếp frame này tới toàn bộ Frontend đang kết nối để xem trực tiếp
            await manager.phat_song_video(data)
    except WebSocketDisconnect:
        manager.disconnect_ai()

@app.websocket("/ws/xem-luong-giao-dien")
async def websocket_frontend(websocket: WebSocket):
    await manager.connect_giao_dien(websocket)
    try:
        while True:
            # Giữ kết nối mở
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_giao_dien(websocket)


# --- REST API ROUTERS ---

@app.get("/api/vi-pham", response_model=Dict)
def lay_danh_sach_vi_pham(
    db: Session = Depends(lay_db),
    page: int = 1,
    limit: int = 10,
    loai_vi_pham: str = None,
    bien_so: str = None,
    da_xu_ly: bool = None
):
    query = db.query(ViPham)
    
    if loai_vi_pham:
        query = query.filter(ViPham.loai_vi_pham == loai_vi_pham)
    if bien_so:
        query = query.filter(ViPham.bien_so.contains(bien_so))
    if da_xu_ly is not None:
        query = query.filter(ViPham.da_xu_ly == da_xu_ly)
        
    tong_so = query.count()
    vi_phams = query.order_by(ViPham.thoi_gian.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "tong_so": tong_so,
        "trang": page,
        "gioi_han": limit,
        "du_lieu": [vp.to_dict() for vp in vi_phams]
    }

@app.post("/api/vi-pham")
async def tao_vi_pham(
    loai_vi_pham: str = Form(...),
    loai_phuong_tien: str = Form(...),
    bien_so: str = Form("Chưa xác định"),
    toc_do_do_duoc: float = Form(None),
    anh_bang_chung: UploadFile = File(...),
    anh_bien_so: UploadFile = File(None),
    db: Session = Depends(lay_db)
):
    # Lưu ảnh bằng chứng vi phạm
    thoi_gian_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_anh_bang_chung = f"vi_pham_{thoi_gian_str}.jpg"
    duong_dan_anh = os.path.join(THU_MUC_UPLOADS, file_anh_bang_chung)
    with open(duong_dan_anh, "wb") as buffer:
        shutil.copyfileobj(anh_bang_chung.file, buffer)
        
    duong_dan_bien_so = None
    if anh_bien_so:
        file_anh_bien_so = f"bien_so_{thoi_gian_str}.jpg"
        duong_dan_bien_so = os.path.join(THU_MUC_UPLOADS, file_anh_bien_so)
        with open(duong_dan_bien_so, "wb") as buffer:
            shutil.copyfileobj(anh_bien_so.file, buffer)

    # Đường dẫn tương đối lưu vào DB để client tải qua /static/uploads/...
    anh_bang_chung_rel = f"static/uploads/{file_anh_bang_chung}"
    bien_so_crop_rel = f"static/uploads/{file_anh_bien_so}" if anh_bien_so else None

    # Lưu vào Database
    vp_moi = ViPham(
        loai_vi_pham=loai_vi_pham,
        loai_phuong_tien=loai_phuong_tien,
        bien_so=bien_so,
        toc_do_do_duoc=toc_do_do_duoc,
        anh_bang_chung=anh_bang_chung_rel,
        bien_so_crop=bien_so_crop_rel,
        da_xu_ly=False
    )
    db.add(vp_moi)
    db.commit()
    db.refresh(vp_moi)

    # Đẩy thông báo thời gian thực lên Frontend
    vp_dict = vp_moi.to_dict()
    await manager.thong_bao_vi_pham(vp_dict)

    return {"status": "success", "data": vp_dict}

@app.put("/api/vi-pham/{id_vi_pham}/xu-ly")
def xu_ly_vi_pham(id_vi_pham: int, db: Session = Depends(lay_db)):
    vp = db.query(ViPham).filter(ViPham.id == id_vi_pham).first()
    if not vp:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi vi phạm")
    
    vp.da_xu_ly = True
    db.commit()
    db.refresh(vp)
    return {"status": "success", "data": vp.to_dict()}

@app.get("/api/thong-ke")
def lay_thong_ke(db: Session = Depends(lay_db)):
    # Lấy dữ liệu thống kê trong 7 ngày gần đây
    ngay_hien_tai = datetime.now()
    bay_ngay_truoc = ngay_hien_tai - timedelta(days=7)
    
    # 1. Tổng số vi phạm và số ca đã xử lý
    tong_so = db.query(ViPham).count()
    da_xu_ly = db.query(ViPham).filter(ViPham.da_xu_ly == True).count()
    chua_xu_ly = tong_so - da_xu_ly

    # 2. Phân loại theo loại vi phạm
    thong_ke_loai = {}
    cac_loai = db.query(ViPham.loai_vi_pham).distinct().all()
    for l in cac_loai:
        loai = l[0]
        count = db.query(ViPham).filter(ViPham.loai_vi_pham == loai).count()
        thong_ke_loai[loai] = count

    # 3. Phân loại theo phương tiện
    thong_ke_xe = {}
    cac_xe = db.query(ViPham.loai_phuong_tien).distinct().all()
    for x in cac_xe:
        xe = x[0]
        count = db.query(ViPham).filter(ViPham.loai_phuong_tien == xe).count()
        thong_ke_xe[xe] = count

    # 4. Thống kê số lỗi theo 7 ngày qua
    bieu_do_ngay = []
    for i in range(7):
        ngay = (ngay_hien_tai - timedelta(days=i)).date()
        so_luong = db.query(ViPham).filter(
            ViPham.thoi_gian >= datetime.combine(ngay, datetime.min.time()),
            ViPham.thoi_gian <= datetime.combine(ngay, datetime.max.time())
        ).count()
        bieu_do_ngay.append({
            "ngay": ngay.strftime("%d/%m"),
            "so_luong": so_luong
        })
    bieu_do_ngay.reverse()

    return {
        "tong_quan": {
            "tong_so": tong_so,
            "da_xu_ly": da_xu_ly,
            "chua_xu_ly": chua_xu_ly
        },
        "theo_loai": thong_ke_loai,
        "theo_phuong_tien": thong_ke_xe,
        "theo_ngay": bieu_do_ngay
    }
