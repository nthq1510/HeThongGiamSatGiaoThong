from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Đường dẫn tệp tin cơ sở dữ liệu SQLite
DUONG_DAN_DB = "co_so_du_lieu/giao_thong.db"
URL_DB = f"sqlite:///./{DUONG_DAN_DB}"

# Đảm bảo thư mục lưu trữ cơ sở dữ liệu tồn tại
os.makedirs(os.path.dirname(DUONG_DAN_DB), exist_ok=True)

# Khởi tạo engine
engine = create_engine(
    URL_DB, connect_args={"check_same_thread": False}
)

# Khởi tạo Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class cho ORM models
Base = declarative_base()

# Dependency để lấy DB session cho mỗi request API
def lay_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
