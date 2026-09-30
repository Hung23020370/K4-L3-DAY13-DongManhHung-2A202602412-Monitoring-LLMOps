# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Đồng Mạnh Hùng
- **MSSV:** 2A202602412
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/Hung23020370/K4-L3-DAY13-DongManhHung-2A202602412-Monitoring-LLMOps
- **Commit SHA cuối:** 762f83f
- **Challenge ID:** day13-k4-l3b-monitoring-llmops-v1
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602412`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 0/100 (chưa implement) | 100/100 | Log JSONL chuẩn cấu trúc, đầy đủ schema trường và correlation ID |
| `validate_dashboard.py` | 0/6 | 6/6 | Đạt chuẩn 6/6 panel hợp đồng với dashboard.yaml |
| `pytest` | Fail tests | 25 passed | Đạt 100% test cases (bao gồm test prompt trace và mock client) |
| Số traces hợp lệ | 0 | 20+ traces | Đầy đủ quan hệ cha con root -> retrieval -> generation |
| Số PII leak | Chưa scrub | 0 rò rỉ | Scrub sạch Email, Phone VN, CCCD, Credit Card |
| Latency P95 / TTFT P95 | ~150ms / 50ms | ~2670ms (khi inject) -> 151ms (sau fix) | Phản ánh chính xác qua Streamlit dashboard và Langfuse |
| Retrieval success rate | 100% | 100% | Retrieval thành công, ghi nhận đầy đủ doc_count |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:**
  - Sử dụng `CorrelationIdMiddleware` để chặn mọi HTTP request đến FastAPI.
  - Middleware kiểm tra header `x-request-id`; nếu client không gửi kèm thì tự sinh mã mới theo định dạng `req-<hex8>` (qua `uuid.uuid4().hex[:8]`).
  - Gán ID này vào ContextVar để luồng xử lý truy cập xuyên suốt, đồng thời trả lại qua response header `x-request-id`.
- **Các metadata được ghi vào structured log:**
  - `ts` (ISO 8601 UTC timestamp), `level`, `service`, `event` (`request_received`, `response_sent`, `request_failed`).
  - `correlation_id`, `user_id_hash` (băm SHA256 lấy 12 ký tự), `session_id`, `feature`, `model`, `env`.
  - Chỉ số hiệu năng: `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`.
- **Cách bảo đảm PII được scrub trước khi ghi:**
  - Cấu hình custom processor `scrub_event` trong pipeline của `structlog`.
  - Processor này duyệt đệ quy qua các dictionary/string trong `event_dict` và áp dụng bộ Regex lọc nhạy cảm trước khi log được định dạng sang JSON hoặc in ra console/file `data/logs.jsonl`.
  - Các mẫu nhạy cảm được che thành: `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CCCD]`, `[REDACTED_CREDIT_CARD]`.
- **Cách kiểm chứng kết quả:**
  - Chạy `python -m pytest tests/test_pii.py -v` (pass 100% các case).
  - Chạy script kiểm thử tự động `python scripts/validate_logs.py` đạt điểm tuyệt đối.
  - Kiểm tra trực tiếp file `data/logs.jsonl` đảm bảo không còn dữ liệu thô.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:**
  - Traces được gửi về project `day13-k4-l3b-2A202602412` trên Langfuse US Region thông qua cấu hình `LANGFUSE_BASE_URL=https://us.cloud.langfuse.com` cùng API key cá nhân trong `.env`.
  - Ảnh chụp màn hình hiển thị rõ tên project trên header.
- **Cấu trúc root/retrieval/generation observations:**
  - Root: Observation dạng Agent mang tên `lab-agent-run` (trace name: `day13-agent-request`).
  - Child Span: Span con `retrieval` ghi nhận quá trình truy xuất context tài liệu.
  - Child Generation: Observation con `generation` ghi nhận lượt gọi LLM, nhận input rendered prompt, model parameters, usage details (token in/out) và ước tính cost.
- **Cách nối trace với log:**
  - Sử dụng chung `correlation_id`. Giá trị này vừa được ghi vào trường `correlation_id` trong structured log, vừa được truyền vào metadata và tags của Langfuse Trace.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1 — gán nhãn `baseline`, `production`.
