# Hệ thống Tích lũy BTC Thích ứng (ABAS) — v2
*(Adaptive BTC Accumulation System — v2)*

> **Tóm tắt ngắn gọn:** Đây là một bộ máy tích lũy BTC dài hạn sử dụng cơ chế khai thác biến động (volatility harvesting), quản lý kho hàng thích ứng (adaptive inventory management) và nhận diện trạng thái thị trường có sự hỗ trợ của AI (AI-assisted regime detection).
>
> **Phiên bản:** 2.0
> **Mục tiêu sơ cấp:** Tối đa hóa lượng BTC nắm giữ qua nhiều chu kỳ thị trường, sau khi trừ các khoản phí giao dịch và thuế, so sánh với mốc tham chiếu là nắm giữ thụ động (passive HODL).

---

## Nhật ký thay đổi (Changelog v1 → v2)

| Khu vực | Thay đổi |
|---|---|
| Buy/Sell anchors | Thêm logic mốc tham chiếu động + giá vốn |
| Bootstrapping | Phần mới định nghĩa cách xây dựng danh mục ban đầu |
| Core BTC | Thêm quy tắc thăng hạng từ giỏ giao dịch |
| Benchmarks | Passive HODL tính theo BTC hiện là mốc so sánh chính |
| Fees & tax | Mô hình hóa rõ ràng, yêu cầu phân tích độ nhạy |
| Regime conflict | Hệ số nhân quy mô có điều kiện theo trạng thái |
| Custody | Chính sách tách biệt: lõi lạnh, giao dịch nóng, dự trữ đa dạng |
| RL data budget | Thêm yêu cầu về trình mô phỏng thị trường tổng hợp |
| Regime labeling | Chỉ sử dụng phương pháp không giám sát (HMM/clustering) |
| Cost basis | Theo dõi giá vốn theo từng lô (lot) đưa vào trạng thái |
| Sell gating | Yêu cầu ngưỡng lợi nhuận tối thiểu |
| Funding harvest | Mô đun trung lập delta mới (tùy chọn) |
| Kill switch | Phần mới (Cơ chế ngắt khẩn cấp) |
| Security | Phần mới (Bảo mật) |
| Invariants | Phần mới (Quy tắc bất biến) |
| Failure playbook | Phần mới (Kịch bản xử lý khi lỗi) |

### [GIẢI THÍCH CHI TIẾT VỀ CÁC THAY ĐỔI TRONG BẢN V2]

Sự khác biệt lớn nhất giữa v1 và v2 là tính **"Phòng thủ chủ động"**. 

1.  **Buy/Sell anchors:** Trong bản v1, hệ thống có thể mua bán dựa trên các mức giá tĩnh. Ở v2, nó sử dụng "mốc neo động" (Rolling anchors). Ví dụ: Nếu giá BTC vừa tạo đỉnh mới ở 74k, thì mốc tham chiếu mua sẽ tự động dời lên theo đỉnh đó, thay vì vẫn đợi ở mốc 50k của năm ngoái.
2.  **Cost-basis logic:** Đây là thay đổi mang tính sống còn. Hệ thống giờ đây theo dõi chính xác bạn đã mua bao nhiêu BTC ở giá nào (Lot-tracking). Điều này giúp robot biết rằng: "Tôi vừa mua cục BTC này ở giá 65k, nên dù thị trường có hồi từ 60k lên 63k, tôi cũng tuyệt đối không được bán vì chưa có lãi".
3.  **Bootstrapping:** Đây là câu trả lời cho những người mới tham gia. Thay vì "tất tay" (all-in), v2 cung cấp một lộ trình giải ngân 3 giai đoạn giúp bạn vào hàng một cách khoa học nhất, giảm thiểu tối đa cảm giác hối tiếc (Regret minimization).
4.  **Kill switch & Invariants:** v2 bổ sung các "cầu chì" tự động. Nếu hệ thống phát hiện có điều gì đó sai trái về mặt toán học (ví dụ: số dư tài khoản không khớp), nó sẽ tự đóng băng toàn bộ hoạt động để bảo vệ tiền của bạn.

---

# 1. Triết lý cốt lõi (Core Philosophy)

## Mục tiêu (Objective)

Hệ thống **KHÔNG** tối ưu hóa cho:

```
Maximize USDT profit (Tối đa hóa lợi nhuận bằng USD)
```

Hệ thống tối ưu hóa cho:

```
Maximize BTC holdings over time, net of fees and taxes,
vs. passive HODL in BTC terms.
(Tối đa hóa lượng BTC nắm giữ theo thời gian, sau khi trừ phí và thuế,
so với việc nắm giữ thụ động tính theo đơn vị BTC).
```

**Cách nhìn nhận Bitcoin (BTC):**
- **Tài sản dự trữ sơ cấp (Primary reserve asset):** BTC là "vàng kỹ thuật số", là cái đích cuối cùng của mọi giao dịch.
- **Kho lưu trữ giá trị dài hạn (Long-term store of value):** Chúng ta giữ BTC không phải để bán lấy USD tiêu xài, mà để giữ tài sản qua nhiều thế hệ.
- **Kho hàng chiến lược (Strategic inventory):** Coi BTC như hàng hóa trong kho của một đại lý. Mục tiêu là làm sao để sau mỗi năm, lượng hàng trong kho nhiều hơn năm trước.

**Cách nhìn nhận USDT (Stablecoin):**
- **Đạn dược (Ammunition):** USDT chỉ là công cụ. Nó giống như đạn, bắn đi để mang về "con mồi" là BTC.
- **Dự trữ thanh khoản (Liquidity reserve):** Tiền mặt sẵn dùng để ứng phó khi thị trường sụp đổ mạnh.
- **Công cụ tái cân bằng (Rebalancing tool):** Dùng để điều chỉnh tỷ lệ an toàn giữa phần tài sản rủi ro (BTC) và tài sản ổn định (Cash).

### [PHÂN TÍCH CHI TIẾT VỀ TRIẾT LÝ ABAS]

**Tại sao không tối ưu USD?** 
Trong 10 năm qua, USD đã mất giá khoảng 25-30% sức mua. Nếu bạn giữ 100k USD, bạn đang nghèo đi mỗi ngày. Nhưng Bitcoin có số lượng giới hạn 21 triệu đồng. ABAS tin rằng Bitcoin là "tiền thật" (Hard Money). 

**Ví dụ minh họa:**
- **Kịch bản A:** Bạn có 1 BTC lúc giá 50k. Giá tăng lên 60k, bạn bán lấy 60k USD lãi 10k. Sau đó giá tăng lên 100k, bạn dùng 60k USD đó chỉ mua lại được 0.6 BTC. Bạn lãi USD nhưng đã **thua cuộc** vì mất đi 40% lượng tài sản thực (BTC).
- **Kịch bản ABAS:** Robot sẽ dùng các đợt biến động để làm sao từ 1 BTC ban đầu, sau một chu kỳ tăng giảm, bạn có 1.2 BTC. Dù giá lúc đó là bao nhiêu, bạn cũng đã giàu hơn 20% so với chính mình.

---

# 2. Khái niệm chiến lược (Strategic Concept)

Chiến lược vận hành dựa trên 4 từ khóa chính:

```
Buy fear (Mua khi thị trường sợ hãi)
Sell partial rebounds (Bán một phần khi giá hồi phục)
Rebuy deeper discounts (Mua lại ở mức chiết khấu sâu hơn)
Accumulate BTC through volatility (Tích lũy BTC thông qua sự biến động)
```

**Các nền tảng tương đồng:**
- **Volatility harvesting (Thu hoạch biến động):** Giống như một người nông dân đi thu gom những trái chín sau mỗi cơn gió mạnh. Biến động không phải là rủi ro, nó là **nguồn lợi nhuận**.
- **Dynamic DCA (DCA năng động):** Không mua mù quáng mỗi tháng 100$. Nếu giá giảm mạnh, chúng ta mua 200$. Nếu giá tăng cao, chúng ta chỉ mua 20$.
- **Inventory trading (Giao dịch kho hàng):** Mua vào khi kho trống và bán ra khi kho đầy (theo các ngưỡng toán học).
- **Long-biased market making:** Chúng ta đóng vai trò là người cung cấp thanh khoản cho thị trường ở những vùng giá cực thấp.

**Các ràng buộc bắt buộc (Constraints):**
1.  **Luôn duy trì vị thế BTC:** Tuyệt đối không bao giờ được phép cầm 100% USDT và đứng ngoài thị trường (No sidelines).
2.  **Không bao giờ bán lỗ (Sell-gating rule):** Đây là kỷ luật thép. Robot không được phép "cắt lỗ" Bitcoin. Nếu giá giảm, chúng ta mua thêm hoặc đứng im.
3.  **Không bao giờ tiêu sạch quỹ dự trữ:** Luôn phải giữ một lượng tiền mặt (USDT) tối thiểu để bảo vệ hệ thống khỏi các cú sập "về lòng đất".

### [VÍ DỤ THỰC TẾ VỀ CHIẾN LƯỢC]

Giả sử giá BTC đang là 60,000 USD.
1.  **Thị trường sập về 50,000 USD:** Chỉ số sợ hãi (Fear) tăng cao. Robot kích hoạt lệnh mua lớn từ quỹ dự trữ.
2.  **Giá hồi lên 55,000 USD:** Robot bán một phần nhỏ (ví dụ 10% lượng vừa mua) để thu hồi lại một ít USDT dự trữ.
3.  **Giá tiếp tục sập về 45,000 USD:** Robot dùng số USDT vừa thu hồi được ở mốc 55k để mua được lượng BTC nhiều hơn ở mốc 45k.

**Kết quả:** Sau một vòng xoáy tăng giảm, lượng BTC trong ví bạn tăng lên đáng kể mà không cần nạp thêm tiền từ bên ngoài.

---

# 3. Giả định & Quy tắc bất biến (Assumptions & Invariants)

## 3.1. Giả định (Phải đúng thì hệ thống mới hoạt động được)

