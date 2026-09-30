import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="K4-L3B Day 13 Monitoring & LLMOps",
    layout="wide",
)

st.title("K4-L3B Day 13 Monitoring & LLMOps")

LOG_PATH = Path("data/logs.jsonl")

def load_logs():
    if not LOG_PATH.exists():
        return pd.DataFrame()
    records = []
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    continue
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    if "ts" in df.columns:
        df["ts"] = pd.to_datetime(df["ts"])
    return df

df = load_logs()

if df.empty:
    st.warning("Chưa có dữ liệu log trong data/logs.jsonl. Hãy chạy load_test.py trước.")
    st.stop()

# Tách log theo event
responses = df[df["event"] == "response_sent"].copy()
requests = df[df["event"] == "request_received"].copy()
failures = df[df["event"] == "request_failed"].copy()

# ==================== HÀNG 1 ====================
col1, col2 = st.columns(2)

# Panel 1: Latency percentiles and TTFT
with col1:
    st.subheader("1. Latency percentiles and TTFT")
    if not responses.empty and "latency_ms" in responses.columns:
        latencies = responses["latency_ms"].dropna()
        ttfts = responses["ttft_ms"].dropna() if "ttft_ms" in responses.columns else pd.Series([])

        p50 = float(np.percentile(latencies, 50)) if len(latencies) else 0.0
        p95 = float(np.percentile(latencies, 95)) if len(latencies) else 0.0
        p99 = float(np.percentile(latencies, 99)) if len(latencies) else 0.0
        ttft_p95 = float(np.percentile(ttfts, 95)) if len(ttfts) else 0.0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("p50", f"{p50:.1f} ms")
        m2.metric("p95", f"{p95:.1f} ms")
        m3.metric("p99", f"{p99:.1f} ms")
        m4.metric("ttft_p95", f"{ttft_p95:.1f} ms")

        # Threshold check
        status = "PASSED (<= 3000 ms)" if p95 <= 3000 else "VIOLATED (> 3000 ms)"
        st.caption(f"**Threshold (p95 <= 3000 ms):** {status}")
        
        # Biểu đồ phân bổ
        st.line_chart(responses.set_index("ts")[["latency_ms"]])
    else:
        st.info("Chưa có dữ liệu response_sent")

# Panel 2: Request traffic
with col2:
    st.subheader("2. Request traffic")
    total_req = len(requests)
    if not requests.empty and "ts" in requests.columns:
        requests_ts = requests.set_index("ts").resample("1min").count()["event"]
        current_rate = float(requests_ts.iloc[-1]) if len(requests_ts) else 0.0
        
        t1, t2 = st.columns(2)
        t1.metric("Total Requests", total_req)
        t2.metric("Rate / min", f"{current_rate:.1f} req/m")

        status = "PASSED (>= 1)" if current_rate >= 1 else "BELOW TARGET (< 1)"
        st.caption(f"**Threshold (rate_per_minute >= 1):** {status}")
        
        st.bar_chart(requests_ts)
    else:
        st.metric("Total Requests", total_req)

st.divider()

# ==================== HÀNG 2 ====================
col3, col4 = st.columns(2)

# Panel 3: Error rate and retrieval success
with col3:
    st.subheader("3. Error rate and retrieval success")
    total_req_count = len(requests)
    fail_count = len(failures)
    error_rate_pct = (fail_count / total_req_count * 100) if total_req_count > 0 else 0.0

    tool_successes = responses["tool_success"].dropna() if "tool_success" in responses.columns else pd.Series([])
    tool_success_rate = (tool_successes.sum() / len(tool_successes) * 100) if len(tool_successes) > 0 else 100.0

    e1, e2, e3 = st.columns(3)
    e1.metric("Error Rate", f"{error_rate_pct:.2f}%")
    e2.metric("Failed Count", fail_count)
    e3.metric("Tool Success", f"{tool_success_rate:.1f}%")

    status = "PASSED (<= 2%)" if error_rate_pct <= 2 else "VIOLATED (> 2%)"
    st.caption(f"**Threshold (error_rate_pct <= 2%):** {status}")

    if not failures.empty and "error_type" in failures.columns:
        st.write("Error distribution:")
        st.dataframe(failures["error_type"].value_counts(), use_container_width=True)

# Panel 4: Cost over time
with col4:
    st.subheader("4. Cost over time")
    if not responses.empty and "cost_usd" in responses.columns:
        total_cost = float(responses["cost_usd"].sum())
        cost_ts = responses.set_index("ts").resample("1min")["cost_usd"].sum()

        c1, c2 = st.columns(2)
        c1.metric("Total Cost", f"${total_cost:.5f}")
        c2.metric("Latest 1m Cost", f"${cost_ts.iloc[-1]:.5f}" if len(cost_ts) else "$0.0")

        status = "PASSED (<= $2.5)" if total_cost <= 2.5 else "VIOLATED (> $2.5)"
        st.caption(f"**Threshold (total <= $2.5):** {status}")

        st.area_chart(cost_ts)
    else:
        st.metric("Total Cost", "$0.0")

st.divider()

# ==================== HÀNG 3 ====================
col5, col6 = st.columns(2)

# Panel 5: Input and output tokens
with col5:
    st.subheader("5. Input and output tokens")
    if not responses.empty and "tokens_in" in responses.columns and "tokens_out" in responses.columns:
        sum_in = int(responses["tokens_in"].sum())
        sum_out = int(responses["tokens_out"].sum())
        total_tokens = sum_in + sum_out

        k1, k2, k3 = st.columns(3)
        k1.metric("Tokens In", f"{sum_in:,}")
        k2.metric("Tokens Out", f"{sum_out:,}")
        k3.metric("Total Tokens", f"{total_tokens:,}")

        status = "PASSED (<= 50,000)" if total_tokens <= 50000 else "VIOLATED (> 50,000)"
        st.caption(f"**Threshold (sum_by_field <= 50,000):** {status}")

        tokens_df = responses.set_index("ts")[["tokens_in", "tokens_out"]]
        st.line_chart(tokens_df)
    else:
        st.info("Chưa có dữ liệu tokens")

# Panel 6: Quality proxy
with col6:
    st.subheader("6. Quality proxy")
    if not responses.empty and "quality_score" in responses.columns:
        mean_quality = float(responses["quality_score"].mean())

        q1, _ = st.columns([1, 2])
        q1.metric("Mean Quality Score", f"{mean_quality:.2f} / 1.0")

        status = "PASSED (>= 0.75)" if mean_quality >= 0.75 else "BELOW TARGET (< 0.75)"
        st.caption(f"**Threshold (mean >= 0.75):** {status}")

        st.line_chart(responses.set_index("ts")[["quality_score"]])
    else:
        st.info("Chưa có dữ liệu quality_score")