- **Version/label candidate:** Version 2 — thêm yêu cầu format ngắn gọn 1-2 câu, gán nhãn `candidate`.
- **Trace ID của mỗi version:**
  - Version 1 (`baseline`): `97d127fec96b7d3a2d2f04fdecb5eab0`
  - Version 2 (`candidate`): `7b46b204635ad1bb39c7d22009880886`
- **Cách promote và rollback `production`:**
  - **Promote:** Trên Langfuse UI, chuyển nhãn `production` từ Version 1 sang Version 2; request mới sẽ tự động nạp prompt Version 2 mà không cần sửa code.
  - **Rollback:** Khi phát hiện output không mong muốn, truy cập lại Version 1 và gán lại nhãn `production` cho Version 1. Ứng dụng lập tức chuyển về dùng prompt V1.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:**
  - Được xây dựng bằng Streamlit bám sát `config/dashboard.yaml` gồm 6 panel:
    1. *Latency percentiles and TTFT*: Đo p50, p95, p99 và TTFT p95 (ngưỡng p95 <= 3000ms).
    2. *Request traffic*: Tổng số request và tốc độ request/phút (ngưỡng >= 1 req/min).
    3. *Error rate and retrieval success*: Tỷ lệ lỗi request (<= 2%) và tỷ lệ thành công của retrieval tool.
    4. *Cost over time*: Tổng chi phí tích lũy theo phút và toàn bộ session (<= $2.5).
    5. *Input and output tokens*: Tổng lượng token in/out tiêu thụ (<= 50,000 tokens).
    6. *Quality proxy*: Điểm chất lượng trung bình dựa trên heuristic (>= 0.75).
- **SLO và lý do chọn:**
  - SLO: `Latency p95 <= 3000ms` và `Error rate <= 2%` trong khung cửa sổ đánh giá.
  - Lý do: Đảm bảo trải nghiệm tương tác trực tiếp (real-time chat) cho người dùng không bị gián đoạn hoặc cảm giác đơ lag, đồng thời giữ tỷ lệ lỗi ở mức tối thiểu.
- **Cách tính error budget:**
  - Với SLO khả dụng 98% (tương ứng Error rate <= 2%), error budget cho phép là 2%. Nếu hệ thống phục vụ 1,000 request, tối đa 20 request được phép thất bại hoặc vi phạm độ trễ trước khi cạn kiệt ngân sách lỗi.
- **Ba alert và runbook tương ứng:**
  1. *HighLatencyAlert*: Kích hoạt khi Latency p95 > 3000ms kéo dài trong 3 phút (Severity: Warning, Owner: @oncall-ops). Runbook: Kiểm tra span retrieval và kết nối database vector/model API.
  2. *HighErrorRateAlert*: Kích hoạt khi tỷ lệ request lỗi > 2% trong 2 phút (Severity: Critical, Owner: @oncall-eng). Runbook: Kiểm tra log `request_failed` tìm stack trace, kiểm tra tình trạng API backend.
  3. *CostSpikeAlert*: Kích hoạt khi chi phí tích lũy vượt $2.5 (Severity: Warning, Owner: @lead-ops). Runbook: Kiểm tra token input/output, xem xét kích hoạt caching hoặc hạ tầng model rẻ hơn.

## 7. Điều tra challenge

- **Challenge ID:** `rag_slow`
- **Khoảng thời gian điều tra:** 10:40 – 11:20 (theo timeline log/dashboard)
- **Triệu chứng từ metrics:**
  - Panel 1 (Latency percentiles) trên Dashboard vọt lên bất thường: p50 và p95 tăng từ ~150ms lên mức **~2660ms – 2673ms**, vượt mức thông thường và chạm sát ngưỡng nguy hiểm.
- **Log line và correlation ID liên quan:**
  - `correlation_id`: `req-a20e5bf9`
  - Log line trích xuất từ `data/logs.jsonl`:
    `{"service": "api", "latency_ms": 2670, "ttft_ms": 50, "tokens_in": 46, "tokens_out": 164, "cost_usd": 0.002598, "quality_score": 0.9, "tool_name": "retrieval", "tool_success": true, "event": "response_sent", "correlation_id": "req-a20e5bf9", "level": "info", "ts": "2026-09-30T04:12:00Z"}`
