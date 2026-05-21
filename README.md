# Hệ thống Tích lũy BTC Thích ứng (ABAS) — Phiên bản v2

ABAS là một công cụ tích lũy Bitcoin (BTC) dài hạn được thiết kế để tối đa hóa số lượng BTC nắm giữ qua nhiều chu kỳ thị trường. Khác với các robot giao dịch truyền thống tối ưu hóa lợi nhuận theo USD, ABAS được xây dựng để vượt trội hơn chiến lược nắm giữ thụ động (HODL) tính theo BTC, sau khi trừ đi tất cả các khoản phí và thuế, bằng cách khai thác độ biến động của thị trường và quản lý kho tài sản một cách linh hoạt.

## Mục lục
1. [Triết lý Cốt lõi](#1-triết-lý-cốt-lõi)
2. [Ý tưởng Chiến lược](#2-ý-tưởng-chiến-lược)
3. [Kiến trúc Hệ thống](#3-kiến-trúc-hệ-thống)
4. [Công nghệ Sử dụng (Tech Stack)](#4-công-nghệ-sử-dụng-tech-stack)
5. [Cơ cấu Danh mục & Lưu ký](#5-cơ-cấu-danh-mục--lưu-ký)
6. [Các Quy tắc Bất biến Enforced](#6-các-quy-tắc-bất-biến-enforced)
7. [Cấu trúc Thư mục](#7-cấu-trúc-thư-mục)
8. [Hướng dẫn Khởi đầu](#8-hướng-dẫn-khởi-đầu)
9. [Lộ trình Phát triển](#9-lộ-trình-phát-triển)
10. [Kiểm thử & Xác thực](#10-kiểm-thử--xác-thực)
11. [Giấy phép](#11-giấy-phép)

---

## 1. Triết lý Cốt lõi

Hệ thống tối ưu hóa cho mục tiêu sau:
$$\max \text{BTC}_t \quad \text{ràng buộc bởi } \text{Quy tắc Bất biến}$$

*   **BTC** là tài sản dự trữ chính, nơi lưu trữ giá trị dài hạn và là kho hàng chiến lược.
*   **USDT/USDC/DAI** được đối xử đơn thuần như đạn dược thanh khoản, quỹ dự trữ và công cụ rebalance.

---

## 2. Ý tưởng Chiến lược

ABAS thực hiện mô hình khai thác biến động được thiết kế riêng cho các đặc tính thị trường độc đáo của Bitcoin:
1.  **Mua khi hoảng loạn (Buy Fear):** Tích lũy BTC khi giá sụt giảm sâu so với các mốc neo di động (anchors).
2.  **Bán một phần khi hồi phục (Sell Partial Rebounds):** Bán từng phần nhỏ của kho giao dịch khi giá hồi phục, đảm bảo mọi lệnh bán đều được chốt chặn bởi ngưỡng lợi nhuận tối thiểu so với giá vốn cụ thể của lô đó (áp dụng FIFO theo dõi lô).
3.  **Tái mua ở mức chiết khấu sâu hơn (Rebuy Deeper):** Sử dụng lượng stablecoin dự trữ thu hoạch được để mua lại ở mức giá thấp hơn.
4.  **Chuyển vào giỏ Lõi (Promote to Core):** Tự động chuyển lượng BTC giao dịch dư thừa vào giỏ Lõi (rút về ví lạnh) khi số dư giao dịch vượt mục tiêu duy trì.

### Mốc neo tham chiếu (Reference Anchors)
Mọi ngưỡng quyết định giao dịch được tính toán động dựa trên các mốc neo:
*   $A_{\text{trend}}$: EMA(200, daily) — Bộ lọc xu hướng vĩ mô.
*   $A_{\text{range}}$: Rolling max(high, 30d) — Kích hoạt sụt giảm từ đỉnh.
*   $A_{\text{vol}}$: ATR(14) / Price — Chỉ báo khoảng cách lưới thích ứng.
*   $A_{\text{cost}}$: Giá vốn trung bình theo lô FIFO — Chốt chặn kiểm tra điều kiện bán.
*   $A_{\text{mean}}$: EMA(20, 4h) — Mốc neo hồi quy trung bình (mean-reversion).

---

## 3. Kiến trúc Hệ thống

ABAS được thiết kế như một hệ thống đa tác tử (multi-agent). Thông tin luân chuyển tuần tự từ các kênh nạp dữ liệu thị trường thô, qua các bước phân tích, tính toán lưới lệnh, kiểm tra rào cản rủi ro trước khi đưa đến sàn giao dịch.

```mermaid
graph TD
    subgraph Lớp Dữ liệu (Data Layer)
        A[Binance WS / CCXT Feed] -->|Dữ liệu thô| B[Data Ingestion & Validation Agent]
        B -->|Nến/Tick sạch| C[Feature Engineering Agent]
    end

    subgraph Lớp Trí tuệ (Intelligence Layer)
        C -->|Đặc trưng| D[Market Regime Detection Agent]
        C -->|Mốc neo Anchors| E[Adaptive Grid Agent]
        D -->|Trạng thái & Độ tin cậy| E
        F[Inventory & Cost-Basis Agent] -->|Giá vốn Avg Cost| E
    end

    subgraph Lớp Kiểm soát & Rủi ro (Risk Layer)
        E -->|Lưới lệnh đề xuất| G[Risk Overlay & Invariant Agent]
        G -->|Lệnh được phê duyệt| H[Execution Agent]
    end

    subgraph Lớp Thực thi & Giám sát (Execution & Monitoring)
        H -->|Kết quả khớp fills| I[Portfolio Tracking Agent]
        I -->|Cập nhật sổ cái| F
        I -->|Trạng thái & Cảnh báo| J[Monitoring & Alerting Agent]
    end
```

Để biết thêm chi tiết về vai trò và cơ chế phối hợp của các tác tử, vui lòng tham khảo [AGENTS.md](file:///d:/MyProject/accumulation_agent/AGENTS.md).

---

## 4. Công nghệ Sử dụng (Tech Stack)

*   **Ngôn ngữ lập trình:** Python 3.11+
*   **Cơ sở dữ liệu:** PostgreSQL + TimescaleDB (lưu trữ dữ liệu chuỗi thời gian, trạng thái sổ cái và lịch sử lệnh)
*   **Hệ thống hàng đợi & Trạng thái:** Redis (quản lý pub/sub liên tác tử và theo dõi heartbeat)
*   **API Giao dịch:** CCXT Pro (kết nối REST API và WebSocket tới Binance)
*   **Container hóa:** Docker & Docker Compose
*   **Đo lường & Cảnh báo:** Prometheus + Grafana kết hợp Telegram API

---

## 5. Cơ cấu Danh mục & Lưu ký

Hệ thống chia tài sản thành ba giỏ riêng biệt với các chính sách lưu ký nghiêm ngặt:

| Giỏ tài sản | Mục tiêu phân bổ | Mục đích | Cơ chế lưu ký |
|---|---|---|---|
| **Core BTC** | 60% — 80% | Nắm giữ dài hạn (Tuyệt đối không bán) | Ví lạnh / Ví Multisig |
| **Trading BTC** | 10% — 25% | Kho lướt sóng khai thác biến động | Ví nóng trên sàn (Binance) |
| **USDT Reserve** | 10% — 20% | Đạn dược để bắt đáy khi thị trường sụp đổ | Stablecoins đa dạng (USDT/USDC/DAI) |

### Quy tắc Lưu ký và Sweep Lệnh chuyển ví
*   Các khóa API trên sàn giao dịch chỉ được cấp quyền **Giao dịch (Trade-Only)**, khóa hoàn toàn quyền rút tiền (Withdrawal Disabled) và bắt buộc whitelist IP.
*   **Quy tắc Sweep:** Khi số dư $\text{Trading BTC} > 1.3 \times \text{Trading Target}$ liên tục trong $\ge 7$ ngày, lượng BTC dư thừa sẽ được phát tín hiệu chuyển đổi thành Core BTC và yêu cầu quét thủ công hoặc tự động bảo mật về địa chỉ ví lạnh đã đăng ký.
*   Tổng lượng BTC nằm trên sàn giao dịch luôn được giới hạn $\le 25\%$ tổng giá trị danh mục để giảm thiểu rủi ro đối tác.

---

## 6. Các Quy tắc Bất biến Enforced

Các quy tắc dưới đây là những ràng buộc được mã hóa cứng. Nếu có bất kỳ vi phạm nào xảy ra, hệ thống sẽ thực hiện **Panic Halt** (Dừng khẩn cấp toàn bộ hệ thống):

*   `INV-1`: Số lượng Core BTC là một hàm không giảm theo thời gian ($\Delta \text{Core BTC} \ge 0$).
*   `INV-2`: Số dư stablecoin dự trữ luôn lớn hơn hoặc bằng mức sàn quy định ($\text{Reserve USDT} \ge \text{Reserve Floor}$).
*   `INV-3`: Bảo toàn số dư: $\sum \text{Giỏ tài sản} == \text{Tổng danh mục}$ (không được rò rỉ số dư).
*   `INV-4`: Từ chối đặt bất kỳ lệnh nào nếu việc khớp lệnh đó dẫn đến vi phạm `INV-1` hoặc `INV-2`.
*   `INV-5`: Lệnh bán chỉ được đặt khi giá bán thỏa mãn: $\text{Giá bán} \ge A_{\text{cost}} \times (1 + \text{min\_profit\_threshold})$.
*   `INV-6`: Giới hạn lượng vốn triển khai mới mỗi ngày ($\text{Vốn triển khai} \le \text{Daily Deployment Cap}$).
*   `INV-7`: Giới hạn lượng BTC lưu giữ trên ví nóng sàn giao dịch ($\text{BTC sàn} \le \text{Exchange Cap}$).

---

## 7. Cấu trúc Thư mục

Mã nguồn của hệ thống được tổ chức như sau:

```text
src/
├── data/              # Đường dẫn nạp, kiểm định và làm sạch dữ liệu
├── features/          # Bộ máy tính toán đặc trưng (ATR, EMA, RSI, funding, OI)
├── regime/            # Mô hình phân loại trạng thái thị trường (HMM, clustering)
├── inventory/         # Sổ cái FIFO và quản lý giá vốn trung bình
├── grid/              # Tính toán khoảng cách lưới lệnh và định cỡ lệnh
├── risk/              # Lớp kiểm soát quy tắc bất biến và kích hoạt halt
├── execution/         # Tương tác CCXT, quản lý định tuyến lệnh
├── portfolio/         # Giám sát số dư và đối soát hàng ngày
├── backtest/          # Khung kiểm thử lịch sử (Vectorbt/Backtrader)
├── simulator/         # Bộ giả lập thị trường nhân tạo (Phase 4)
├── ai/                # Thuật toán Học tăng cường (RL) và tối ưu hóa
├── custody/           # Quản lý sweep ví lạnh và logic khuyến mãi Core
├── monitoring/        # Prometheus exporter và kênh cảnh báo Telegram
├── api/               # API dịch vụ nội bộ
└── tests/             # Kiểm thử đơn vị, kiểm thử thuộc tính (Hypothesis), chaos tests
```

---

## 8. Hướng dẫn Khởi đầu

1.  **Clone dự án:**
    ```bash
    git clone https://github.com/tamtiger/accumulation_agent.git
    cd accumulation_agent
    ```
2.  **Thiết lập môi trường:**
    Cài đặt các gói phụ thuộc Python bằng `uv` hoặc `pip`:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Cấu hình hệ thống:**
    Cập nhật thông tin tài khoản sàn và các tham số vận hành trong file `config/production.json`.
4.  **Khởi động cơ sở hạ tầng cơ sở:**
    Khởi chạy Redis và PostgreSQL/TimescaleDB thông qua docker-compose:
    ```bash
    docker-compose up -d
    ```
5.  **Khởi chạy hệ thống:**
    Chạy trình Orchestrator chính:
    ```bash
    python src/execution/orchestrator.py
    ```

---

## 9. Lộ trình Phát triển

*   **Pha 1: Prototype Dựa trên Quy tắc (Rule-Based Core)** — Xây dựng công cụ nạp dữ liệu, sổ cái FIFO, tính toán lưới thích ứng và lớp kiểm soát Invariant. (Đang thực hiện)
*   **Pha 2: Backtest Lịch sử** — Đánh giá hiệu suất hệ thống qua các thời kỳ sập mạnh và tăng trưởng của BTC.
*   **Pha 3: Tích hợp AI Phân loại Trạng thái (Regime Overlay)** — Sử dụng HMM và K-Means để tối ưu hóa hệ số định cỡ lệnh.
*   **Pha 4: Tối ưu hóa bằng Học Tăng Cường (RL)** — Huấn luyện tác tử RL tối ưu hóa vùng đệm lưới trên môi trường giả lập.
*   **Pha 5: Giao dịch Mô phỏng (Paper Trading)** — Vận hành thực tế không dùng tiền thật để đo lường độ trễ và độ trượt giá.
*   **Pha 6: Triển khai Vốn nhỏ** — Chạy thử nghiệm thực tế với $\le 1\%$ lượng vốn định danh để đối soát độ chính xác của sổ cái DB và ví sàn.
*   **Pha 7: Delta-Neutral Sleeve (Tùy chọn)** — Xây dựng giỏ hedging thu hoạch funding rate phòng vệ rủi ro.

---

## 10. Kiểm thử & Xác thực

Dự án áp dụng quy trình xác thực nghiêm ngặt để đảm bảo an toàn tuyệt đối cho tài sản:
1.  **Unit & Property-based Testing:** Kiểm thử độ chính xác tuyệt đối của cơ chế FIFO, phân bổ số dư giỏ và tính toán các Assertions của lớp Risk.
2.  **Combinatorial Purged Cross Validation (CPCV):** Sử dụng trong việc huấn luyện mô hình phân loại trạng thái để tránh rò rỉ dữ liệu lịch sử.
3.  **Backtest Sensitivity Analysis:** Stress-test hệ thống trước các biến đổi về phí giao dịch ($0.05\% \text{ đến } 0.15\%$), trượt giá ($0.02\% \text{ đến } 0.10\%$) và thuế suất.
4.  **Chaos Testing:** Chạy các kịch bản lỗi mạng, API timeout, sàn khớp lệnh một phần (partial fills) và stablecoin mất peg đột ngột.

---

## 11. Giấy phép

Dự án này mang tính chất nội bộ và thuộc bản quyền của dự án. Tất cả các quyền được bảo lưu (Proprietary. All rights reserved).
