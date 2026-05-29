import urllib.request
import os

def tai_video():
    url = "https://github.com/intel-iot-devkit/sample-videos/raw/master/car-detection.mp4"
    duong_dan_luu = "../giao_thong_mau.mp4"
    
    print(f"Đang tải video giao thông mẫu từ: {url}")
    print("Vui lòng đợi trong giây lát...")
    
    try:
        # Tải file về
        urllib.request.urlretrieve(url, duong_dan_luu)
        size_mb = os.path.getsize(duong_dan_luu) / (1024 * 1024)
        print(f"Tải video thành công! Lưu tại: {os.path.abspath(duong_dan_luu)} ({size_mb:.2f} MB)")
    except Exception as e:
        print(f"Lỗi khi tải video mẫu: {e}")
        print("Mẹo: Bạn có thể tự chuẩn bị một file video MP4 bất kỳ và đổi tên thành 'giao_thong_mau.mp4' đặt tại thư mục dự án.")

if __name__ == "__main__":
    tai_video()