- **Trace ID và span gây ảnh hưởng:**
  - Trace ID: `6eed8f46d49140b0e579de9576228cdd`
  - Span gây ảnh hưởng: Span con **`retrieval`** bị kéo dài bất thường (~2500ms), trong khi span `generation` chỉ tốn ~150ms.
- **Root cause:**
  - Hàm `retrieve()` trong module RAG bị nghẽn (giả lập bởi kịch bản incident `rag_slow` chèn sleep 2.5s vào bước truy xuất dữ liệu), gây kéo dài thời gian phản hồi toàn trình của Agent.
- **Fix action:**
  - Tắt kịch bản incident bằng lệnh `python scripts/inject_incident.py --disable`.
  - Khôi phục độ trễ bình thường của khâu retrieval về < 20ms.
- **Preventive measure:**
  - Cấu hình Timeout (ví dụ `timeout=1.0s`) và cơ chế Circuit Breaker cho bước Retrieval. Nếu retrieval quá hạn, lập tức fallback sang câu trả lời mặc định hoặc dùng cache để không làm treo luồng chat.
  - Bổ sung alert cảnh báo sớm khi thời gian thực thi của riêng span `retrieval` vượt quá 500ms.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
  - Tách bạch cấu trúc cha-con cho Tracing: Bọc riêng hàm truy xuất context (`retrieval`) thành Span con và hàm sinh câu trả lời (`generation`) thành Generation con thay vì gom chung một span lớn. Quyết định này giúp cô lập chính xác vị trí phát sinh độ trễ hay lỗi (như thấy rõ ở challenge `rag_slow`) mà không cần phỏng đoán.
- **Một lỗi/blocker đã gặp:**
  - Gặp lỗi `AttributeError: 'RecordingLangfuseClient' object has no attribute 'update_current_generation'` khi chạy `pytest` cho file `test_agent_prompt_trace.py`.
- **Cách tìm nguyên nhân và xử lý:**
  - Nguyên nhân: Trong môi trường unit test, bài test sử dụng class giả lập `RecordingLangfuseClient` chỉ có sẵn `update_current_span`, không có hàm `update_current_generation` của SDK thật.
  - Xử lý: Thêm điều kiện `if hasattr(langfuse_client, "update_current_generation"):` trước khi gọi. Điều này giúp code vừa hoạt động chuẩn xác với full tính năng trên production/Langfuse runtime, vừa tương thích hoàn toàn với mock client khi chạy test.
- **Cách hiểu luồng Metrics → Logs → Traces:**
  - **Metrics:** Đóng vai trò cảnh báo sớm (Alert/Overview), cho biết *khi nào có vấn đề* và *hệ thống đang đau ở đâu* (ví dụ: Latency p95 tăng vọt).
  - **Logs:** Cung cấp ngữ cảnh theo sự kiện (Context), cho biết *sự việc gì đã xảy ra* với các thuộc tính cụ thể và chỉ ra mã định danh `correlation_id`.
  - **Traces:** Cung cấp góc nhìn chi tiết từng nhịp xử lý (Granular Waterfall), dùng `correlation_id` để đào sâu vào đúng request đó, phân tách từng span con để khẳng định chính xác *bước nào bị nghẽn/lỗi và do đâu*.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
  - Quản lý prompt qua version và label cho phép tách biệt chu kỳ release prompt khỏi chu kỳ deploy code; có thể thử nghiệm (A/B testing với candidate) và tức tốc rollback về baseline khi output suy giảm chất lượng mà không cần restart server hay build lại image.
  - Giám sát token và cost liên tục giúp tránh sự cố tràn chi phí do prompt loop hoặc output quá dài, đồng thời SLO giúp lượng hóa chất lượng cam kết với người dùng.
- **Điều quan trọng nhất đã học:**
  - Kỹ năng thiết kế hệ thống quan sát (Observability) toàn diện cho ứng dụng AI/LLM: Từ làm sạch log, chuẩn hóa Correlation ID xuyên suốt, đến phân tách span chi tiết và xây dựng Dashboard/Alert bám sát SLO thực tế.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**
  - Hệ thống cảnh báo Alert mới dừng ở mức định nghĩa rules (`alert_rules.yaml`) và runbook chứ chưa cấu hình webhook gửi trực tiếp tới kênh Slack thật.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.