| Giả định | Tại sao quan trọng? | Cách xử lý nếu bị sai |
|---|---|---|
| BTC tăng giá dài hạn | Đây là nền móng của hệ thống tích lũy. | Nếu BTC về 0, hệ thống sẽ thất bại hoàn toàn. |
| Biến động giá sẽ hồi quy | Giá không bao giờ đi thẳng một mạch, nó luôn có sóng. | Hệ thống lưới (Grid) sẽ tự nới rộng để chờ sóng hồi. |
| Sàn giao dịch sẵn sàng ≥ 99% | Robot cần kết nối sàn để đặt lệnh 24/7. | Triển khai trên nhiều sàn (Binance, OKX, Bybit). |
| Stablecoin (USDT/USDC) giữ giá | USDT phải bằng 1 USD. | Chia nhỏ quỹ dự trữ vào nhiều loại Stablecoin khác nhau. |
| Không bị pháp luật cấm | Robot cần được phép hoạt động hợp pháp. | Giữ phần lớn tài sản (Lõi) ở ví cá nhân ngoài tầm kiểm soát của sàn. |

## 3.2. Quy tắc bất biến (Invariants - Buộc phải đúng trong mã nguồn)

Đây là các "luật thép" được lập trình cứng trong code. Nếu có bất kỳ dòng code nào định vi phạm, robot sẽ tự sát (halt) ngay lập tức.

```python
# INV-1: Lượng BTC trong giỏ Lõi chỉ được tăng hoặc giữ nguyên.
# Mục đích: Đảm bảo tài sản tích lũy của bạn không bị đem đi mạo hiểm.
INV-1: core_btc_qty is monotonically non-decreasing

# INV-2: Số dư USDT dự trữ phải >= mức sàn tối thiểu (% danh mục).
# Mục đích: Không bao giờ được tiêu hết tiền mặt, phải luôn có phao cứu sinh.
INV-2: reserve_usdt >= reserve_floor (% of portfolio)

# INV-3: Tổng tài sản trong tất cả các giỏ cộng lại phải bằng chính xác tổng danh mục.
# Mục đích: Kiểm tra rò rỉ dữ liệu hoặc lỗi tính toán.
INV-3: sum(buckets) == total_portfolio (no leak)

# INV-4: Không đặt lệnh mua/bán nếu nó làm vi phạm INV-1 hoặc INV-2.
# Mục đích: Chặn các lệnh sai lầm từ AI hoặc logic giao dịch.
INV-4: no order placed if it would violate INV-1 or INV-2

# INV-5: Không đặt lệnh bán nếu giá thấp hơn giá vốn trung bình cộng biên lãi.
# Mục đích: Cấm tuyệt đối việc bán lỗ Bitcoin.
INV-5: no sell order if price < avg_cost * (1 + min_profit_threshold)

# INV-6: Vốn giải ngân mỗi ngày không được vượt quá hạn mức (ví dụ 10%).
# Mục đích: Ngăn chặn việc mua quá nhanh (FOMO) khi giá đang giảm.
INV-6: daily_deployed_capital <= daily_deployment_cap

# INV-7: Tổng BTC trên ví nóng của sàn không được vượt quá hạn mức an toàn.
# Mục đích: Giảm thiểu thiệt hại nếu sàn bị hack.
INV-7: total BTC on hot exchange <= hot_exchange_cap
```

### [MÔ PHỎNG KIỂM THỬ QUY TẮC BẤT BIẾN]

Hãy xem cách robot xử lý các tình huống "nguy hiểm" nhờ các quy tắc này:

**Tình huống 1: Thị trường sập 50% trong 1 giờ.**
- *Hành động của AI:* AI hoảng loạn hoặc logic lưới yêu cầu mua hết số USDT còn lại để "bắt đáy".
- *Sự can thiệp của INV-2:* Quy tắc này phát hiện lệnh mua sẽ làm số dư USDT xuống dưới 10% danh mục.
- *Kết quả:* Lệnh bị chặn lại ngay tại tầng Risk Overlay. Hệ thống giữ lại 10% tiền mặt cuối cùng để đảm bảo sự sống sót.

**Tình huống 2: Robot định thực hiện một lệnh bán lướt sóng để thu hồi vốn.**
- *Thông số:* Giá vốn trung bình của lô hàng là 65,000 USD. Giá thị trường hiện tại là 64,500 USD.
- *Hành động:* Robot định bán để cắt lỗ vì AI dự báo giá còn giảm tiếp.
- *Sự can thiệp của INV-5:* Quy tắc này so sánh `Price (64.5k) < Avg_Cost (65k)`. 
- *Kết quả:* Lệnh bán bị từ chối. Robot bị buộc phải nắm giữ (HODL) lô hàng đó cho đến khi giá hồi phục trên 65k + phí.

**Tình huống 3: Hacker chiếm được máy chủ và định rút BTC.**
- *Hành động:* Hacker cố gắng chuyển BTC từ giỏ Lõi sang một địa chỉ ví lạ.
- *Sự can thiệp của INV-1:* Hệ thống kiểm tra thấy hành động này làm giảm `core_btc_qty`.
- *Kết quả:* Hệ thống kích hoạt cơ chế tự hủy (Panic Shutdown), đóng băng toàn bộ kết nối API và báo động đỏ qua mọi kênh liên lạc.

---

---

# 4. Mục tiêu của hệ thống (System Objectives)

Hệ thống được thiết kế để đạt được 6 mục tiêu chiến lược:

1.  **Tích lũy BTC:** Đây là mục tiêu tối thượng. Mọi thông số đều hướng tới việc gia tăng số lượng BTC sở hữu (so với mốc nắm giữ thụ động HODL).
2.  **Sống sót qua biến động (Survival):** Tránh việc bị "cháy túi" USDT trong những đợt thị trường sụt giảm dài hạn (như mùa đông crypto 2022).
3.  **Thu hoạch nhiễu (Harvest Noise):** Biến những dao động nhỏ 2-3% hàng ngày thành lợi nhuận BTC.
4.  **Tránh giao dịch quá đà (No Overtrading):** Giao dịch nhiều chỉ làm giàu cho sàn qua phí. Robot chỉ giao dịch khi xác suất thắng cao và biên lợi nhuận đủ bù đắp phí/thuế.
5.  **Bảo tồn vị thế cốt lõi:** Luôn đảm bảo bạn nắm giữ một lượng Bitcoin đủ lớn để hưởng lợi khi có "siêu sóng" tăng giá bất ngờ.
6.  **Hạn chế rủi ro đối tác:** Giới hạn lượng tiền để trên sàn. "Không phải chìa khóa của bạn, không phải tiền của bạn" (Not your keys, not your coins).

---

# 5. Kiến trúc hệ thống cấp cao (High-Level Architecture)

Đây là cách các "cơ quan" trong robot phối hợp với nhau:

- **Lớp dữ liệu (Market Data Layer):** Lấy giá từ sàn (Binance, OKX...).
- **Xác thực dữ liệu:** Loại bỏ "giá ảo", "giá rác".
- **Feature Engine:** Tính toán các chỉ báo (EMA, RSI, ATR...).
- **Nhận diện trạng thái (Regime Detection):** AI tự động phân loại thị trường (Hoảng loạn, Bình thường, Hưng phấn).
- **Quản lý kho hàng (Inventory Engine):** Theo dõi xem trong kho còn bao nhiêu BTC, mua giá nào.
- **Lưới thích ứng (Adaptive Grid):** Tự động đặt các lệnh chờ mua/chờ bán ở các mức giá hợp lý.
- **Lớp phủ rủi ro (Risk Overlay):** Bộ kiểm tra cuối cùng trước khi lệnh được bắn lên sàn.
- **Thực thi lệnh (Execution Engine):** Gửi lệnh lên sàn và theo dõi xem có khớp không.
- **Theo dõi danh mục (Portfolio Tracking):** Giám sát trạng thái 3 giỏ tài sản (Lõi / Giao dịch / Dự trữ) và đối soát giá vốn.
- **Giám sát & Phân tích (Monitoring & Analytics):** Báo cáo kết quả và cảnh báo qua Telegram hoặc Dashboard.

---

# 6. Cấu trúc danh mục đầu tư (Portfolio Structure)

Hệ thống chia tài sản của bạn thành 3 "túi" tiền riêng biệt:

## 6.1. Phân bổ vốn mục tiêu (Target steady-state)

| Giỏ tài sản (Bucket) | Tỷ lệ | Mục đích | Cách cất giữ |
|---|---|---|---|
| **Core BTC (Lõi)** | 60–80% | Tài sản chiến lược, không bao giờ bán. | Ví lạnh (Lưu trữ ngoại tuyến an toàn). |
| **Trading BTC (Giao dịch)** | 10–25% | Dùng để lướt sóng, tạo lợi nhuận BTC. | Ví nóng trên sàn (Để robot đặt lệnh). |
| **USDT Reserve (Dự trữ)** | 10–20% | Đạn dược để bắt đáy khi giá sập. | Chia nhỏ vào USDT, USDC, Tín phiếu. |

## 6.2. Đa dạng hóa quỹ dự trữ USDT

Để tránh rủi ro "Stablecoin sụp đổ":
- **USDT (Tether):** 40–50% (Dùng để giao dịch nhanh trên Binance).
- **USDC (Circle):** 30–40% (Độ minh bạch cao, dự phòng cho USDT).
- **DAI / T-bills:** 10–20% (Kiếm thêm lãi suất nhỏ khi tiền đang nằm chờ).

## 6.3. Chính sách lưu ký (Custody Policy)

- **Core BTC (Lõi):** Luôn sử dụng **ví lạnh (cold wallet)**, có thể là ví đa chữ ký (multisig) hoặc ví cứng (hardware wallet).
- **Quy tắc quét (Sweep rule):** Khi robot lướt sóng quá giỏi và kiếm được nhiều BTC trên sàn, hệ thống sẽ nhắc bạn: "Này, trên sàn đang có quá nhiều BTC rồi, hãy chuyển bớt về ví lạnh đi cho an toàn".
- **Quyền API:** Khóa API của robot tuyệt đối không được cấp quyền "Rút tiền" (Withdraw). Robot chỉ có quyền xem số dư và đặt lệnh mua/bán.

---

# 7. Khởi động (Bootstrapping — Từ số 0 đến khi ổn định)

**Vấn đề:** Nếu hôm nay bạn bắt đầu với 100k USD. Nếu bạn mua hết BTC ngay bây giờ mà mai giá sập 20%, bạn sẽ cực kỳ hối tiếc. Ngược lại, nếu bạn không mua gì mà mai giá tăng 20%, bạn cũng sẽ tiếc.

**Giải pháp: Chiến lược 3 giai đoạn của ABAS.**

