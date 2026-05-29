import easyocr
import re
import cv2

class BoNhanDienBienSo:
    def __init__(self):
        # Khởi tạo EasyOCR reader cho tiếng Anh (chữ cái và chữ số)
        # và chạy trên GPU nếu có sẵn
        print("Đang khởi tạo EasyOCR Reader...")
        self.reader = easyocr.Reader(['en'], gpu=True)
        print("EasyOCR Reader đã sẵn sàng.")

    def doc_bien_so(self, anh_crop):
        """
        Nhận diện biển số xe từ ảnh vùng biển số đã được crop.
        """
        if anh_crop is None or anh_crop.size == 0:
            return "Chưa xác định"
            
        try:
            # Tiền xử lý ảnh nhẹ để nâng cao chất lượng OCR
            gray = cv2.cvtColor(anh_crop, cv2.COLOR_BGR2GRAY)
            # Khử nhiễu và tăng độ tương phản bằng CLAHE
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
            
            # Đọc text bằng EasyOCR
            results = self.reader.readtext(gray)
            
            if not results:
                return "Chưa xác định"
                
            # Ghép tất cả các đoạn text đọc được và loại bỏ ký tự đặc biệt
            text_ghep = ""
            for bbox, text, score in results:
                # Chỉ lấy những phần text có độ tin cậy > 20%
                if score > 0.20:
                    text_ghep += text.upper()
                    
            # Làm sạch biển số: loại bỏ các ký tự đặc biệt, chỉ giữ lại chữ cái và chữ số
            bien_so_sach = re.sub(r'[^A-Z0-9]', '', text_ghep)
            
            # Chuẩn hóa biển số Việt Nam cơ bản:
            # Ví dụ: 29A12345 -> 29A-123.45 hoặc giữ nguyên chuỗi
            if len(bien_so_sach) >= 7 and len(bien_so_sach) <= 10:
                return bien_so_sach
                
            return bien_so_sach if bien_so_sach else "Chưa xác định"
            
        except Exception as e:
            print(f"Lỗi khi OCR biển số: {e}")
            return "Lỗi nhận diện"
