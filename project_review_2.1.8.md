# ABAS v2 — Đánh giá Dự án Toàn diện

> **Ngày đánh giá:** 11/06/2026  
> **Người đánh giá:** AI Agent (Antigravity)  
> **Phạm vi:** Kiểm toán toàn bộ dự án — kiến trúc, chất lượng mã nguồn, mức độ tuân thủ đặc tả (spec), lỗi (bugs), bảo mật, độ bao phủ kiểm thử (test coverage)

---

## Tóm tắt điều hành (Executive Summary)

Dự án ABAS v2 đang ở trạng thái **ổn định và hoạt động tốt**. Tất cả **8 giai đoạn phát triển** (Giai đoạn 0–7) được đánh dấu hoàn thành, toàn bộ **53 unit test đều vượt qua** trong 4.37 giây, và cơ sở mã nguồn được tổ chức tốt với sự phân chia trách nhiệm rõ ràng. Tài liệu đặc tả hệ thống ([ABAS_PLAN_v2.md](ABAS_PLAN_v2.md)) rất toàn diện và phần triển khai thực tế bám sát đặc tả này ở hầu hết các điểm quan trọng.

Tuy nhiên, đợt đánh giá này đã phát hiện **một số điểm thiếu sót, lỗi tiềm ẩn và cơ hội cải tiến** cần được giải quyết trước khi triển khai hệ thống với nguồn vốn thực tế.

---

## 1. Sự Tuân thủ Kiến trúc (Architecture Conformance) ✅

Cơ sở mã nguồn tuân thủ chặt chẽ theo kiến trúc đã được quy định:

```
Data (Dữ liệu) → Features (Tính năng) → Regime (Trạng thái) → Inventory (Kho hàng) → Grid (Lưới) → Risk (Rủi ro) → Execution (Thực thi) → Portfolio (Danh mục) → Monitoring (Giám sát)
```

| Thành phần | File liên quan | Trạng thái |
|---|---|---|
| Thu thập Dữ liệu (Data Ingestion) | [ingester.py](src/data/ingester.py), [validators.py](src/data/validators.py) | ✅ Hoàn thành |
| Động cơ Tính năng (Feature Engine) | [engine.py](src/features/engine.py) | ✅ Hoàn thành |
| Phát hiện Trạng thái (Regime Detection) | [hmm.py](src/regime/hmm.py), [kmeans.py](src/regime/kmeans.py), [bocpd.py](src/regime/bocpd.py), [classifier.py](src/regime/classifier.py) | ✅ Hoàn thành |
| Kho hàng/FIFO (Inventory/FIFO) | [ledger.py](src/inventory/ledger.py), [models.py](src/inventory/models.py) | ✅ Hoàn thành |
| Động cơ Lưới (Grid Engine) | [engine.py](src/grid/engine.py) | ✅ Hoàn thành |
| Lớp Kiểm soát Rủi ro (Risk Overlay) | [overlay.py](src/risk/overlay.py) | ✅ Hoàn thành |
| Thực thi Giao dịch (Execution) | [orchestrator.py](src/execution/orchestrator.py), [ccxt_mock.py](src/execution/ccxt_mock.py), [paper.py](src/execution/paper.py), [live_ws.py](src/execution/live_ws.py) | ✅ Hoàn thành |
| Danh mục Đầu tư (Portfolio) | [tracker.py](src/portfolio/tracker.py), [reconcile_audit.py](src/portfolio/reconcile_audit.py) | ✅ Hoàn thành |
| Lưu ký (Custody) | [sweeper.py](src/custody/sweeper.py) | ✅ Hoàn thành |
| Giám sát (Monitoring) | [exporter.py](src/monitoring/exporter.py) | ✅ Hoàn thành |
| Trung lập Delta (Delta-Neutral) | [delta_neutral.py](src/execution/delta_neutral.py) | ✅ Hoàn thành |

---

## 2. Kiểm toán mức độ Tuân thủ Đặc tả (Spec Conformance Audit)

### ✅ Đã triển khai đúng