| Giai đoạn | Thời gian | Hành động | Giải thích ý nghĩa |
|---|---|---|---|
| **Giai đoạn B1 — Gieo hạt** | Tuần 1 | Mua ngay lập tức 20% lượng BTC mục tiêu. | Đảm bảo bạn "có hàng" ngay lập tức để không bị lỡ sóng nếu giá bay luôn. |
| **Giai đoạn B2 — DCA dốc** | Tuần 2–12 | Mua đều đặn 60% tiếp theo trong vòng 3 tháng (mỗi tuần mua một ít). | Giúp bạn có mức giá trung bình ổn định, không lo đỉnh hay đáy ngắn hạn. |
| **Giai đoạn B3 — Cơ hội** | Tuần 4–26 | Giữ lại 20% cuối cùng để chờ những cú sập mạnh (>15-20%). | Đây là "đòn quyết định" giúp bạn mua được hàng cực rẻ khi có biến cố lớn. |

- **Xây dựng song song:** Giỏ giao dịch (Trading bucket) và quỹ dự trữ (Reserve) được xây dựng song song trong quá trình lấp đầy giỏ Lõi (Core).

### [TỔNG KẾT GIAI ĐOẠN KHỞI ĐỘNG]

**Cơ sở lý luận (Rationale):** Phương pháp này loại bỏ sự tùy hứng, giới hạn cảm giác hối tiếc, đồng thời nắm bắt được cả xu hướng tiếp diễn (trend continuation) và sự hồi quy trung bình (mean reversion).

Cách làm này loại bỏ hoàn toàn yếu tố cảm xúc. Bạn không cần phải đoán khi nào là đáy. Bạn chỉ cần tuân thủ lịch trình giải ngân này. Sau 6 tháng, bạn sẽ có một danh mục Bitcoin vững chắc để bắt đầu vận hành robot toàn phần.

---

# 8. Công cụ quản lý kho hàng (Inventory Management Engine)

## Triết lý (Philosophy)

Tác nhân (Agent) suy nghĩ theo hướng:
*"Làm thế nào để tôi tăng lượng tồn kho BTC trên mỗi đơn vị rủi ro chấp nhận?"*

**KHÔNG PHẢI:**
*"Tôi có thể dự đoán cây nến tiếp theo hay không?"*

### [GIẢI THÍCH CHI TIẾT]
Nhiều robot giao dịch bị cháy tài khoản vì chúng cố gắng làm "thầy bói" đoán tương lai. ABAS thì khác, nó coi mình là một "thương nhân". Nếu bạn buôn vàng, khi vàng rẻ bạn mua thêm để tích trữ, khi vàng đắt bạn bán bớt để lấy tiền mặt chờ mua đợt rẻ tiếp theo. Mục tiêu cuối cùng là sau một thời gian, số lượng vàng trong kho của bạn tăng lên. Đó chính là tư duy "Quản lý tồn kho" (Inventory Management).

## Bộ theo dõi giá vốn (Cost Basis Tracker - Thành phần bắt buộc)

Đây là "bộ não" tính toán của hệ thống. Nếu không có bộ phận này, robot sẽ không bao giờ biết mình đang lãi hay lỗ thực sự.

- **Sổ cái FIFO theo từng lô (Per-lot FIFO ledger):** Ghi chép chi tiết mọi lệnh mua BTC: `(Số lượng - qty, Giá mua - price, Thời gian - timestamp, Nhãn trạng thái - regime_tag)`.
- **Chức năng tính toán:**
    - `avg_cost`: Giá vốn trung bình của tất cả BTC hiện có.
    - `realized_pnl_btc`: Lợi nhuận BTC đã thực hiện (đã chốt).
    - `unrealized_pnl_btc`: Lợi nhuận BTC chưa thực hiện (trên giấy tờ).
- **Tính bền vững (Persistence):** Dữ liệu phải được lưu vào Database (DB) và được đối soát (reconciled) với các lệnh khớp thực tế trên sàn (exchange fills) hàng ngày.
- **Vai trò:** Cung cấp dữ liệu cho cơ chế chặn bán lỗ (INV-5).

---

# 9. Các mốc tham chiếu (Reference Anchors - Cực kỳ quan trọng)

Tất cả các ngưỡng mua/bán đều được định nghĩa dựa trên các mốc tham chiếu rõ ràng, chứ không phải "giá giảm X%".

| Mốc (Anchor) | Định nghĩa | Sử dụng cho |
|---|---|---|
| `A_trend` | EMA(200, khung ngày) | Bộ lọc xu hướng vĩ mô (Macro trend filter) |
| `A_range` | Giá cao nhất trong 30 ngày qua - Rolling max(high, 30d) | Kích hoạt mua khi giá sụt giảm từ đỉnh (Drawdown-from-peak) |
| `A_vol` | ATR(14) / giá hiện tại | Co dãn khoảng cách lưới thích ứng (Adaptive grid spacing) |
| `A_cost` | Giá vốn trung bình theo từng lô | Chặn bán lỗ (Sell gating) |
| `A_mean` | EMA(20, khung 4 giờ) | Mốc hồi quy trung bình (Mean-reversion anchor) |

**Lưu ý kỹ thuật:** Mọi mức "giảm X%" luôn được tính bằng công thức: `(A_anchor − giá_hiện_tại) / A_anchor` với mốc tham chiếu được chỉ định cụ thể trong từng quy tắc.

---

# 10. Logic giao dịch cốt lõi (Core Trading Logic)

## 10.1. Logic Mua (Buy Logic - Phụ thuộc trạng thái thị trường)

Bảng giải ngân dự trữ cơ bản (tính theo % của **số dư dự trữ còn lại**, không phải tổng danh mục):

| Mức sụt giảm từ `A_range` | % Giải ngân dự trữ cơ bản | [Ví dụ minh họa] |
|---|---|---|
| −3% | 5% | Nếu bạn có 10,000 USDT dự trữ, khi giá giảm 3% từ đỉnh tháng, robot sẽ trích 500 USDT để mua BTC. |
| −6% | 10% | Giá giảm sâu hơn, robot trích tiếp 10% của số USDT còn lại. |
| −10% | 20% | Bắt đầu giải ngân mạnh tay. |
| −15% | 30% | Giải ngân quyết liệt. |
| −25% | 40% | Mua tối đa khi thị trường hoảng loạn. |

**Áp dụng hệ số nhân trạng thái (Regime Multiplier):**
`vốn_giải_ngân_thực_tế = vốn_cơ_bản × hệ_số_nhân_trạng_thái(trạng_thái)`

| Trạng thái (Regime) | Hệ số nhân (Multiplier) | [Hành động của AI] |
|---|---|---|
| **Panic dump (trong sóng tăng)** | 1.5 – 2.0 | Tăng mạnh lượng mua vì đây là cơ hội bắt đáy hiếm có. |
| **Sideways (Đi ngang)** | 1.0 | Giữ nguyên lộ trình mua tiêu chuẩn. |
| **Bull trend (Sóng tăng)** | 0.8 | Hạn chế mua vì giá đang đắt. |
| **Bear trend (Sóng giảm)** | 0.3 – 0.5 | Mua rất ít để giữ tiền mặt chờ đáy sâu hơn. |
| **Blowoff top (Đỉnh hưng phấn)** | 0.0 | **Dừng mua hoàn toàn.** |

**Các giới hạn cứng (Hard caps):**
- `daily_deployment_cap` ≤ 5–10% tổng danh mục.
- Không mua nếu tiền mặt dưới mức sàn `reserve_floor`.
- Không mua nếu công tắc ngắt (kill switch) đang được kích hoạt.

## 10.2. Logic Bán (Sell Logic - Có cổng kiểm soát)

| Mức hồi phục từ đáy cục bộ | Lượng bán cơ bản |
|---|---|
| +4% | 10% lượng BTC giao dịch |
| +8% | 20% lượng BTC giao dịch |
| +12% | 30% lượng BTC giao dịch |

**Các cổng chặn (Gates) — Phải thỏa mãn TẤT CẢ mới được bán:**
1.  `giá > giá_vốn_trung_bình × (1 + ngưỡng_lãi_tối_thiểu)` (Mặc định ngưỡng lãi = 1.5 × [phí giao dịch 2 chiều + trượt giá]).
2.  Không nằm trong xu hướng tăng mạnh (Áp dụng hệ số nhân bán theo trạng thái).
3.  Lệnh bán **không bao giờ** được chạm vào giỏ Lõi (Core bucket).
4.  Sau khi bán, lượng BTC giao dịch còn lại phải ≥ mức sàn `trading_floor`.

**Hệ số nhân bán theo trạng thái (Sell regime multipliers):**
- **Blowoff top:** 1.5 (Bán mạnh hơn để chốt lãi).
- **Bull trend:** 0.3 (Bán rất ít để gồng lãi dài hơn).
- **Sideways:** 1.0 (Bán theo kế hoạch).
- **Bear trend:** 0.8 (Bán để thu hồi vốn nhanh).
- **Panic dump:** 0.0 (**Tuyệt đối không bán** khi mọi người đang hoảng loạn tháo chạy).

## 10.3. Quy tắc thăng hạng Lõi (Core Promotion Rule)

Khi lượng BTC giao dịch (`trading_btc_qty`) vượt quá mục tiêu (`trading_target`) hơn 30% trong vòng ít nhất 7 ngày, phần thặng dư sẽ được thăng hạng:

```python
phần_thừa = trading_btc_qty − trading_target
core_btc_qty += phần_thừa
trading_btc_qty −= phần_thừa
```

Đây chính là cơ chế **giúp giỏ Lõi tăng trưởng** theo thời gian. Phần BTC thặng dư này sau đó sẽ được quét (sweep) về ví lạnh.

---

# 11. Hệ thống lưới thích ứng (Adaptive Grid System)

Khoảng cách lưới tự động co dãn theo biến động thực tế (Realized Volatility).

| Trạng thái biến động (σ năm) | Khoảng cách lưới (mỗi tầng) |
|---|---|
| Thấp (< 40%) | 1 – 2% |
| Trung bình (40–80%) | 3 – 5% |
| Cao (> 80%) | 6 – 10% |

Hệ thống xây dựng lại lưới (Rebuild) khi:
- Trạng thái biến động thay đổi (có cơ chế trễ - hysteresis để tránh nhảy nhãn liên tục).
- Mốc neo phạm vi (`A_range`) di chuyển > 10%.
- Bộ phân loại trạng thái AI thay đổi nhãn trạng thái.

