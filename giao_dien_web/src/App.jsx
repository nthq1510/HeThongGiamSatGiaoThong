import React, { useState, useEffect, useRef } from 'react';
import { 
  Shield, 
  Activity, 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  Search, 
  Eye, 
  RefreshCw, 
  Database, 
  TrendingUp, 
  Car, 
  Sliders,
  Play,
  Pause
} from 'lucide-react';
import './App.css';

const API_BASE = "http://localhost:8000";

function App() {
  // Luồng trực tiếp và Trạng thái kết nối
  const [streamImage, setStreamImage] = useState(null);
  const [trafficLight, setTrafficLight] = useState("GREEN");
  const [wsStatus, setWsStatus] = useState("disconnected");
  
  // Danh sách vi phạm & Thống kê
  const [violations, setViolations] = useState([]);
  const [totalViolations, setTotalViolations] = useState(0);
  const [stats, setStats] = useState({
    tong_quan: { tong_so: 0, da_xu_ly: 0, chua_xu_ly: 0 },
    theo_loai: {},
    theo_phuong_tien: {},
    theo_ngay: []
  });
  
  // Cảnh báo thời gian thực nhận được từ socket
  const [liveAlerts, setLiveAlerts] = useState([]);
  const [alertFlashId, setAlertFlashId] = useState(null);

  // Bộ lọc & Phân trang cho Database
  const [page, setPage] = useState(1);
  const [limit] = useState(8);
  const [searchPlate, setSearchPlate] = useState("");
  const [filterType, setFilterType] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  
  // Modal Xem chi tiết
  const [selectedViolation, setSelectedViolation] = useState(null);
  
  // Refs
  const wsRef = useRef(null);

  // Tải dữ liệu ban đầu
  const fetchViolations = async () => {
    try {
      let url = `${API_BASE}/api/vi-pham?page=${page}&limit=${limit}`;
      if (searchPlate) url += `&bien_so=${searchPlate}`;
      if (filterType) url += `&loai_vi_pham=${filterType}`;
      if (filterStatus !== "") url += `&da_xu_ly=${filterStatus === "true"}`;
      
      const res = await fetch(url);
      const data = await res.json();
      setViolations(data.du_lieu || []);
      setTotalViolations(data.tong_so || 0);
    } catch (e) {
      console.error("Lỗi tải danh sách vi phạm:", e);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/thong-ke`);
      const data = await res.json();
      setStats(data);
    } catch (e) {
      console.error("Lỗi tải thống kê:", e);
    }
  };

  // Cập nhật khi bộ lọc hoặc trang thay đổi
  useEffect(() => {
    fetchViolations();
  }, [page, searchPlate, filterType, filterStatus]);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 10000); // Tự động cập nhật stats mỗi 10s
    return () => clearInterval(interval);
  }, []);

  // Kết nối WebSockets để xem video stream và thông báo vi phạm mới
  useEffect(() => {
    const connectWS = () => {
      setWsStatus("connecting");
      const wsUrl = `ws://localhost:8000/ws/xem-luong-giao-dien`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsStatus("connected");
        console.log("WebSocket connected to backend.");
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          
          // Nhận luồng video từ AI
          if (payload.hinh_anh) {
            setStreamImage(payload.hinh_anh);
            if (payload.den_tin_hieu) {
              setTrafficLight(payload.den_tin_hieu);
            }
          }
          
          // Nhận thông báo vi phạm mới
          if (payload.kieu === "vi_pham_moi") {
            const vp_moi = payload.du_lieu;
            
            // Đưa lên đầu feed cảnh báo
            setLiveAlerts(prev => [vp_moi, ...prev.slice(0, 9)]);
            
            // Tạo hiệu ứng nhấp nháy cho card cảnh báo mới
            setAlertFlashId(vp_moi.id);
            setTimeout(() => setAlertFlashId(null), 3000);
            
            // Phát âm thanh cảnh báo bíp nhẹ
            playAlertSound();
            
            // Cập nhật lại danh sách và thống kê
            fetchViolations();
            fetchStats();
          }
        } catch (e) {
          // Xử lý dữ liệu thô nếu không phải JSON (frame video dạng chuỗi)
          if (typeof event.data === 'string' && event.data.startsWith('data:image')) {
            setStreamImage(event.data);
          }
        }
      };

      ws.onclose = () => {
        setWsStatus("disconnected");
        setStreamImage(null);
        // Tự động kết nối lại sau 3 giây
        setTimeout(connectWS, 3000);
      };

      ws.onerror = (err) => {
        console.error("Lỗi kết nối WebSocket:", err);
        ws.close();
      };
    };

    connectWS();

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  // Hàm phát âm thanh cảnh báo lỗi
  const playAlertSound = () => {
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioCtx.createOscillator();
      const gainNode = audioCtx.createGain();
      
      oscillator.type = 'sine';
      oscillator.frequency.setValueAtTime(880, audioCtx.currentTime); // Âm cao cảnh báo
      gainNode.gain.setValueAtTime(0.15, audioCtx.currentTime);
      
      oscillator.connect(gainNode);
      gainNode.connect(audioCtx.destination);
      
      oscillator.start();
      oscillator.stop(audioCtx.currentTime + 0.15); // Kéo dài 150ms
    } catch (e) {
      // Trình duyệt có thể chặn âm thanh nếu chưa tương tác
    }
  };

  // Đánh dấu vi phạm đã xử lý
  const handleMarkProcessed = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/api/vi-pham/${id}/xu-ly`, {
        method: 'PUT'
      });
      if (res.ok) {
        // Cập nhật state tại chỗ
        setViolations(prev => prev.map(vp => vp.id === id ? { ...vp, da_xu_ly: true } : vp));
        if (selectedViolation && selectedViolation.id === id) {
          setSelectedViolation(prev => ({ ...prev, da_xu_ly: true }));
        }
        setLiveAlerts(prev => prev.map(vp => vp.id === id ? { ...vp, da_xu_ly: true } : vp));
        fetchStats();
      }
    } catch (e) {
      console.error("Lỗi cập nhật xử lý:", e);
    }
  };

  // Dịch loại vi phạm sang màu sắc tương ứng
  const layMauLoi = (loai) => {
    switch (loai) {
      case "Vượt đèn đỏ": return "var(--color-red)";
      case "Đi ngược chiều": return "var(--color-orange)";
      case "Chạy quá tốc độ": return "var(--color-purple)";
      case "Đi sai làn đường": return "var(--color-yellow)";
      case "Không đội mũ bảo hiểm": return "var(--color-secondary)";
      default: return "var(--primary)";
    }
  };

  return (
    <div className="dashboard-container">
      {/* HEADER SECTION */}
      <header className="dashboard-header glass-panel">
        <div className="header-title-section">
          <h1>
            <Shield size={28} color="var(--primary)" />
            TRAFFIC AI GUARD
          </h1>
          <p>Hệ thống giám sát giao thông và phát hiện vi phạm thời gian thực</p>
        </div>
        
        <div className="status-badge-container">
          <div className="status-badge">
            <span className="status-indicator status-online"></span>
            <span>API Server: Online</span>
          </div>
          <div className="status-badge">
            <span className={`status-indicator ${wsStatus === 'connected' ? 'status-online' : wsStatus === 'connecting' ? 'status-yellow' : 'status-offline'}`}></span>
            <span>AI Pipeline: {wsStatus === 'connected' ? 'Streaming' : wsStatus === 'connecting' ? 'Connecting...' : 'Offline'}</span>
          </div>
        </div>
      </header>

      {/* STATS OVERVIEW CARDS */}
      <div className="stats-grid">
        <div className="glass-panel stat-card">
          <div className="stat-icon-box" style={{ background: 'rgba(99, 102, 241, 0.1)', color: 'var(--primary)' }}>
            <Activity size={24} />
          </div>
          <div className="stat-info">
            <h3>Tổng số ghi nhận</h3>
            <p>{stats.tong_quan.tong_so}</p>
          </div>
        </div>

        <div className="glass-panel stat-card">
          <div className="stat-icon-box" style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--color-red)' }}>
            <AlertTriangle size={24} />
          </div>
          <div className="stat-info">
            <h3>Chưa xử phạt</h3>
            <p>{stats.tong_quan.chua_xu_ly}</p>
          </div>
        </div>

        <div className="glass-panel stat-card">
          <div className="stat-icon-box" style={{ background: 'rgba(16, 185, 129, 0.1)', color: 'var(--color-green)' }}>
            <CheckCircle size={24} />
          </div>
          <div className="stat-info">
            <h3>Đã lập biên bản</h3>
            <p>{stats.tong_quan.da_xu_ly}</p>
          </div>
        </div>

        <div className="glass-panel stat-card">
          <div className="stat-icon-box" style={{ background: 'rgba(14, 165, 233, 0.1)', color: 'var(--color-secondary)' }}>
            <Clock size={24} />
          </div>
          <div className="stat-info">
            <h3>Tỷ lệ xử lý</h3>
            <p>
              {stats.tong_quan.tong_so > 0 
                ? `${Math.round((stats.tong_quan.da_xu_ly / stats.tong_quan.tong_so) * 100)}%` 
                : "0%"}
            </p>
          </div>
        </div>
      </div>

      {/* MAIN CONTENT SECTION: STREAM & LIVE FEED */}
      <div className="main-grid">
        {/* LEFT COLUMN: LIVE VIDEO STREAM */}
        <div className="glass-panel" style={{ overflow: 'hidden' }}>
          <div className="card-title">
            <div className="card-title-text">
              <Sliders size={20} color="var(--primary)" />
              <span>Camera giám sát trực tiếp (Vùng ROI)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: '#64748b' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: wsStatus === 'connected' ? 'var(--color-green)' : 'var(--color-red)' }}></span>
              {wsStatus === 'connected' ? 'Luồng thời gian thực' : 'Mất kết nối luồng'}
            </div>
          </div>
          
          <div className="video-stream-container">
            {streamImage ? (
              <img src={streamImage} alt="Video Stream" className="video-stream-img" />
            ) : (
              <div className="video-placeholder">
                <Play size={48} style={{ opacity: 0.3 }} />
                <p>Đang chờ luồng dữ liệu từ AI Engine...</p>
                <p style={{ fontSize: '0.75rem', color: '#475569' }}>Hãy khởi chạy file `luong_chinh.py` để đẩy luồng camera</p>
              </div>
            )}

            {/* Đèn tín hiệu giao thông mô phỏng hiển thị trên luồng */}
            <div className="traffic-light-overlay">
              <div className={`light-bulb ${trafficLight === 'RED' ? 'active-red' : ''}`} style={{ backgroundColor: '#ef4444' }}></div>
              <div className={`light-bulb ${trafficLight === 'YELLOW' ? 'active-yellow' : ''}`} style={{ backgroundColor: '#f59e0b' }}></div>
              <div className={`light-bulb ${trafficLight === 'GREEN' ? 'active-green' : ''}`} style={{ backgroundColor: '#10b981' }}></div>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: LIVE ALERT FEED */}
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column' }}>
          <div className="card-title">
            <div className="card-title-text">
              <AlertTriangle size={20} color="var(--color-red)" />
              <span>Cảnh báo vi phạm thời gian thực</span>
            </div>
          </div>
          
          <div className="alerts-feed-container">
            {liveAlerts.length === 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: '300px', color: '#475569', gap: '0.5rem' }}>
                <Clock size={36} style={{ opacity: 0.3 }} />
                <p style={{ fontSize: '0.85rem' }}>Chưa có cảnh báo vi phạm mới nào...</p>
                <p style={{ fontSize: '0.75rem', textAlign: 'center', maxWidth: '80%' }}>Các vi phạm được phát hiện từ camera sẽ ngay lập tức đẩy lên đây.</p>
              </div>
            ) : (
              liveAlerts.map(alert => (
                <div 
                  key={alert.id} 
                  className={`alert-card ${alertFlashId === alert.id ? 'alert-flash' : ''} animate-slide-in`}
                >
                  <img 
                    src={`${API_BASE}/${alert.anh_bang_chung}`} 
                    alt="Proof" 
                    className="alert-thumb"
                    onClick={() => setSelectedViolation(alert)}
                  />
                  <div className="alert-details">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span 
                        className="alert-type-badge" 
                        style={{ backgroundColor: `${layMauLoi(alert.loai_vi_pham)}15`, color: layMauLoi(alert.loai_vi_pham) }}
                      >
                        {alert.loai_vi_pham}
                      </span>
                      <span className="alert-time">{alert.thoi_gian.split(' ')[1]}</span>
                    </div>
                    
                    <div className="alert-vehicle-info">
                      Xe: <span style={{ textTransform: 'capitalize', color: '#cbd5e1' }}>{alert.loai_phuong_tien}</span> | Biển: <span className="alert-plate">{alert.bien_so}</span>
                    </div>
                    
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.25rem' }}>
                      <span style={{ fontSize: '0.75rem', color: alert.da_xu_ly ? 'var(--color-green)' : 'var(--color-yellow)' }}>
                        {alert.da_xu_ly ? '✓ Đã ghi nhận xử phạt' : '⏱ Đang chờ duyệt'}
                      </span>
                      {!alert.da_xu_ly && (
                        <button 
                          className="btn-primary" 
                          onClick={() => handleMarkProcessed(alert.id)}
                          style={{ padding: '0.2rem 0.5rem', fontSize: '0.7rem' }}
                        >
                          Xử lý nhanh
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* ANALYTICS SECTION (CHARTS) */}
      <div className="charts-grid">
        {/* Chart 1: Lịch sử vi phạm 7 ngày qua (SVG Bar Chart) */}
        <div className="glass-panel">
          <div className="card-title">
            <div className="card-title-text">
              <TrendingUp size={20} color="var(--primary)" />
              <span>Biểu đồ vi phạm trong tuần qua</span>
            </div>
          </div>
          <div className="chart-card-body">
            {stats.theo_ngay.length === 0 ? (
              <p style={{ color: '#475569', fontSize: '0.85rem' }}>Đang tải dữ liệu biểu đồ...</p>
            ) : (
              <svg width="100%" height="220" viewBox="0 0 500 220" style={{ overflow: 'visible' }}>
                {/* Vẽ các đường lưới ngang */}
                <line x1="30" y1="160" x2="480" y2="160" stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
                <line x1="30" y1="110" x2="480" y2="110" stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
                <line x1="30" y1="60" x2="480" y2="60" stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
                <line x1="30" y1="10" x2="480" y2="10" stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
                
                {stats.theo_ngay.map((item, index) => {
                  const maxVal = Math.max(...stats.theo_ngay.map(d => d.so_luong), 5);
                  const barHeight = (item.so_luong / maxVal) * 150;
                  const x = 50 + index * 60;
                  const y = 160 - barHeight;
                  
                  return (
                    <g key={index}>
                      {/* Bar */}
                      <rect 
                        x={x} 
                        y={y} 
                        width="30" 
                        height={barHeight} 
                        fill="url(#barGradient)" 
                        rx="4" 
                        style={{ transition: 'all 0.5s ease' }}
                      />
                      {/* Số liệu bên trên cột */}
                      <text x={x + 15} y={y - 8} textAnchor="middle" fill="#cbd5e1" fontSize="10" fontWeight="bold">
                        {item.so_luong}
                      </text>
                      {/* Nhãn ngày bên dưới cột */}
                      <text x={x + 15} y="180" textAnchor="middle" fill="#64748b" fontSize="10">
                        {item.ngay}
                      </text>
                    </g>
                  );
                })}
                <defs>
                  <linearGradient id="barGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stopColor="#818cf8" />
                    <stop offset="100%" stopColor="#4f46e5" />
                  </linearGradient>
                </defs>
              </svg>
            )}
          </div>
        </div>

        {/* Chart 2: Phân bố xe vi phạm (Progress Bars) */}
        <div className="glass-panel">
          <div className="card-title">
            <div className="card-title-text">
              <Car size={20} color="var(--color-secondary)" />
              <span>Phương tiện vi phạm nhiều nhất</span>
            </div>
          </div>
          <div className="chart-card-body" style={{ flexDirection: 'column', alignItems: 'stretch', justifyContent: 'center', padding: '1.5rem' }}>
            {Object.keys(stats.theo_phuong_tien).length === 0 ? (
              <div style={{ textAlign: 'center', color: '#475569', fontSize: '0.85rem' }}>Chưa có dữ liệu phương tiện</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', width: '100%' }}>
                {Object.entries(stats.theo_phuong_tien).map(([xe, count]) => {
                  const maxCount = Math.max(...Object.values(stats.theo_phuong_tien), 1);
                  const phan_tram = (count / maxCount) * 100;
                  
                  return (
                    <div key={xe} style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                        <span style={{ textTransform: 'capitalize', fontWeight: 600, color: '#94a3b8' }}>{xe === "motorcycle" ? "Xe máy" : xe === "car" ? "Ô tô" : xe === "truck" ? "Xe tải" : xe === "bus" ? "Xe buýt" : xe}</span>
                        <span style={{ fontWeight: 'bold', color: '#f1f5f9' }}>{count} lượt</span>
                      </div>
                      <div style={{ width: '100%', height: 8, background: 'rgba(255,255,255,0.03)', borderRadius: 999, overflow: 'hidden', border: '1px solid var(--border-glass)' }}>
                        <div style={{ width: `${phan_tram}%`, height: '100%', background: 'linear-gradient(to right, #38bdf8, #0284c7)', borderRadius: 999, transition: 'width 0.8s cubic-bezier(0.4, 0, 0.2, 1)' }}></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* DATABASE GRID / ARCHIVE LIST */}
      <div className="glass-panel db-card-container">
        <div className="card-title">
          <div className="card-title-text">
            <Database size={20} color="var(--primary)" />
            <span>Cơ sở dữ liệu lưu vết vi phạm</span>
          </div>
          <button className="btn-icon" onClick={fetchViolations} title="Làm mới cơ sở dữ liệu">
            <RefreshCw size={16} />
          </button>
        </div>

        {/* BỘ LỌC TÌM KIẾM */}
        <div className="db-filters">
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <Search size={16} style={{ position: 'absolute', left: 12, color: '#64748b' }} />
            <input 
              type="text" 
              placeholder="Tìm kiếm biển số xe..." 
              value={searchPlate}
              onChange={(e) => { setSearchPlate(e.target.value); setPage(1); }}
              className="filter-input"
              style={{ paddingLeft: '2.25rem' }}
            />
          </div>

          <select 
            value={filterType} 
            onChange={(e) => { setFilterType(e.target.value); setPage(1); }}
            className="filter-select"
          >
            <option value="">-- Tất cả các lỗi --</option>
            <option value="Vượt đèn đỏ">Vượt đèn đỏ</option>
            <option value="Đi ngược chiều">Đi ngược chiều</option>
            <option value="Chạy quá tốc độ">Chạy quá tốc độ</option>
            <option value="Đi sai làn đường">Đi sai làn đường</option>
            <option value="Không đội mũ bảo hiểm">Không đội mũ bảo hiểm</option>
          </select>

          <select 
            value={filterStatus} 
            onChange={(e) => { setFilterStatus(e.target.value); setPage(1); }}
            className="filter-select"
          >
            <option value="">-- Trạng thái lập hồ sơ --</option>
            <option value="false">Đang chờ duyệt</option>
            <option value="true">Đã lập biên bản</option>
          </select>
        </div>

        {/* BẢNG DỮ LIỆU */}
        <div className="table-wrapper">
          <table className="modern-table">
            <thead>
              <tr>
                <th>Ảnh bằng chứng</th>
                <th>Mốc thời gian</th>
                <th>Loại vi phạm</th>
                <th>Phương tiện</th>
                <th>Biển số nhận dạng</th>
                <th>Chi tiết khác</th>
                <th>Lập hồ sơ</th>
                <th style={{ textAlign: 'center' }}>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {violations.length === 0 ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
                    Không tìm thấy bản ghi vi phạm nào trùng khớp với bộ lọc.
                  </td>
                </tr>
              ) : (
                violations.map(vp => (
                  <tr key={vp.id}>
                    <td>
                      <img 
                        src={`${API_BASE}/${vp.anh_bang_chung}`} 
                        alt="Evidence" 
                        style={{ width: 60, height: 45, objectFit: 'cover', borderRadius: 6, border: '1px solid var(--border-glass)', cursor: 'pointer' }}
                        onClick={() => setSelectedViolation(vp)}
                      />
                    </td>
                    <td>{vp.thoi_gian}</td>
                    <td>
                      <span style={{ color: layMauLoi(vp.loai_vi_pham), fontWeight: 600 }}>
                        {vp.loai_vi_pham}
                      </span>
                    </td>
                    <td style={{ textTransform: 'capitalize' }}>
                      {vp.loai_phuong_tien === "motorcycle" ? "Xe máy" : vp.loai_phuong_tien === "car" ? "Ô tô" : vp.loai_phuong_tien === "truck" ? "Xe tải" : vp.loai_phuong_tien === "bus" ? "Xe buýt" : vp.loai_phuong_tien}
                    </td>
                    <td>
                      <span className="alert-plate" style={{ fontSize: '0.8rem' }}>{vp.bien_so}</span>
                    </td>
                    <td>
                      {vp.toc_do_do_duoc ? (
                        <span style={{ color: 'var(--color-red)', fontWeight: 'bold' }}>{intVal(vp.toc_do_do_duoc)} km/h</span>
                      ) : (
                        <span style={{ color: '#475569' }}>-</span>
                      )}
                    </td>
                    <td>
                      <span className={`badge-status ${vp.da_xu_ly ? 'processed' : 'pending'}`}>
                        {vp.da_xu_ly ? "Đã lập biên bản" : "Đang chờ duyệt"}
                      </span>
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <div style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem' }}>
                        <button className="btn-icon" onClick={() => setSelectedViolation(vp)} title="Xem chi tiết">
                          <Eye size={16} />
                        </button>
                        {!vp.da_xu_ly && (
                          <button 
                            className="btn-primary" 
                            style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                            onClick={() => handleMarkProcessed(vp.id)}
                          >
                            Duyệt phạt
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* PHÂN TRANG */}
        <div className="pagination-footer">
          <span>Tổng số: {totalViolations} bản ghi vi phạm</span>
          <div className="pagination-btn-group">
            <button 
              className="pagination-btn" 
              onClick={() => setPage(prev => Math.max(prev - 1, 1))}
              disabled={page === 1}
            >
              Trang trước
            </button>
            <span style={{ alignSelf: 'center', margin: '0 0.5rem', color: '#cbd5e1' }}>Trang {page} / {Math.ceil(totalViolations / limit) || 1}</span>
            <button 
              className="pagination-btn" 
              onClick={() => setPage(prev => (prev * limit < totalViolations ? prev + 1 : prev))}
              disabled={page * limit >= totalViolations}
            >
              Trang sau
            </button>
          </div>
        </div>
      </div>

      {/* DETAIL MODAL OVERLAY */}
      {selectedViolation && (
        <div className="modal-overlay" onClick={() => setSelectedViolation(null)}>
          <div className="glass-panel modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="card-title">
              <div className="card-title-text">
                <AlertTriangle size={20} color={layMauLoi(selectedViolation.loai_vi_pham)} />
                <span>Chi tiết hồ sơ vi phạm #{selectedViolation.id}</span>
              </div>
              <button className="btn-icon" style={{ fontSize: '1.25rem' }} onClick={() => setSelectedViolation(null)}>×</button>
            </div>
            
            <div className="modal-body">
              {/* Bên trái: Ảnh bằng chứng */}
              <div className="modal-img-container">
                <div>
                  <label style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600, display: 'block', marginBottom: '0.25rem' }}>Hình ảnh bằng chứng (Chụp bởi AI Camera)</label>
                  <img 
                    src={`${API_BASE}/${selectedViolation.anh_bang_chung}`} 
                    alt="Main Proof" 
                    className="modal-main-img"
                  />
                </div>
                {selectedViolation.bien_so_crop && (
                  <div>
                    <label style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600, display: 'block', marginBottom: '0.25rem' }}>Vùng biển số được trích xuất (OCR)</label>
                    <img 
                      src={`${API_BASE}/${selectedViolation.bien_so_crop}`} 
                      alt="Plate Proof" 
                      className="modal-plate-img"
                    />
                  </div>
                )}
              </div>
              
              {/* Bên phải: Thông tin */}
              <div className="modal-info-list">
                <div className="info-item">
                  <label>Loại lỗi vi phạm</label>
                  <p className="large-value" style={{ color: layMauLoi(selectedViolation.loai_vi_pham) }}>{selectedViolation.loai_vi_pham}</p>
                </div>
                
                <div className="info-item">
                  <label>Thời gian ghi nhận</label>
                  <p>{selectedViolation.thoi_gian}</p>
                </div>
                
                <div className="info-item">
                  <label>Loại phương tiện</label>
                  <p style={{ textTransform: 'capitalize' }}>
                    {selectedViolation.loai_phuong_tien === "motorcycle" ? "Xe máy" : selectedViolation.loai_phuong_tien === "car" ? "Ô tô" : selectedViolation.loai_phuong_tien === "truck" ? "Xe tải" : selectedViolation.loai_phuong_tien === "bus" ? "Xe buýt" : selectedViolation.loai_phuong_tien}
                  </p>
                </div>
                
                <div className="info-item">
                  <label>Biển số xe trích xuất</label>
                  <div>
                    <span className="alert-plate" style={{ fontSize: '1.1rem', padding: '0.25rem 0.6rem', display: 'inline-block', marginTop: '0.25rem' }}>
                      {selectedViolation.bien_so}
                    </span>
                  </div>
                </div>

                {selectedViolation.toc_do_do_duoc && (
                  <div className="info-item">
                    <label>Vận tốc đo được</label>
                    <p style={{ color: 'var(--color-red)', fontWeight: 'bold' }}>{intVal(selectedViolation.toc_do_do_duoc)} km/h</p>
                  </div>
                )}
                
                <div className="info-item">
                  <label>Trạng thái hồ sơ phạt</label>
                  <div style={{ marginTop: '0.25rem' }}>
                    <span className={`badge-status ${selectedViolation.da_xu_ly ? 'processed' : 'pending'}`} style={{ fontSize: '0.85rem' }}>
                      {selectedViolation.da_xu_ly ? "Đã lập biên bản phạt" : "Đang chờ duyệt hồ sơ"}
                    </span>
                  </div>
                </div>
                
                <div style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem' }}>
                  {!selectedViolation.da_xu_ly && (
                    <button 
                      className="btn-primary" 
                      onClick={() => handleMarkProcessed(selectedViolation.id)}
                      style={{ flex: 1, padding: '0.75rem', fontSize: '0.9rem' }}
                    >
                      Duyệt phạt & Gửi thông báo
                    </button>
                  )}
                  <button 
                    className="pagination-btn" 
                    onClick={() => setSelectedViolation(null)}
                    style={{ flex: selectedViolation.da_xu_ly ? 1 : 0.5 }}
                  >
                    Đóng
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Hàm format tốc độ
function intVal(val) {
  return Math.round(val);
}

export default App;
