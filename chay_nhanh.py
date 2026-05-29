import subprocess
import time
import sys
import os
import signal

# Danh sách chứa các tiến trình đang chạy
processes = []

def cleanup(sig=None, frame=None):
    print("\n đang dừng toàn bộ hệ thống...")
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=2)
        except Exception:
            pass
    print(" Hệ thống đã dừng hoàn toàn.")
    sys.exit(0)

# Đăng ký tín hiệu kết thúc để tắt toàn bộ tiến trình con khi nhấn Ctrl+C
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def main():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    
    # 1. Khởi chạy Backend FastAPI
    print("🚀 1. Đang khởi chạy FastAPI Backend API...")
    path_venv_bin = os.path.join(base_dir, "venv", "bin")
    
    # Lệnh chạy Backend
    cmd_backend = [
        os.path.join(path_venv_bin, "uvicorn"),
        "chinh:app",
        "--host", "127.0.0.1",
        "--port", "8000",
        "--reload"
    ]
    p_backend = subprocess.Popen(
        cmd_backend,
        cwd=os.path.join(base_dir, "backend_api"),
        stdout=subprocess.DEVNULL, # Chạy ngầm log để không làm rối console chính
        stderr=subprocess.DEVNULL
    )
    processes.append(p_backend)
    print("   [OK] Backend đang chạy tại http://localhost:8000")
    
    # 2. Khởi chạy Frontend React (Vite)
    print("🚀 2. Đang khởi chạy Frontend Vite Dashboard...")
    # Kiểm tra xem có npm trên Windows hay Unix
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    p_frontend = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=os.path.join(base_dir, "giao_dien_web"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    processes.append(p_frontend)
    print("   [OK] Frontend Dashboard đang chạy tại http://localhost:5173")
    
    # Đợi 5 giây để Backend và Frontend khởi động xong
    print("⏱ Đang đợi 5 giây cho các dịch vụ khởi động hoàn tất...")
    time.sleep(5)
    
    # 3. Khởi chạy Động cơ xử lý AI (AI Engine)
    print("🚀 3. Đang khởi chạy AI Engine...")
    cmd_ai = [
        os.path.join(path_venv_bin, "python"),
        "luong_chinh.py",
        "--video", "../giao_thong_mau.mp4"
    ]
    p_ai = subprocess.Popen(
        cmd_ai,
        cwd=os.path.join(base_dir, "bo_xu_ly_ai")
    )
    processes.append(p_ai)
    print("   [OK] AI Engine đang xử lý video giao_thong_mau.mp4 và truyền trực tiếp về Dashboard")
    
    print("\n=======================================================")
    print(" HỆ THỐNG ĐÃ SẴN SÀNG HOẠT ĐỘNG!")
    print(" - Nhấn http://localhost:5173 trên trình duyệt để xem.")
    print(" - Nhấn Ctrl+C để dừng toàn bộ hệ thống.")
    print("=======================================================\n")
    
    # Giữ luồng chính chạy để giám sát
    while True:
        # Kiểm tra xem các tiến trình con có bị chết đột ngột không
        for p in processes:
            if p.poll() is not None:
                print(f"⚠️ Cảnh báo: Một tiến trình con đã dừng (Exit code: {p.returncode}). Tự động tắt hệ thống...")
                cleanup()
        time.sleep(1)

if __name__ == "__main__":
    main()