---

# 12. Lớp nhận diện trạng thái thị trường (Regime Detection Layer)

## 12.1. Phương pháp dán nhãn: Chỉ dùng không giám sát (Unsupervised Only)

Tuyệt đối không dùng dữ liệu do con người dán nhãn (ví dụ: "đây là panic", "đây là bear"). Các phương pháp gồm:
1.  **HMM (Hidden Markov Model):** Chạy trên 2, 3 hoặc 4 trạng thái dựa trên Log-returns và Realized Vol.
2.  **K-means clustering:** Gom nhóm các vector đặc trưng dữ liệu.
3.  **Change-point detection (BOCPD):** Phát hiện các điểm chuyển đổi trạng thái bằng xác suất Bayesian.

## 12.2. Các trạng thái đầu ra (Output regimes)
(Các nhãn này robot chỉ đánh số index, tên gọi dưới đây là do con người đặt sau khi phân tích dữ liệu):

| Trạng thái | Các đặc trưng điển hình |
|---|---|
| **Panic dump** | Lợi nhuận âm lớn, biến động (vol) cao, funding âm, khối lượng tăng vọt. |
| **Sideways** | Biến động thấp, đi ngang trong biên độ, xu hướng phẳng. |
| **Bull trend** | Độ dốc xu hướng dương, lượng hợp đồng mở (OI) tăng, funding dương. |
| **Blowoff top** | Funding cực cao, biến động cực lớn, giá tăng parabol. |
| **Bear market** | Xu hướng âm, lượng hợp đồng mở (OI) giảm, khối lượng thấp. |

## 12.3. Các đặc trưng (Features) sử dụng cho AI

**Nhóm Cơ bản:**
- ATR, độ biến động thực tế (với nhiều khung thời gian khác nhau).
- Độ dốc các đường trung bình (EMA20, EMA50, EMA200).
- Trạng thái RSI.
- Chỉ số Z-score của khối lượng giao dịch.

**Nhóm Nâng cao:**
- Phí Funding (thị trường phái sinh).
- Biến động lượng hợp đồng mở (OI delta).
- Dữ liệu thanh lý (Liquidation data).
- Dòng lệnh (Orderflow) và chênh lệch khối lượng (Delta volume).
- Hồ sơ khối lượng (Volume profile) và khoảng cách tới điểm POC (Point of Control).

---

# 13. Chiến lược tích hợp AI (AI Integration Strategy)

## 13.1. KHÔNG dùng AI để:
- **Dự đoán chính xác hướng đi của giá BTC.** (Robot không phải là thầy bói).

## 13.2. DÙNG AI để:
### A. Phân loại trạng thái (Regime classification)
Học máy không giám sát, đưa ra trạng thái thị trường hiện tại kèm theo độ tin cậy (confidence score).

### B. Điều chỉnh quy mô vị thế động (Dynamic position sizing)
Dựa trên `độ tin cậy của AI → điều chỉnh hệ số giải ngân (0.5 – 1.5)`.

### C. Tối ưu hóa lưới thích ứng (Adaptive grid optimization)
Học tăng cường (RL) tự động điều chỉnh khoảng cách lưới, tốc độ tiêu quỹ dự trữ, và các ngưỡng hồi phục trong một phạm vi hành động được giới hạn.

---

# 14. Chiến lược học tăng cường (Reinforcement Learning - RL)

## 14.1. Những gì RL sẽ tối ưu hóa:
| Thành phần | RL có can thiệp không? |
|---|---|
| Hệ số nhân khoảng cách lưới | Có |
| Đường cong giải ngân quỹ dự trữ | Có |
| Tỷ lệ bán theo từng trạng thái | Có |
| Ngưỡng lợi nhuận mục tiêu | Có |
| Dự đoán giá thô | **KHÔNG** |

## 14.2. Bài toán ngân sách dữ liệu (Data Budget Problem)
Bitcoin chỉ có khoảng 15 năm dữ liệu, quá ít cho RL (thường cần 10⁵–10⁶ lượt chạy). Giải pháp:
1.  **Trình mô phỏng thị trường tổng hợp (Synthetic market simulator):** (Bắt buộc cho Giai đoạn 4)
    - Sử dụng mô hình GBM với độ biến động thay đổi theo trạng thái.
    - Sử dụng bộ tạo dữ liệu GAN hoặc Diffusion được huấn luyện trên các đặc trưng lịch sử.
    - Kiểm tra trình mô phỏng: Các chuỗi dữ liệu tạo ra phải vượt qua được các bài kiểm tra thực tế (đuôi béo, cụm biến động, tương quan tự động).
2.  **Không gian hành động giới hạn:** Chỉ cho phép AI điều chỉnh tối đa 4 tham số liên tục để giữ cho mô hình không bị quá phức tạp.
3.  **Offline RL (CQL, IQL):** Sử dụng dữ liệu lịch sử để huấn luyện AI có một điểm xuất phát tốt trước khi cho nó tự học trong trình mô phỏng.

---

# 15. Hàm phần thưởng (Reward Function)

## 15.1. Cách thiết lập SAI (Rủi ro cao):
`reward = usdt_profit` (Chỉ quan tâm lợi nhuận USDT).

## 15.2. Cách thiết lập ĐÚNG (Tiêu chuẩn ABAS):
```python
reward = (
    tăng_trưởng_btc                 # Mục tiêu chính (primary)
    - phạt_sụt_giảm_tài_sản          # Để sống sót (survival)
    - phạt_giao_dịch_quá_đà          # Để tiết kiệm phí và thuế
    - phạt_cạn_kiệt_dự_trữ           # Để đảm bảo thanh khoản
    - phạt_vi_phạm_quy_tắc_bất_biến  # Phạt cực nặng, kết thúc lượt chạy
    - phạt_kết_quả_kém_hơn_hodl      # Phải thắng được mốc tham chiếu
)
```

**Điểm mấu chốt:** `phạt_kết_quả_kém_hơn_hodl` là phần bổ sung quan trọng. Nếu chiến lược mang lại ít BTC hơn việc chỉ mua rồi để đó (Passive HODL), AI sẽ bị phạt nặng.

---

# 16. Đại diện trạng thái (State Representation)

Đây là Vector trạng thái mà robot AI sẽ nhìn thấy ở mỗi bước thời gian để ra quyết định:

```python
state = [
    # 1. Nhóm Giá & Biến động (Price & Vol)
    btc_price,                   # Giá BTC hiện tại
    returns_1h, returns_24h,     # Tỷ suất lợi nhuận 1h, 24h
    returns_7d,                  # Tỷ suất lợi nhuận 7 ngày
    realized_vol_short,          # Độ biến động thực tế (ngắn hạn)
    realized_vol_long,           # Độ biến động thực tế (dài hạn)
    atr_normalized,              # ATR chuẩn hóa theo giá

    # 2. Nhóm Xu hướng (Trend)
    ema20_slope, ema200_slope,   # Độ dốc đường EMA20 và EMA200
    price_vs_ema200,             # Khoảng cách giữa giá và EMA200

    # 3. Nhóm Phái sinh (Derivatives)
    funding_rate,                # Phí Funding hiện tại
    oi_delta,                    # Thay đổi của lượng hợp đồng mở
    liquidation_intensity,       # Cường độ thanh lý trên sàn

    # 4. Nhóm Trạng thái (Regime)
    regime_label_onehot,         # Nhãn trạng thái (mã hóa One-hot)
    regime_confidence,           # Độ tin cậy của bộ phân loại AI

    # 5. Nhóm Danh mục (Portfolio - Đã chuẩn hóa)
    core_btc_ratio,              # Tỷ lệ giỏ Lõi
    trading_btc_ratio,           # Tỷ lệ giỏ Giao dịch
    reserve_ratio,               # Tỷ lệ quỹ Dự trữ USDT
    avg_cost_distance,           # Khoảng cách từ giá tới giá vốn (price - avg_cost) / avg_cost
    unrealized_pnl_btc,          # Lợi nhuận BTC chưa thực hiện

    # 6. Nhóm Ràng buộc (Constraints)
    daily_capacity_remaining,    # Hạn mức giải ngân còn lại trong ngày
    reserve_headroom,            # Khoảng cách tới mức sàn dự trữ tối thiểu
]
```

---

# 17. Lớp phủ rủi ro & Công tắc ngắt (Risk Overlay & Kill Switches)

Đây là các quy tắc bảo vệ hệ thống, hoạt động độc lập với logic giao dịch.

## 17.1. Các quy tắc thường trực (Standing Rules)

| Quy tắc | Giá trị | Ý nghĩa |
|---|---|---|
| **Giải ngân tối đa hàng ngày** | 5 – 10% danh mục | Giới hạn lượng tiền mặt được tiêu mỗi ngày. |
| **Dự trữ USDT tối thiểu** | 10 – 20% danh mục | Luôn giữ tiền mặt để sống sót qua sập mạnh. |
| **Bảo vệ giỏ Lõi (Core)** | Không bao giờ bán / Không đòn bẩy | Thực thi nghiêm ngặt bởi Quy tắc bất biến INV-1. |
| **Hạn mức ví nóng** | Tối đa 25% tổng BTC | Giới hạn lượng BTC để trên sàn giao dịch. |

## 17.2. Công tắc ngắt (Kill Switches) — Tạm dừng tự động

| Kích hoạt (Trigger) | Hành động | [Giải thích lý do] |
|---|---|---|
| **Sụt giảm (Drawdown) > 15% trong 24h** | Tạm dừng các lệnh mua mới | Giá giảm quá sốc, cần chờ ổn định. |
| **Sụt giảm (Drawdown) > 25% trong 7 ngày** | Tạm dừng toàn bộ giao dịch | Yêu cầu con người kiểm tra thủ công. |
| **Dự trữ < Mức sàn (Floor)** | Chỉ tạm dừng các lệnh mua | Bảo vệ quỹ tiền mặt còn lại. |
| **Lỗi API sàn > 5% trong 5 phút** | Tạm dừng toàn bộ, gửi cảnh báo | Kết nối mạng hoặc sàn đang gặp sự cố. |
| **Stablecoin De-peg > 2%** | Đóng băng đồng Stablecoin bị lỗi | USDT/USDC mất giá là rủi ro hệ thống. |
| **Chênh lệch mua/bán (Spread) > 5 lần trung bình** | Tạm dừng toàn bộ | Thanh khoản quá mỏng, dễ bị trượt giá nặng. |
| **Phí Funding > 0.3% mỗi 8 giờ** | Tạm dừng các lệnh mua đuổi | Thị trường đang quá nóng, rủi ro điều chỉnh cao. |
| **Khớp lệnh bất thường (Trượt giá > 2%)** | Dừng hệ thống, đối soát lại sổ cái | Đảm bảo tính toàn vẹn của dữ liệu giá vốn. |