| Mục đặc tả | Phần triển khai trong mã nguồn |
|---|---|
| INV-1: Core BTC monotonic non-decreasing (BTC cốt lõi không giảm đơn điệu) | [overlay.py:L86-89](src/risk/overlay.py#L86-L89) |
| INV-2: Reserve floor enforcement (Áp dụng mức sàn dự trữ) | [overlay.py:L91-97](src/risk/overlay.py#L91-L97) |
| INV-3: Portfolio sum conservation (epsilon) (Bảo toàn tổng danh mục đầu tư) | [overlay.py:L99-119](src/risk/overlay.py#L99-L119) |
| INV-5: Sell gating against FIFO head lot cost (Rào cản bán so với giá vốn lô FIFO đầu tiên) | [overlay.py:L76-81](src/risk/overlay.py#L76-L81), [engine.py:L96-99](src/grid/engine.py#L96-L99) |
| INV-5 Ngoại lệ 180 ngày | [overlay.py:L78](src/risk/overlay.py#L78), [engine.py:L97](src/grid/engine.py#L97) |
| INV-6: Daily deployment cap (Giới hạn giải ngân hàng ngày) | [overlay.py:L122-127](src/risk/overlay.py#L122-L127) |
| INV-7: Hot exchange cap (Giới hạn trên sàn giao dịch nóng) | [overlay.py:L129-136](src/risk/overlay.py#L129-L136) |
| Accumulation Guard (Chốt bảo vệ tích lũy) | [engine.py:L126-128](src/grid/engine.py#L126-L128) |
| 30/70 P&L split (Phân chia lợi nhuận P&L tỷ lệ 30/70) | [ledger.py:L182-199](src/inventory/ledger.py#L182-L199) |
| A_local_low dynamic anchoring (Neo động đáy cục bộ) | [orchestrator.py:L234-246](src/execution/orchestrator.py#L234-L246) |
| Hysteresis filtering (Lọc trễ - 3 tick liên tiếp hoặc độ tin cậy > 0.95) | [classifier.py:L221-239](src/regime/classifier.py#L221-L239) |
| FIFO tax export CSV (Xuất file CSV báo cáo thuế FIFO) | [ledger.py:L241-265](src/inventory/ledger.py#L241-L265) |
| Công tắc ngắt khẩn cấp (Halt/Kill switches) (Tất cả 8 tác nhân kích hoạt) | [overlay.py:L141-194](src/risk/overlay.py#L141-L194) |

### ⚠️ Các sai lệch & Thiếu sót so với Đặc tả

| # | Vấn đề | Đặc tả tham chiếu | Vị trí mã nguồn | Mức độ |
|---|---|---|---|---|
| 1 | **Hệ số nhân mua trong thị trường gấu là 0.4, đặc tả yêu cầu 1.0–1.2** | ABAS_PLAN_v2.md L282 | [engine.py:L64](src/grid/engine.py#L64) | 🔴 Cao |
| 2 | **Hệ số nhân bán trong thị trường gấu là 0.8, đặc tả yêu cầu 0.3–0.5** | ABAS_PLAN_v2.md L320 | [engine.py:L120](src/grid/engine.py#L120) | 🔴 Cao |
| 3 | **Hệ số nhân mua khi hoảng loạn (panic dump) là 1.5, đặc tả yêu cầu 1.5–2.0** | ABAS_PLAN_v2.md L279 | [engine.py:L60](src/grid/engine.py#L60) — mức tối thiểu an toàn, chấp nhận được | 🟡 Thấp |
| 4 | **Thiếu công tắc ngắt khẩn cấp: Funding rate > 0.3%/8h** | ABAS_PLAN_v2.md L536 | Chưa được triển khai trong [overlay.py](src/risk/overlay.py) | 🟡 Trung bình |
| 5 | **Thiếu tính năng tự động khôi phục công tắc ngắt sau 30 phút** | ABAS_PLAN_v2.md L541 | Hiện tại `system_halted` là vĩnh viễn cho đến khi được thay đổi thủ công | 🟡 Trung bình |
| 6 | **Thiếu tính năng theo dõi kích hoạt kép ngắt khẩn cấp để yêu cầu khôi phục thủ công sau 24h** | ABAS_PLAN_v2.md L542 | Chưa được theo dõi | 🟡 Trung bình |
| 7 | **Chưa triển khai hết hạn chu kỳ bán sau 48h** | ABAS_PLAN_v2.md L292 | `anchored_local_low` không bao giờ tự động reset sau 48h nếu không có lệnh bán | 🟡 Trung bình |
| 8 | **Quét lưu ký (Custody sweep) sử dụng quy tắc nghiêm ngặt 7/7 ngày liên tiếp, đặc tả cho phép cả 5 trên 7 ngày** | ABAS_PLAN_v2.md L326 | [sweeper.py:L36-49](src/custody/sweeper.py#L36-L49) — nghiêm ngặt hơn thì an toàn hơn | 🟢 Thông tin |
| 9 | **Thiếu cấu hình `delta_neutral_enabled` trong production.json** | [config.py:L26](src/config.py#L26) | [production.json](config/production.json) — đang để mặc định là `False` trong code, chấp nhận được | 🟢 Thông tin |
| 10 | **Phiên bản trong `pyproject.toml` là `2.0.0`, nên cập nhật thành `2.1.8`** | CHANGELOG.md L10 | [pyproject.toml:L7](pyproject.toml#L7) | 🟡 Thấp |

---

## 3. Lỗi & Vấn đề Chất lượng Mã nguồn (Bugs & Code Quality Issues)

### 🔴 Nghiêm trọng (Critical)

| # | Vấn đề | File | Dòng | Mô tả |
|---|---|---|---|---|
| B1 | **Trả về từ hàm `float()` không được sử dụng** | [orchestrator.py](src/execution/orchestrator.py#L109) | L109 | Kết quả của `float(features["sigma_ann"])` bị bỏ qua — có khả năng là dòng code debug còn sót lại. |
| B2 | **Trả về từ hàm `float()` không được sử dụng trong bộ phân loại** | [classifier.py](src/regime/classifier.py#L198) | L198 | Kết quả của `float(latest_features["close"])` bị bỏ qua. |
| B3 | **Gọi `np.random.seed()` trong hàm khởi tạo lớp ảnh hưởng toàn cục** | [hmm.py](src/regime/hmm.py#L13) | L13 | Thiết lập `np.random.seed()` trong `__init__` sẽ ảnh hưởng đến trạng thái RNG NumPy toàn cục, có thể gây ra lỗi tái lập kiểm thử ngầm và ảnh hưởng đến các mô-đun khác. Nên sử dụng `np.random.RandomState` hoặc `np.random.default_rng`. |
| B4 | **Rò rỉ bộ nhớ BOCPD do mảng tăng trưởng vô hạn** | [bocpd.py](src/regime/bocpd.py#L33-L77) | L33-77 | Mỗi lệnh gọi `update()` sẽ thêm phần tử vào các mảng `mu_t`, `kappa_t`, `alpha_t`, `beta_t`, `R` — tăng tuyến tính theo số lượng tick. Chạy thực tế trong nhiều tuần/tháng sẽ gây ngốn bộ nhớ lớn. Cần cắt bớt các độ dài cũ. |

### 🟡 Trung bình (Medium)

| # | Vấn đề | File | Dòng | Mô tả |
|---|---|---|---|---|
| B5 | **`FeatureEngine.compute_latest_features` truy vấn dữ liệu 1 phút cho các cột `funding_rate`/`open_interest`/`liquidations` vốn không tồn tại trong truy vấn 1m** | [engine.py](src/features/engine.py#L283-L285) | L283-285 | Truy vấn SQL 1m chỉ lấy `time, open, high, low, close, volume` — vì vậy kiểm tra `'funding_rate' in df_1m.columns` luôn trả về `False`. Các tính năng như `funding_rate_delta_24h` luôn mặc định là 0.0 ở chế độ trực tuyến (online mode). |
| B6 | **`CustodySweeper.__init__` bỏ qua tham số khởi tạo** | [sweeper.py](src/custody/sweeper.py#L13-L15) | L13-15 | Hàm khởi tạo nhận tham số `trading_target` và `promotion_threshold_multiplier` nhưng lại ghi đè chúng bằng `settings.trading_target` và `settings.promotion_threshold`. |
| B7 | **Rò rỉ kết nối DB tiềm ẩn trong `save_raw_ohlcv_to_db`** | [orchestrator.py](src/execution/orchestrator.py#L414-L463) | L414-463 | Nếu `conn.commit()` thành công nhưng xảy ra ngoại lệ ở câu lệnh tiếp theo, `release_connection` vẫn được kích hoạt (tốt), nhưng nếu bản thân `get_connection()` ném ra lỗi, `conn` sẽ là `None` và việc gọi `release_connection(None)` có thể bị lỗi. |
| B8 | **Thiếu kiểm tra trước INV-4 trong Grid Engine** | Đặc tả yêu cầu Grid Engine phải tự động loại bỏ các lệnh vi phạm INV-1/INV-2 (INV-4). Hiện tại Orchestrator chỉ thực hiện kiểm tra trước một phần (L222-227) nhưng bản thân Grid Engine không thực thi INV-4. | 🟡 |
| B9 | **Thiếu thư viện `aiohttp` trong danh sách phụ thuộc** | [pyproject.toml](pyproject.toml) | — | File [live_ws.py](src/execution/live_ws.py) import `aiohttp` nhưng thư viện này không được liệt kê trong phần dependencies của `pyproject.toml`. |

### 🟢 Nhỏ / Phong cách viết mã (Minor / Style)

| # | Vấn đề | File | Mô tả |
|---|---|---|---|
| B10 | Cách ghi log chưa thống nhất: một số mô-đun dùng `get_agent_logger()`, số khác lại dùng `logging.getLogger()` | [engine.py (grid)](src/grid/engine.py#L4), [engine.py (features)](src/features/engine.py#L10), [models.py](src/inventory/models.py#L6) | Nên thống nhất sử dụng `get_agent_logger()` để ghi nhật ký dạng JSON có cấu trúc nhằm bảo vệ thông tin nhạy cảm. |
| B11 | Sử dụng trực tiếp `import os` trong [delta_neutral.py](src/execution/delta_neutral.py#L1) — nên cân nhắc chuyển sang `pathlib.Path` để đồng bộ. | | |
| B12 | Tiện ích `db.py` chưa được xem xét kỹ (không nằm trong danh sách thư mục nhưng được import) — cần đảm bảo quản lý connection pooling hoạt động tốt cho các tiến trình chạy lâu dài. | | |

---

## 4. Đánh giá độ bao phủ kiểm thử (Test Coverage Assessment)

### ✅ Bộ kiểm thử hiện tại: 53 tests, toàn bộ đều đạt

| File test | Số lượng | Vùng kiểm thử |
|---|---|---|
| [test_audit.py](tests/test_audit.py) | 2 | Trạng thái đạt/không đạt của kiểm toán sổ cái |
| [test_backtest.py](tests/test_backtest.py) | 1 | Khung kiểm thử lịch sử (Backtest) |
| [test_benchmarks.py](tests/test_benchmarks.py) | 1 | So sánh hệ thống với Benchmark |
| [test_config.py](tests/test_config.py) | 3 | Tải cấu hình, ghi đè biến môi trường, lọc log nhạy cảm |
| [test_custody.py](tests/test_custody.py) | 4 | Logic kích hoạt lệnh quét lưu ký |
| [test_data.py](tests/test_data.py) | 3 | Xác thực lược đồ dữ liệu, khoảng trống dữ liệu, và ngoại lệ |
| [test_delta_neutral.py](tests/test_delta_neutral.py) | 2 | Động cơ trung lập Delta + Tích hợp Orchestrator |
| [test_features.py](tests/test_features.py) | 1 | Các phép tính toán tính năng dữ liệu |
| [test_grid.py](tests/test_grid.py) | 3 | Khoảng cách lưới, định lượng quy mô mua/bán |
| [test_inventory.py](tests/test_inventory.py) | 3 | FIFO mua/bán, bảo toàn tổng lượng theo Hypothesis, khôi phục DB |
| [test_monitoring.py](tests/test_monitoring.py) | 2 | Trình thông báo Telegram |
| [test_orchestrator.py](tests/test_orchestrator.py) | 1 | Chu kỳ tick đầy đủ |
| [test_paper.py](tests/test_paper.py) | 3 | Client kết nối WS, thực thi paper trading, kiểm toán bảo mật |
| [test_portfolio.py](tests/test_portfolio.py) | 3 | Đối chiếu số dư thành công/thất bại, giám sát rủi ro danh mục |
| [test_regime.py](tests/test_regime.py) | 4 | HMM, KMeans, BOCPD, bộ lọc trễ (hysteresis) |
| [test_risk.py](tests/test_risk.py) | 9 | Toàn bộ 7 invariant rủi ro, các công tắc ngắt khẩn cấp, rào cản mềm |
| [test_rl.py](tests/test_rl.py) | 3 | Môi trường Gym, tác nhân RL, đánh giá PBO |
| [test_simulator.py](tests/test_simulator.py) | 2 | Trình mô phỏng GBM, trình tạo dữ liệu MSAR |
| [test_run_simulations.py](tests/test_run_simulations.py) | 1 | Tính nhất quán của backtest |
| [test_download_data.py](tests/test_download_data.py) | 1 | Tải dữ liệu lịch sử |

### ⚠️ Vùng kiểm thử còn thiếu (Missing Test Coverage)

| Khoảng trống | Mô tả | Mức độ ưu tiên |
|---|---|---|
| **Chưa có kiểm thử tích hợp cho phân chia lợi nhuận P&L tỷ lệ 30/70** | Logic `consume_sell_lots` tương đối phức tạp — cần các ca kiểm thử xác minh việc phân bổ 30/70, cơ chế ghi đè khi thiếu hụt dự trữ, và các trường hợp biên (P&L âm, doanh thu bằng 0). | 🔴 Cao |
| **Chưa có kiểm thử cho Accumulation Guard** | Việc theo dõi `net_btc_accumulated_current_cycle` trong orchestrator + giới hạn trần trong GridEngine chưa được kiểm thử end-to-end. | 🔴 Cao |
| **Chưa có kiểm thử cho trường hợp ngoại lệ bán sau 180 ngày** | Cả GridEngine và RiskOverlay đều cho phép bán khi `fifo_head_age_days > 180` ngay cả khi dưới giá vốn — nhưng chưa có kiểm thử nào kích hoạt nhánh logic này. | 🟡 Trung bình |
| **Thiếu kiểm thử hỗn loạn (chaos/adversarial tests)** | Đặc tả yêu cầu kiểm thử trong điều kiện khắc nghiệt (ngắt kết nối sàn giao dịch, khớp lệnh một phần, mất dữ liệu). Hiện bộ test chỉ giả lập trong điều kiện tối ưu. | 🟡 Trung bình |
| **Chưa có kiểm thử cho chu kỳ neo/reset của `A_local_low`** | Logic phát hiện giá phục hồi → neo đáy → bán → reset đáy trong orchestrator rất phức tạp nhưng chưa được kiểm thử. | 🟡 Trung bình |

---

## 5. Đánh giá Bảo mật (Security Assessment)

| Lĩnh vực | Trạng thái | Ghi chú |
|---|---|---|
| Ẩn thông tin nhạy cảm | ✅ | Lớp lọc [RedactorFilter](src/utils/logging.py#L7-L42) hoạt động tốt trên API keys, mật khẩu DB, Telegram token. |
| Kiểm toán quyền API key | ✅ | [BinancePaper.audit_api_permissions()](src/execution/paper.py#L47-L63) kiểm tra và đảm bảo quyền rút tiền bị vô hiệu hóa. |
| Không để lộ bí mật trong mã nguồn | ✅ | File cấu hình production.json để trống chuỗi thông tin xác thực; file `.env` đã nằm trong `.gitignore`. |
| Mật khẩu DB trong cấu hình | ⚠️ | File [production.json:L2](config/production.json#L2) để mặc định là `postgrespassword` — chấp nhận được với môi trường phát triển (dev), cần đảm bảo ghi đè bằng biến môi trường ở production. |
| Sổ cái Delta-neutral lưu trữ dưới dạng JSON văn bản thường | ⚠️ | [delta_neutral.py:L18](src/execution/delta_neutral.py#L18) — file `data/delta_neutral_ledger.json` lưu cục bộ. Không quá nghiêm trọng nhưng lưu trữ trong DB sẽ an toàn và đồng bộ tốt hơn. |

---

## 6. Hiệu năng & Vận hành (Performance & Operational Concerns)

| # | Vấn đề | Tác động | Khuyến nghị |
|---|---|---|---|
| P1 | **Rò rỉ bộ nhớ BOCPD** | Gây crash ứng dụng sau nhiều tuần hoạt động liên tục | Cắt bớt mảng phân phối xác suất xuống tối đa khoảng 500 bản ghi mỗi lần cập nhật |
| P2 | **Tạo kết nối DB cho mỗi thao tác nhỏ** | Mỗi lần gọi `save_lot`, `save_portfolio_state`,... đều phải yêu cầu và giải phóng kết nối | Nhóm các thao tác ghi DB lại theo từng tick — sử dụng chung một kết nối cho toàn bộ vòng đời của tick đó |
| P3 | **Bộ phân loại trạng thái phải huấn luyện lại mỗi lần khởi động nếu chưa fit** | [classifier.py:L194-195](src/regime/classifier.py#L194-L195) — khiến tick đầu tiên bị chậm và yêu cầu truy cập DB | Thêm cơ chế tuần tự hóa mô hình (pickle/joblib) để lưu trữ mô hình đã huấn luyện |
| P4 | **FeatureEngine chế độ trực tuyến phát nhiều truy vấn SQL riêng biệt** | Gửi 3 truy vấn riêng lẻ mỗi tick (daily, 4h, 1m) | Nên tối ưu hóa bằng cách gom truy vấn hoặc dùng materialized view |
| P5 | **Thời gian chờ mỗi tick của Orchestrator được code cứng 60s** | [orchestrator.py:L500](src/execution/orchestrator.py#L500) | Chuyển cấu hình này vào file cài đặt (settings) |

---

## 7. Tóm tắt Chất lượng Mã nguồn (Code Quality Summary)

| Khía cạnh | Đánh giá | Ghi chú |
|---|---|---|
| **Cấu trúc thư mục** | ⭐⭐⭐⭐⭐ | Phân chia mô-đun rõ ràng, tuân thủ chính xác kiến trúc đặc tả |
| **Tài liệu hướng dẫn** | ⭐⭐⭐⭐ | Docstring rõ ràng, lưu trữ CHANGELOG và TASK.md đầy đủ |
| **Độ an toàn kiểu dữ liệu** | ⭐⭐⭐ | Sử dụng Pydantic cho config và MarketTick, nhưng nhiều hàm vẫn dùng dict thô |
| **Xử lý ngoại lệ** | ⭐⭐⭐⭐ | Đóng gói try/catch đầy đủ và phân cấp ngoại lệ tốt |
| **Chất lượng kiểm thử** | ⭐⭐⭐⭐ | Độ bao phủ tốt với các bài kiểm thử thuộc tính Hypothesis; còn một số khoảng trống |
| **Ghi nhật ký (Logging)** | ⭐⭐⭐ | Chưa đồng bộ hoàn toàn giữa ghi log dạng cấu trúc và log mặc định của stdlib |
| **Thư viện phụ thuộc** | ⭐⭐⭐⭐ | Tối giản, chọn lọc kỹ; thiếu khai báo `aiohttp` trong manifest (B9) |

---

## 8. Các Hành động Ưu tiên Khuyến nghị (Recommended Priority Actions)

### 🔴 Trước khi Vận hành Thực tế (Before Live Deployment)

1. **Sửa các hệ số nhân thị trường gấu** (Sai lệch đặc tả #1, #2) — sửa hệ số mua `0.4` thành `1.0–1.2` và hệ số bán `0.8` thành `0.3–0.5`. Thay đổi này cực kỳ quan trọng để đảm bảo hành vi chính xác của hệ thống trong thị trường gấu.
2. **Khắc phục lỗi rò rỉ bộ nhớ BOCPD** (B4) — thêm cơ chế cắt bớt mảng độ dài chuỗi để tránh lỗi hết bộ nhớ (OOM).
3. **Thêm thư viện phụ thuộc `aiohttp`** (B9) — tránh lỗi cài đặt mới không thể chạy chế độ paper trading.
4. **Viết thêm kiểm thử tích hợp cho cơ chế phân chia lợi nhuận 30/70 P&L** — xác minh đường đi logic quan trọng nhất về mặt tài chính.
5. **Viết thêm kiểm thử tích hợp cho Accumulation Guard** — đảm bảo cơ chế giới hạn trần mua BTC hoạt động đúng.

### 🟡 Trước khi Mở rộng Nguồn vốn (Before Scaling Capital)

6. **Triển khai công tắc ngắt khẩn cấp dựa trên tỷ lệ tài trợ (funding rate)** (Sai lệch đặc tả #4) — tạm dừng mua mạnh khi `funding_rate > 0.3%/8h`.
7. **Triển khai thời gian hết hạn 48h cho chu kỳ bán** (Sai lệch đặc tả #7) — tự động đặt lại `anchored_local_low`.
8. **Triển khai tự động khôi phục công tắc ngắt** (Sai lệch đặc tả #5, #6) — thêm thời gian chờ 30 phút và theo dõi kích hoạt kép.
9. **Viết thêm các bài kiểm thử hỗn loạn (chaos tests)** — giả lập sự cố kết nối sàn, khớp lệnh một phần và mất dữ liệu.
10. **Chuẩn hóa ghi nhật ký** (B10) — sử dụng `get_agent_logger()` đồng bộ trên toàn bộ dự án.

### 🟢 Khuyến khích Thực hiện (Nice to Have)

11. Sửa phiên bản trong `pyproject.toml` đồng bộ với CHANGELOG (v2.1.8).
12. Lưu trữ mô hình `RegimeClassifier` sau khi huấn luyện.
13. Tối ưu hóa số lượng truy cập DB (ghi hàng loạt mỗi tick).
14. Thêm biến cấu hình `delta_neutral_enabled` vào `production.json`.
15. Dọn dẹp các lời gọi hàm `float()` thừa (B1, B2).

---

## 9. Kết luận (Verdict)

> [!IMPORTANT]
> Dự án **hoàn thiện về mặt kiến trúc** và **đầy đủ về mặt chức năng** trên cả 8 giai đoạn phát triển. Các logic giao dịch cốt lõi, sổ cái FIFO, lớp kiểm soát rủi ro và các bất biến rủi ro (invariants) đều được triển khai tốt và kiểm thử tương đối đầy đủ.
>
> **Tuy nhiên**, sự sai lệch về hệ số nhân trong thị trường gấu (#1, #2) và lỗi rò rỉ bộ nhớ của BOCPD (#B4) là **những rào cản lớn buộc phải giải quyết trước khi vận hành thực tế**. Các vấn đề thiếu công tắc ngắt khẩn cấp và thiếu kiểm thử tích hợp cũng cần được bổ sung sớm để đảm bảo hệ thống sẵn sàng chạy sản xuất an toàn.

| Khía cạnh đánh giá | Kết luận |
|---|---|
| **Sẵn sàng để chạy thử lịch sử (backtest) / paper trading?** | ✅ Sẵn sàng |
| **Sẵn sàng triển khai với nguồn vốn nhỏ?** | ⚠️ Chỉ sau khi khắc phục xong các mục từ 1 đến 5 ở trên |
| **Sẵn sàng triển khai với nguồn vốn lớn?** | ❌ Chỉ sau khi khắc phục xong các mục từ 1 đến 10 ở trên |
