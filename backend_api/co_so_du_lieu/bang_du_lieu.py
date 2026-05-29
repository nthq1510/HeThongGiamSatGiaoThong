from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from datetime import datetime
from .ket_noi import Base

class ViPham(Base):
    __tablename__ = "vi_pham"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    thoi_gian = Column(DateTime, default=datetime.now, index=True)
    loai_vi_pham = Column(String, index=True)      # Đi ngược chiều, Vượt đèn đỏ, Không đội mũ, Quá tốc độ, Sai làn
    loai_phuong_tien = Column(String)             # car, motorcycle, truck, bus
    bien_so = Column(String, default="Chưa xác định", index=True)
    anh_bang_chung = Column(String)               # Đường dẫn ảnh chụp bằng chứng vi phạm
    bien_so_crop = Column(String, nullable=True)  # Đường dẫn ảnh chụp riêng biển số
    toc_do_do_duoc = Column(Float, nullable=True) # Tốc độ đo được (nếu là lỗi quá tốc độ)
    da_xu_ly = Column(Boolean, default=False)      # Trạng thái xử phạt (chưa xử lý/đã xử lý)

    def to_dict(self):
        return {
            "id": self.id,
            "thoi_gian": self.thoi_gian.strftime("%Y-%m-%d %H:%M:%S"),
            "loai_vi_pham": self.loai_vi_pham,
            "loai_phuong_tien": self.loai_phuong_tien,
            "bien_so": self.bien_so,
            "anh_bang_chung": self.anh_bang_chung,
            "bien_so_crop": self.bien_so_crop,
            "toc_do_do_duoc": self.toc_do_do_duoc,
            "da_xu_ly": self.da_xu_ly
        }