## 17.3. Thiết lập lại hệ thống (Circuit Breaker Reset)
- **Tự động:** Sau khi điều kiện lỗi biến mất trong 30 phút (đối với các lỗi mềm).
- **Thủ công:** Nếu bất kỳ công tắc ngắt nào bị kích hoạt 2 lần trong 24 giờ, hệ thống sẽ khóa chặt và yêu cầu con người mở lại.

---

# 18. Tùy chọn: Thu hoạch phí Funding (Delta-Neutral Funding Harvest)

Mô-đun phụ, hoạt động riêng biệt, mặc định tắt cho đến Giai đoạn 5+.

**Cơ chế:**
- Khi phí `funding_rate_perp > ngưỡng` (ví dụ: 0.05%/8h bền vững)
- Mở vị thế đối ứng tương đương `short perp + long spot` → delta-neutral (trung lập thị trường)
- Thu phí Funding bằng USDT → nạp thêm vào quỹ dự trữ

**Ràng buộc:**
- Tối đa 20% danh mục được phân bổ cho mô-đun này
- Yêu cầu bộ giám sát rủi ro riêng biệt (rủi ro chênh lệch giá basis risk, thanh lý vị thế perp)
- Được hạch toán riêng biệt; số lượng BTC ở phía giao ngay (spot) vẫn được tính vào tổng lượng tồn kho BTC

Đây là một động cơ tích lũy thực sự (kiếm lợi nhuận mà không làm thay đổi mức độ tiếp xúc với biến động giá BTC) nhưng làm tăng thêm độ phức tạp. Hãy tạm hoãn cho đến khi hệ thống cốt lõi hoạt động ổn định.

---

# 19. Phí, Thuế và Trượt giá (Fees, Taxes, and Slippage)

Hệ thống phải được kiểm tra thực tế qua các chi phí sau:

## 19.1. Mô hình phí (Fee Model)
| Thành phần | Giá trị mặc định |
|---|---|
| **Phí Taker** | 0.10% (Binance spot tiêu chuẩn) |
| **Phí Maker** | 0.02% (Khi có ưu đãi BNB) |
| **Tỷ lệ Maker/Taker dự kiến** | 60/40 |
| **Trượt giá (Slippage)** | 0.05% + hàm số dựa trên (quy mô lệnh, độ sâu sổ lệnh) |
| **Phí rút tiền** | Cố định, được tính mỗi khi quét về ví lạnh |

**Tổng chi phí vòng quay (Round-trip cost): ~0.25%.** Một giao dịch phải có mục tiêu lãi ít nhất 2 lần con số này (0.5%) mới được phép thực hiện.

## 19.2. Mô hình Thuế (Tax Model)
- Mỗi lệnh bán là một sự kiện tính thuế (Taxable event).
- Passive HODL chỉ đóng thuế khi bán hết vào cuối kỳ (Lợi thế thuế lớn).
- Backtest phải báo cáo cả lợi nhuận BTC **Trước thuế** và **Sau thuế**. Robot phải thắng được HODL ngay cả sau khi đã trừ thuế.

## 19.3. Phân tích độ nhạy (Sensitivity Analysis) - Bắt buộc
Chạy Backtest tại các mức:
- Phí: 0.05%, 0.10%, 0.15%.
- Trượt giá: 0.02%, 0.05%, 0.10%.
- Thuế: 0%, 20%, 35%.
Nếu chiến lược thất bại trước HODL ở mức (Phí 0.1% / Trượt giá 0.05% / Thuế 20%), chiến lược đó coi như không khả thi.

---

# 20. Phương pháp chống học vẹt (Anti-Overfitting Methodology)

## Đường ống xác thực (Validation Pipeline)

```
Huấn luyện (Train)
  ↓
Kiểm chứng tịnh tiến (Walk-Forward Validation)
  ↓
CPCV (Kiểm chứng chéo tổ hợp có loại bỏ dữ liệu)
  ↓
PBO (Xác suất học vẹt của thử nghiệm lịch sử)
  ↓
Thử nghiệm Out-of-Sample Backtest
  ↓
Giao dịch giả lập Paper Trading (≥3 tháng)
```

## Walk-Forward (Kiểm chứng tịnh tiến)

*(Giải thích: Phương pháp kiểm thử bằng cách huấn luyện mô hình trên một khoảng dữ liệu quá khứ rồi chạy thử nghiệm ngay ở giai đoạn tiếp theo. Sau đó, tịnh tiến khoảng thời gian huấn luyện và thử nghiệm về phía trước để lặp lại quy trình, giúp mô phỏng cách hệ thống thích ứng và tự cập nhật trong thực tế).*

Lịch trình ví dụ:
```
Train: 2018–2020 → Test: 2021
Train: 2018–2021 → Test: 2022
Train: 2018–2022 → Test: 2023
Train: 2018–2023 → Test: 2024
Train: 2018–2024 → Test: 2025 (paper)
```

## CPCV (Combinatorial Purged Cross Validation — Kiểm chứng chéo tổ hợp có loại bỏ dữ liệu)

*(Giải thích: Phương pháp chia nhỏ dữ liệu lịch sử thành nhiều phần và tạo ra nhiều tổ hợp tập huấn luyện/kiểm thử khác nhau. Để tránh rò rỉ dữ liệu (data leakage), phương pháp này loại bỏ (purging) các phần dữ liệu bị chồng lấn giữa các tập và áp dụng cơ chế cấm (embargo) dữ liệu ngay sau tập kiểm thử).*

- Thực hiện loại bỏ (purge) và cấm (embargo) dữ liệu xung quanh ranh giới các tập kiểm thử (test fold).
- Cực kỳ quan trọng đối với thị trường Crypto do hiện tượng tự tương quan (autocorrelation) và gom cụm biến động (volatility clustering).

## PBO (Probability of Backtest Overfitting — Xác suất học vẹt của thử nghiệm lịch sử)

*(Giải thích: Chỉ số đo lường xác suất một chiến lược đạt kết quả backtest xuất sắc chỉ vì các tham số được tối ưu hóa quá mức để khớp với dữ liệu quá khứ (học vẹt/overfit) thay vì có hiệu quả thực tế khi chạy trên dữ liệu tương lai).*

- Mục tiêu: PBO < 0.5 (lý tưởng là < 0.3).
- Nếu PBO > 0.7, chiến lược gần như chắc chắn bị học vẹt (overfit).

---

# 21. Mốc tham chiếu so sánh (Benchmarks - Bắt buộc)

Mỗi lần chạy thử nghiệm phải báo cáo kết quả so với:

| Mốc tham chiếu | Tại sao phải so sánh? |
|---|---|
| **Passive HODL (Mua vào ngày 0)** | **Chính:** ABAS phải thắng mốc này về lượng BTC sau khi trừ thuế. |
| **Weekly DCA** | Mốc so sánh chiến lược mua trung bình giá cơ bản. |
| **Lưới 5% cố định** | Để chứng minh giá trị của AI/Lớp nhận diện trạng thái. |
| **Core + Weekly DCA** | Để chứng minh giá trị của mô-đun lướt sóng (swing sleeve). |

Chỉ số tiêu đề của mọi lượt chạy là: `Δ_BTC vs HODL`.

---

# 22. Khung thử nghiệm (Backtesting Framework)

## Công cụ sử dụng (Stack)

| Công cụ | Mục đích |
|---|---|
| vectorbt | Giả lập quét tham số nhanh (Fast sweep simulation) |
| backtrader hoặc nautilus-trader | Mô phỏng khớp lệnh thực tế (sổ lệnh order book, khớp lệnh từng phần partial fills) |
| Polars / Pandas | Xử lý dữ liệu |
| DuckDB | Phân tích nhanh (Ad-hoc analysis) |
| MLflow | Theo dõi và quản lý các thí nghiệm (Experiment tracking) |

## Yêu cầu thử nghiệm (Backtest Requirements)

- Phải mô phỏng được việc khớp lệnh từng phần (partial fills).
- Phải mô hình hóa đầy đủ các loại phí + trượt giá (slippage) + chi phí rút tiền về ví lạnh (withdrawal costs).
- Phải mô phỏng các khoản thanh toán phí Funding (nếu mô-đun Funding được bật).
- Phải đối soát và đảm bảo các Quy tắc bất biến (invariants) được giữ vững tại mỗi bước giá (tick).
- Phải báo cáo cả hai chỉ số hiệu quả trước thuế (pre-tax) và sau thuế (after-tax).

---

# 23. Các chỉ số đo lường (Metrics)

## 23.1. Chỉ số ưu tiên BTC (BTC-Native)
| Chỉ số | Định nghĩa |
|---|---|
| `Δ_BTC vs HODL` | Lượng BTC của ABAS − Lượng BTC của HODL tại thời điểm kết thúc. |
| **BTC CAGR** | Tỷ lệ tăng trưởng số lượng BTC hàng năm. |
| **BTC Velocity** | Lượng BTC tích lũy được trên mỗi đơn vị rủi ro sụt giảm. |
| **Core Promotion Rate** | Tốc độ chuyển BTC từ giao dịch sang tích trữ vĩnh viễn. |
| **Reserve Stability** | % thời gian quỹ dự trữ duy trì trên mức sàn an toàn. |

## 23.2. Chỉ số phụ
- Sharpe / Sortino (Tính bằng đơn vị BTC).
- Profit factor (Hệ số lợi nhuận).
- Tỷ lệ phí (Tổng phí / Tổng lợi nhuận thô). Nếu phí quá cao, robot đang làm giàu cho sàn.

---

# 24. Kiến trúc thực thi (Execution Architecture)

Cấu trúc mã nguồn tổ chức chuyên nghiệp:
```
src/
├── data/              # Thu thập, xác thực, làm sạch dữ liệu
├── features/          # Trích xuất đặc trưng
├── regime/            # HMM, clustering, change-point
├── inventory/         # Quản lý kho, theo dõi giá vốn
├── grid/              # Bộ máy lưới thích ứng
├── risk/              # Quy tắc bất biến, công tắc ngắt
├── execution/         # Đặt lệnh lên sàn, CCXT wrappers
├── portfolio/         # Theo dõi danh mục, đối soát
├── backtest/          # Giả lập vectorbt / backtrader
├── simulator/         # Máy tạo thị trường giả lập (Giai đoạn 4)
├── ai/                # Các tác nhân RL, mô hình trạng thái
├── custody/           # Logic quét ví lạnh, đối soát thủ công
├── monitoring/        # Dashboard Grafana, báo cáo metrics
├── api/               # API nội bộ giữa các service
└── tests/             # Unit test, replay test
```

---

# 25. Hạ tầng công nghệ (Tech Stack)

## 25.1. Hệ thống lõi
- **Ngôn ngữ:** Python 3.11+
- **API Sàn:** CCXT + WebSocket trực tiếp của Binance.
- **Cơ sở dữ liệu:** PostgreSQL + TimescaleDB (Chuyên trị chuỗi thời gian).
- **Hàng đợi:** Redis.
- **Giám sát:** Grafana + Prometheus.
- **Bảo mật:** HashiCorp Vault (Quản lý bí mật).

## 25.2. Hệ thống AI
- **Học tăng cường (RL):** Stable-Baselines3 / CleanRL.
- **Thí nghiệm:** MLflow.
- **Xác thực AI:** FinRL_Crypto.
- **Trình mô phỏng:** Custom Simulator + QuantGAN.
# 26. Nguồn dữ liệu (Data Sources)

Dữ liệu đầu vào là "máu" và "oxy" để nuôi dưỡng hệ thống AI. Nếu dữ liệu không chuẩn, mọi thuật toán RL hay HMM đều trở nên vô dụng.

## 26.1. Các nguồn dữ liệu bắt buộc (Required)

Hệ thống yêu cầu các luồng dữ liệu sau đây để duy trì hoạt động:

- **Dữ liệu Giá (Binance OHLCV):** 
    - Bao gồm Giá mở (Open), Cao nhất (High), Thấp nhất (Low), Đóng cửa (Close) và Khối lượng (Volume).
    - Cần thu thập trên 3 khung thời gian chính: 1 phút (1m), 1 giờ (1h) và 1 ngày (1d).
    - [Giải thích]: Dữ liệu 1m dùng cho việc thực thi lệnh chính xác; 1h và 1d dùng để AI nhận diện xu hướng dài hạn.

- **Phí Funding (Binance Funding Rate):**
    - Cần thu thập dữ liệu lịch sử và dữ liệu thời gian thực.
    - [Giải thích]: Đây là chỉ số quan trọng để biết phe Long hay Short đang chiếm ưu thế và họ đang phải trả bao nhiêu phí để duy trì vị thế.

- **Lượng hợp đồng mở (Binance Open Interest - OI):**
    - [Giải thích]: OI tăng kèm giá tăng cho thấy dòng tiền thật đang đổ vào. OI giảm cho thấy sự rút lui của các nhà đầu tư lớn.

- **Luồng dữ liệu thanh lý (Binance Liquidation Feed):**
    - [Giải thích]: Robot theo dõi các cú "cháy" tài khoản của phe Long và phe Short. Đây thường là các điểm đảo chiều tiềm năng mà hệ thống có thể tận dụng để mua/bán.

- **Hồ sơ khối lượng (Volume Profile):**
    - [Giải thích]: Cho biết tại mức giá nào thì có nhiều giao dịch nhất, giúp robot xác định các vùng "giá trị" (Value Area).

## 26.2. Đường ống chất lượng dữ liệu (Data Quality Pipeline)

Bắt buộc phải thực thi quy trình này trước khi tiến hành bất kỳ Backtest nào để tránh lỗi "Rác vào - Rác ra" (Garbage In - Garbage Out):

1.  **Phát hiện lỗ hổng (Gap detection):** Robot phải kiểm tra tính liên tục của chuỗi thời gian. Nếu phát hiện thiếu dù chỉ 1 phút, hệ thống phải gắn cờ báo động ngay lập tức, tuyệt đối không được tự ý điền giá giả một cách thầm lặng.
2.  **Phát hiện giá ngoại lai (Outlier detection):** Sử dụng các thuật toán thống kê (như Z-score) để tìm các cây nến "râu" phi lý. Những trường hợp này phải được đẩy vào một hàng chờ để con người kiểm duyệt thủ công (Manual Review Queue).
3.  **Đánh dấu bảo trì sàn giao dịch:** Các khoảng thời gian sàn Binance bảo trì phải được đánh dấu rõ ràng và loại trừ khỏi các tính toán về hiệu quả giao dịch.
4.  **Lấp đầy dữ liệu tiến (Forward-fill):** Chỉ được phép áp dụng cho các khoảng trống dữ liệu nhỏ hơn 5 phút để đảm bảo tính nhất quán của các chỉ báo kỹ thuật.
5.  **Xác thực Schema:** Kiểm tra cấu trúc và định dạng của dữ liệu ở mỗi bước nhập (Ingest) để tránh lỗi kiểu dữ liệu trong lúc robot đang chạy.

## 26.3. Các nguồn dữ liệu tùy chọn (Optional)

- **Chỉ số Sợ hãi & Tham lam (Fear & Greed Index):** Cung cấp thêm bối cảnh tâm lý đám đông.
- **Dòng vốn Bitcoin ETF (Sau năm 2024):** Theo dõi lực mua/bán từ các tổ chức tài chính lớn tại Mỹ.
- **Lịch kinh tế vĩ mô:** Theo dõi ngày công bố CPI, cuộc họp Fed để robot có thể tạm dừng trước các tin tức biến động mạnh.
- **Phân tích tâm lý tin tức (FinGPT):** Sử dụng AI ngôn ngữ để đọc hiểu các tiêu đề tin tức trên thế giới.

---

# 27. Bảo mật hệ thống (Security)

Bảo mật là ưu tiên hàng đầu, vì lỗi code có thể sửa được, nhưng tiền bị mất do hack thì không bao giờ lấy lại được.

| Lĩnh vực | Yêu cầu kỹ thuật chi tiết | [Giải thích chuyên sâu] |
|---|---|---|
| **Khóa API (API Keys)** | Chỉ cấp quyền Giao dịch (Trade-only), Tuyệt đối CẤM Rút tiền (Withdrawal disabled), Giới hạn địa chỉ IP (IP-whitelisted). | Đảm bảo rằng dù hacker có chiếm được khóa API, chúng cũng chỉ có thể mua bán trong tài khoản của bạn chứ không thể rút tiền đi nơi khác. |
| **Lưu trữ bí mật** | Sử dụng HashiCorp Vault hoặc Cloud KMS; Tuyệt đối không để khóa trong code hoặc các file môi trường (.env) được đẩy lên Git. | Tránh việc rò rỉ thông tin nhạy cảm qua mã nguồn hoặc các cuộc tấn công vào hệ thống quản lý phiên bản. |
| **Ví lạnh (Cold Storage)** | Sử dụng ví cứng (Hardware wallet) hoặc ví đa chữ ký (Multisig) cho toàn bộ số BTC thuộc giỏ Lõi. | Đây là "phòng tuyến" cuối cùng. 80% tài sản của bạn phải nằm ngoại tuyến, tách biệt hoàn toàn với internet. |
| **Hạn mức sàn (Hot exchange cap)** | Không bao giờ để quá 25% tổng lượng BTC trên một sàn giao dịch duy nhất. | Giảm thiểu thiệt hại nếu chẳng may sàn giao dịch bị phá sản (như vụ FTX) hoặc bị hack hệ thống ví nóng. |
| **Ẩn nhật ký (Log redaction)** | Tuyệt đối không được ghi Khóa API hoặc Bí mật vào file Log; ẩn thông tin số dư chi tiết khi chia sẻ file Log. | Ngăn chặn việc vô tình lộ thông tin bảo mật qua các công cụ giám sát hoặc khi gửi file Log cho kỹ thuật viên. |
| **Mạng lưới (Network)** | Hệ thống phải chạy đằng sau lớp VPN; chỉ cho phép kết nối tới các sàn giao dịch đã được xác nhận. | Bảo vệ robot khỏi các cuộc tấn công rà quét từ bên ngoài internet. |
| **Nhật ký kiểm toán (Audit log)** | Mọi lệnh đặt, mọi thay đổi trạng thái AI phải được ghi lại vĩnh viễn dưới dạng Append-only (chỉ thêm, không sửa). | Giúp bạn có thể truy cứu 100% các hành động của robot vào bất kỳ thời điểm nào trong quá khứ. |
| **Phục hồi thảm họa** | Trạng thái danh mục phải có khả năng tái tạo lại hoàn toàn từ lịch sử giao dịch của sàn và sổ cái nội bộ. | Nếu máy chủ bị nổ, bạn vẫn có thể khôi phục lại "bộ não" của robot trên một máy chủ mới dựa trên các bản sao lưu. |

---

# 28. Chiến lược kiểm thử (Testing Strategy)

Robot phải được thử thách trong những môi trường khắc nghiệt nhất trước khi được tin tưởng giao phó tài sản.

## 28.1. Kiểm thử đơn vị (Unit Tests)

Các thành phần nhỏ nhất phải chạy đúng 100%:
- **Toán học quản lý kho:** Kiểm tra các hàm thêm/bớt lô hàng (lot), tính toán giá vốn trung bình (cost basis) phải chính xác đến từng con số thập phân.
- **Đầu ra bộ phân loại trạng thái:** Đảm bảo nhãn trạng thái (Regime) luôn có định dạng đúng và không bị nhảy loạn xạ.
- **Tính xác định của lưới:** Với cùng một dữ liệu đầu vào, bộ máy xây dựng lưới phải cho ra kết quả giống hệt nhau ở mọi lần chạy.

## 28.2. Kiểm thử thuộc tính (Property-Based Tests)

Sử dụng phương pháp kiểm thử dựa trên giả thuyết (Hypothesis) để kiểm tra các Quy tắc bất biến (Invariants) trên hàng triệu dữ liệu ngẫu nhiên:
- **Kiểm thử INV-1:** Chứng minh bằng toán học rằng không có bất kỳ chuỗi thao tác mua bán nào có thể làm giảm lượng BTC trong giỏ Lõi.
- **Kiểm thử INV-3:** Đảm bảo tổng tài sản trong các giỏ luôn khớp với tổng danh mục (bảo toàn vốn).
- **Tính nhất quán giá vốn:** Kiểm tra xem giá vốn trung bình có được tính đúng theo phương pháp FIFO ngay cả khi các lô hàng được nhập vào không theo thứ tự thời gian.

## 28.3. Kiểm thử chạy lại (Replay Tests)

- **Backtest lịch sử:** Chạy lại toàn bộ diễn biến thị trường các năm 2021, 2022, 2023, 2024. Robot phải đưa ra kết quả duy nhất và không đổi (Deterministic output).
- **Kiểm thử Snapshot:** Chụp ảnh trạng thái danh mục tại những ngày "đen tối" trong quá khứ (ví dụ ngày sập FTX) và so sánh với giá trị mong đợi để đảm bảo robot xử lý đúng tình huống.

## 28.4. Kiểm thử hỗn loạn (Chaos Tests - Bắt buộc trước khi chạy thật)

Giả lập các tình huống "ác mộng" để xem robot ứng phó thế nào:
- **Sàn bị sập:** Giả lập lỗi API 500 hoặc ngắt kết nối WebSocket đột ngột.
- **Lệnh bị lỗi:** Giả lập tình huống lệnh chỉ khớp được một nửa hoặc bị sàn từ chối do thiếu thanh khoản.
- **Stablecoin mất giá:** Giả lập kịch bản USDT sập về 0.95 USD. Robot phải biết đóng băng giao dịch và báo động.
- **Mất dữ liệu:** Giả lập các khoảng trống dữ liệu lớn khi đang giao dịch.

---

# 29. Lộ trình phát triển 7 giai đoạn (Development Roadmap)

Việc xây dựng ABAS v2 là một cuộc marathon, không phải là chạy nước rút.

## Giai đoạn 1 — Nguyên mẫu dựa trên quy tắc (Rule-Based Prototype)

**Mục tiêu cốt lõi:** Xây dựng nền móng vững chắc về quản lý kho và logic giao dịch. **Chưa sử dụng AI trong giai đoạn này.**

- **Các sản phẩm bàn giao (Deliverables):**
    1.  Bộ theo dõi giá vốn (Cost basis tracker).
    2.  Máy trạng thái danh mục đầu tư (Portfolio state machine) với các Quy tắc bất biến (Invariants) được thực thi nghiêm ngặt.
    3.  Logic mua/bán dựa trên các quy tắc toán học thuần túy.
    4.  Hệ thống Backtest hoàn chỉnh với mô hình phí và trượt giá thực tế.
- **Tiêu chí để "tốt nghiệp" (Exit criteria):**
    - Toàn bộ các Quy tắc bất biến phải giữ vững trong 5 năm lịch sử chạy thử nghiệm.
    - Chiến lược phải thắng được mốc HODL trong ít nhất một chu kỳ đầy đủ (ví dụ 2020–2023) với giả định mức phí sàn là 0.10%.

## Giai đoạn 2 — Thử nghiệm lịch sử chuyên sâu (Historical Backtesting)

Kiểm tra khả năng chịu đựng của hệ thống qua các thời kỳ lịch sử khác nhau:

| Chu kỳ | Mục đích kiểm tra |
|---|---|
| **2018–2019** | Kiểm tra khả năng tích lũy trong thị trường Gấu và giai đoạn phục hồi sớm. |
| **2020–2021** | Kiểm tra khả năng gồng lãi và không bị "bán hớ" trong siêu sóng tăng. |
| **2022** | Kiểm tra khả năng **Sống sót** và bảo toàn vốn dự trữ khi thị trường sụp đổ mạnh. |
| **2023** | Kiểm tra khả năng chuyển đổi trạng thái khi thị trường bắt đầu hồi phục. |
| **2024** | Kiểm tra khả năng thích ứng với dòng tiền từ các quỹ ETF tài chính truyền thống. |

- **Tiêu chí tốt nghiệp:**
    - Chỉ số `Δ_BTC vs HODL` phải lớn hơn 0 trong ít nhất 3 trên 5 chu kỳ sau khi đã trừ hết phí và thuế.
    - Mức sụt giảm lượng BTC (Max drawdown) phải luôn thấp hơn mức sụt giảm của chiến lược HODL.

## Giai đoạn 3 — Lớp phủ AI (AI Overlay)

Bổ sung thêm "trí thông minh" cho hệ thống:
- Tích hợp bộ nhận diện trạng thái thị trường (HMM / Clustering).
- Cho phép điều chỉnh quy mô giải ngân vốn (Sizing) dựa trên trạng thái thị trường.
- **Lưu ý:** Vẫn giữ nguyên logic cốt lõi dựa trên các quy tắc an toàn ở Giai đoạn 1.
- **Tiêu chí tốt nghiệp:** Bộ phân loại trạng thái hoạt động ổn định (không bị nhảy nhãn liên tục); Cải thiện được ít nhất 20% chỉ số tích lũy BTC so với Giai đoạn 2.

## Giai đoạn 4 — Tối ưu hóa bằng Học tăng cường (RL Optimization)

Sử dụng AI cấp cao để tinh chỉnh các tham số:
- Khoảng cách các tầng lưới.
- Đường cong giải ngân quỹ dự trữ.
- Tỷ lệ bán tối ưu cho từng trạng thái.
- **Yêu cầu kỹ thuật:** Trình mô phỏng thị trường phải vượt qua các bài kiểm tra thực tế; AI phải được huấn luyện khởi đầu bằng Offline RL; Chỉ số PBO (Học vẹt) phải < 0.5.

## Giai đoạn 5 — Giao dịch giả lập (Paper Trading)

- Chạy trên dữ liệu thời gian thực nhưng không dùng tiền thật.
- Thời gian thử nghiệm: Ít nhất 3 tháng (tốt nhất là 6 tháng).
- Theo dõi sát sao: Độ trễ mạng, mức độ trượt giá thực tế và chất lượng khớp lệnh so với mô hình lý thuyết.
- **Tiêu chí tốt nghiệp:** Hiệu quả thực tế chênh lệch không quá 20% so với dự báo của Backtest; Không có bất kỳ vi phạm Quy tắc bất biến nào.

## Giai đoạn 6 — Triển khai vốn thật (Small Capital Deployment)

- Bắt đầu với số vốn rất nhỏ (≤ 1% tổng số vốn dự kiến).
- Chỉ nâng quy mô vốn (Scale-up) sau ít nhất 3 tháng nếu kết quả chạy thật khớp với kết quả giao dịch giả lập.
- Thực hiện đánh giá lại toàn bộ hệ thống hàng tháng trước khi nâng thêm vốn.

## Giai đoạn 7 — Mô-đun Funding Delta-Neutral (Tùy chọn)

- Chỉ triển khai khi hệ thống lõi ở Giai đoạn 6 đã chạy ổn định và an toàn.

---

# 30. Sổ tay xử lý lỗi (Failure Mode Playbook)

Đừng bao giờ hành động theo cảm tính khi có sự cố. Hãy tuân thủ quy trình đã định sẵn:

| Loại lỗi | Dấu hiệu nhận biết (Trigger) | Hành động phản ứng ngay lập tức |
|---|---|---|
| **Nghiện giao dịch (Overtrading)** | Số lệnh/tháng vượt ngưỡng quy định HOẶC tỷ lệ phí sàn chiếm > 20% lợi nhuận. | Nới rộng khoảng cách lưới, tăng ngưỡng lợi nhuận mục tiêu, giảm hệ số nhân lệnh bán. |
| **Bán quá nhiều Bitcoin** | Lượng BTC trong giỏ Giao dịch giảm xuống dưới mức sàn `trading_floor`. | Tạm dừng toàn bộ các lệnh bán, đánh giá lại cơ chế chặn bán (sell-gating). |
| **Học vẹt (Overfitting)** | Hiệu quả chạy thật kém hơn kết quả Backtest > 30% trong vòng 3 tháng. | Quay lại Giai đoạn phát triển trước đó (N-1), huấn luyện lại AI với dữ liệu sạch hơn. |
| **Hết tiền bắt đáy** | Quỹ dự trữ USDT thấp hơn mức sàn `reserve_floor` khi giá đang sập sâu. | Tạm dừng mọi lệnh mua mới, đối soát lại đường cong giải ngân vốn và hệ số nhân trạng thái. |
| **Stablecoin mất giá** | Giá USDT hoặc USDC lệch mốc $1 quá 2%. | Đóng băng mọi lệnh liên quan đến đồng Stablecoin đó, chuyển đổi sang đồng Stablecoin còn an toàn. |
| **Sàn giao dịch lỗi** | Tỷ lệ lỗi API > 5% trong vòng 5 phút liên tục. | Kích hoạt Công tắc ngắt (Kill switch), chuyển hướng giao dịch sang sàn dự phòng (nếu có). |
| **Biến cố pháp lý** | Sàn giao dịch bị hạn chế tại khu vực sinh sống của bạn. | Rút toàn bộ số BTC lướt sóng về ví lạnh, tạm dừng toàn bộ hệ thống. |
| **Mô hình AI bị lệch (Drift)** | Độ tự tin (Confidence score) của AI sụt giảm mạnh. | Chuyển robot về chế độ chạy bằng Quy tắc cứng (Rule-only) và huấn luyện lại AI. |
| **Vi phạm Quy tắc bất biến** | Bất kỳ Quy tắc INV-* nào bị báo sai (False). | **DỪNG TOÀN BỘ HỆ THỐNG NGAY LẬP TỨC.** Yêu cầu con người kiểm tra thủ công toàn diện. |

**Nguyên tắc vàng:** Mọi tình huống lỗi đều phải có tên gọi và cách xử lý đã được thống nhất trước. Không được phép ngẫu hứng khi hệ thống đang vận hành thật.

---

# 31. Chẩn đoán các kịch bản thất bại thường gặp (Diagnostics)

Để biết hệ thống đang "ốm" ở đâu, hãy nhìn vào các triệu chứng sau:

## F1 — Nghiện giao dịch (Overtrading)
- **Triệu chứng:** Giao dịch liên tục không nghỉ, bị phí sàn bào mòn hết lợi nhuận, lượng BTC trong ví giảm dần dù tổng tiền USDT có thể vẫn tăng nhẹ.
- **Cách chữa:** Tăng ngưỡng lợi nhuận mục tiêu cho mỗi lệnh, nới rộng khoảng cách giữa các tầng lưới.

## F2 — Bán quá nhiều BTC (Selling Too Much)
- **Triệu chứng:** Số dư USDT tăng mạnh, lượng BTC sụt giảm nhanh chóng, bỏ lỡ hoàn toàn các đợt tăng giá mạnh nhất của thị trường.
- **Cách chữa:** Giảm hệ số nhân bán khi AI nhận diện trạng thái Bull Trend, nâng mức sàn dự trữ BTC giao dịch (`trading_floor`).

## F3 — Học vẹt (Overfitting)
- **Triệu chứng:** Kết quả Backtest quá hoàn hảo nhưng khi chạy thật (hoặc chạy giả lập) thì kết quả cực kỳ tệ.
- **Cách chữa:** Áp dụng quy trình xác thực chặt chẽ hơn (CPCV), thu hẹp phạm vi điều chỉnh của AI, kéo dài thời gian chạy giả lập.

## F4 — Sai lầm quản lý quỹ dự trữ (No Reserve Management)
- **Triệu chứng:** Tiêu hết sạch tiền mặt ngay từ khi giá mới bắt đầu giảm nhẹ, dẫn đến khi giá về đáy thực sự thì không còn đồng nào để bắt đáy.
- **Cách chữa:** Sử dụng mô hình giải ngân vốn theo bậc thang, áp dụng hệ số nhân trạng thái nghiêm ngặt để "kiềm chế" robot.

---

# 32. Tóm tắt kiến trúc AI (AI Architecture Summary)

Chúng ta xây dựng AI theo mô hình phân lớp bảo mật để đảm bảo tính giải thích được và sự an toàn:

## Mô hình KHUYẾN NGHỊ:
```
Lõi dựa trên các Quy tắc toán học (Rule-Based Core)
    +
Nhận diện trạng thái thị trường bằng HMM / Học máy không giám sát
    +
Lớp tối ưu hóa bằng Học tăng cường (RL) cho các tham số giới hạn
    +
Lớp phủ rủi ro cứng (Risk Overlay) + Các quy tắc bất biến + Công tắc ngắt
```

## Mô hình KHÔNG KHUYẾN NGHỊ:
```
Robot AI tự trị hoàn toàn (End-to-End Autonomous AI Trader)
```
**Lý do:** Loại này cực kỳ kém ổn định, không thể giải thích được lý do tại sao nó lại ra lệnh mua/bán, và khi nó hỏng, nó sẽ phá hủy tài khoản của bạn một cách âm thầm mà bạn không biết tại sao.

---

# 33. Hệ sinh thái FinRL hỗ trợ

Dự án ABAS v2 tận dụng những tinh hoa từ cộng đồng mã nguồn mở FinRL:

| Dự án / Thư viện | Vai trò cụ thể trong hệ thống ABAS |
|---|---|
| **FinRL** | Cung cấp nền tảng Học tăng cường (RL) cơ bản cho tài chính. |
| **FinRL_Crypto** | Cung cấp các phương pháp xác thực hiện đại dành riêng cho tiền điện tử (CPCV, PBO). |
| **FinRL-X** | Tham chiếu về kiến trúc hệ thống Module hóa giúp dễ dàng bảo trì. |
| **FinGPT** | (Tùy chọn) Trích xuất các đặc trưng từ tin tức và tâm lý thị trường toàn cầu. |
| **LangGraph** | (Tùy chọn) Điều phối hoạt động giữa các tác nhân AI khác nhau. |

---

# 34. Tầm nhìn chiến lược (Strategic Insight)

Hãy luôn ghi nhớ bản chất của hệ thống này:

Hệ thống hành xử như:
**Một người quản lý kho Bitcoin kỷ luật, lạnh lùng và kiên định.**

**KHÔNG PHẢI** là:
**Một cỗ máy dự đoán giá quá khích luôn tìm cách "ăn thua" với thị trường hàng ngày.**

---

# 35. Mục tiêu tối thượng (Ultimate Goal)

```
Tối đa hóa quyền sở hữu Bitcoin xuyên suốt nhiều chu kỳ thị trường,
Sau khi đã hoàn tất mọi nghĩa vụ về chi phí giao dịch và thuế,
Đạt được kết quả thắng mốc HODL về mặt số lượng BTC một cách đo lường được,
Trong khi luôn bảo vệ tuyệt đối số vốn của chủ nhân trước các biến động cực đoan và rủi ro đối tác.
```

Đó là cách duy nhất để bạn có được sự tự do tài chính bền vững cùng Bitcoin.

---

# 36. Các câu hỏi thường gặp (Q&A - Mở rộng)

Trong quá trình thiết kế hệ thống ABAS v2, có một số câu hỏi then chốt mà nhà phát triển thường đặt ra:

**Hỏi: Tại sao không dùng AI để dự đoán giá BTC trong 5 phút tới?**
*Trả lời:* Dự đoán giá ngắn hạn cực kỳ nhiễu. Nếu robot sai 51% số lần, phí giao dịch sẽ bào mòn tài khoản của bạn rất nhanh. ABAS tập trung vào "Trạng thái" (Regime) vì trạng thái thị trường có tính bền vững hơn nhiều so với hướng đi của một cây nến lẻ loi.

**Hỏi: Quỹ dự trữ 20% USDT có quá nhiều không khi đang trong sóng tăng (Bull market)?**
*Trả lời:* Trong sóng tăng, cảm giác cầm tiền mặt rất khó chịu (FOMO). Tuy nhiên, lịch sử cho thấy ngay cả trong sóng tăng mạnh nhất, BTC vẫn có những cú sập "cháy tài khoản" 20-30%. Nếu không có quỹ dự trữ này, bạn sẽ mất cơ hội mua rẻ nhất và không có gì để bảo vệ tài khoản nếu sóng tăng kết thúc đột ngột.

**Hỏi: Tại sao lại ưu tiên ví lạnh cho giỏ Lõi (Core)?**
*Trả lời:* Sàn giao dịch là nơi để giao dịch, không phải nơi để cất tiền. Vụ sụp đổ của FTX hay Mt.Gox là bài học xương máu. 80% tài sản của bạn phải nằm ở nơi mà chỉ có bạn giữ chìa khóa. Robot chỉ được phép "chơi" trên 20% tài sản lướt sóng.

**Hỏi: Nếu tôi muốn tích lũy thêm các đồng coin khác (ETH, SOL) thì sao?**
*Trả lời:* ABAS v2 được thiết kế riêng cho Bitcoin vì tính chất "tiền cứng" của nó. Nếu muốn áp dụng cho Altcoin, bạn cần điều chỉnh lại các tham số về độ biến động (Volatility) vì Altcoin rung lắc mạnh hơn BTC rất nhiều, và hệ số sụt giảm (Drawdown) cũng phải nới rộng hơn.

**Hỏi: Bao lâu thì nên huấn luyện lại (Retrain) mô hình AI?**
*Trả lời:* Thị trường Crypto thay đổi cấu trúc rất nhanh (đặc biệt là sau khi có các quỹ ETF). Khuyến nghị huấn luyện lại bộ phân loại trạng thái (HMM) mỗi 3 tháng một lần hoặc sau mỗi biến cố thị trường lớn.

**Hỏi: Tôi có cần máy chủ cực mạnh để chạy ABAS không?**
*Trả lời:* Phần vận hành (Execution) không tốn nhiều tài nguyên, có thể chạy trên một máy chủ ảo (VPS) cấu hình trung bình. Tuy nhiên, phần huấn luyện AI (RL Training) sẽ cần máy tính có GPU mạnh để chạy các trình mô phỏng thị trường hàng triệu lần.

**Hỏi: Điều gì xảy ra nếu internet của tôi bị mất khi robot đang đặt lệnh?**
*Trả lời:* Đó là lý do chúng ta có **Kiểm thử hỗn loạn (Chaos Testing)**. Robot phải có cơ chế kiểm tra lại trạng thái lệnh ngay khi có mạng trở lại. Nếu lệnh đang lửng lơ, nó phải hủy hoặc đối soát lại để đảm bảo không vi phạm các Quy tắc bất biến.

---

### [LỜI KẾT TỪ ĐỘI NGŨ THIẾT KẾ]

Bản kế hoạch ABAS v2 này là một tài liệu sống. Nó không chỉ là những dòng code, nó là một tư duy đầu tư kỷ luật. Khi bạn xây dựng hệ thống này, bạn đang xây dựng một pháo đài tài chính cho chính mình. Hãy kiên nhẫn, hãy cẩn trọng trong từng bước kiểm thử, và luôn nhớ rằng: **Mục tiêu là Bitcoin, không phải những con số USD nhảy múa tạm thời.**

---
*Chúc bạn thành công trên con đường trở thành một "Inventory Manager" thực thụ của Bitcoin!*

---

# 37. Tuyên bố miễn trừ trách nhiệm (Disclaimer)

Tài liệu này được biên soạn cho mục đích nghiên cứu và giáo dục về hệ thống giao dịch tự động. Đầu tư vào tiền điện tử, đặc biệt là Bitcoin, luôn tiềm ẩn rủi ro mất vốn rất cao. 

1.  **Không phải lời khuyên tài chính:** Toàn bộ nội dung trong bản kế hoạch ABAS v2 này không cấu thành lời khuyên đầu tư, lời khuyên tài chính hay bất kỳ loại lời khuyên chuyên môn nào khác.
2.  **Rủi ro kỹ thuật:** Việc vận hành robot giao dịch có thể gặp lỗi phần mềm, lỗi kết nối API hoặc các sự cố máy chủ dẫn đến thiệt hại tài sản không mong muốn.
3.  **Tự chịu trách nhiệm:** Người sử dụng tài liệu này để xây dựng hệ thống thực tế phải tự chịu hoàn toàn trách nhiệm về mọi quyết định và kết quả đầu tư của mình.

# 38. Thông tin bản quyền & Liên hệ

- **Phiên bản tài liệu:** ABAS v2.0 - Tiếng Việt (Bản siêu chi tiết).
- **Tác giả gốc:** Đội ngũ Nghiên cứu Giao dịch Thuật toán (Trading Research Team).
- **Ngày hoàn thiện bản dịch:** 10/05/2026.
- **Giấy phép:** Tài liệu này mang tính chất nội bộ và thuộc bản quyền của dự án. Tất cả các quyền được bảo lưu (Proprietary. All rights reserved).

---
*End of Document - Tài liệu kết thúc tại đây.*
