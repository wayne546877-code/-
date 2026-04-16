import streamlit as st
from moralis import evm_api
import requests
import pandas as pd
import time
import os

# ==========================================
# 🛠️ 核心内置配置 (API Keys)
# ==========================================
# BSC 使用的 Moralis Key
BSC_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6IjY1ZmY0OWNiLWI2YTAtNDgwZC1hNjcyLTZiMDZmYjM2OTlkOCIsIm9yZ0lkIjoiNTA4NTM3IiwidXNlcklkIjoiNTIzMjQxIiwidHlwZSI6IlBST0pFQ1QiLCJ0eXBlSWQiOiIyMGNjMDVkYS1kYzI1LTQxNjUtYjYxNS1hY2NjYzMwZWU4NjMiLCJpYXQiOjE3NzU0ODQxODcsImV4cCI6NDkzMTI0NDE4N30.lKDIBSKI5u5M9KsQ39TFfOyrpJ1Sw9jWayjwJlXVnDg"
# TRC 使用的 API Key
TRC_API_KEY = "685c8cd0-1c17-4301-90af-ccb0ce655f02"
# ERC 使用的 Etherscan Key
ERC_API_KEY = "A71YIBIEZHTRR4669IS65A45QEFX24EY7N"
# 系统登录密码
ACCESS_PASSWORD = "0224"

# 基础过滤名单
BASE_EXCLUDE = [
    "0x8894e0a0c962cb723c1976a4421c95949be2d4e3", # BSC Binance
    "0x55d398326f99059ff775485246999027b3197955", # BSC USDT
    "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",         # TRC USDT 合约
    "T9yD14Nj9j7xMB4UXP2VJC2Bcg5NCtoL93",         # TRC 销毁地址
    "0xdac17f958d2ee523a2206206994597c13d831ec7", # ERC USDT 合约
    "0x0000000000000000000000000000000000000000"  # 零地址
]

# --- 共通黑名单加载函数 ---
def load_common_blacklist():
    bl_file = "blacklist.txt"
    if os.path.exists(bl_file):
        with open(bl_file, "r", encoding="utf-8") as f:
            return [line.strip().lower() for line in f.readlines() if line.strip()]
    return []

# ==========================================
# 🛡️ 登录安全验证
# ==========================================
st.set_page_config(page_title="USDT 多链智能追踪系统", page_icon="🕵️", layout="wide")

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; color: #00ffcc;'>🔐 系统登录</h1>", unsafe_allow_html=True)
        pwd = st.text_input("", type="password", placeholder="请输入授权码...", label_visibility="collapsed")
        if st.button("🚀 解锁系统", use_container_width=True):
            if pwd == ACCESS_PASSWORD:
                st.session_state['authenticated'] = True
                st.rerun()
            else:
                st.error("❌ 密码错误")
    st.stop()

# ==========================================
# 🕵️ 主系统界面 (BSC & TRC & ERC 分页)
# ==========================================
st.markdown("<h1 style='text-align: center; color: #00ffcc;'>🕵️ USDT 多链关联穿透系统</h1>", unsafe_allow_html=True)

# 加载通用黑名单
common_blacklist = load_common_blacklist()

# --- 侧边栏 ---
with st.sidebar:
    st.title("⚙️ 共通设置")
    st.write(f"📁 通用黑名单: **{len(common_blacklist)}** 条")
    st.divider()
    filter_builtin = st.checkbox("启用内置基础过滤", value=True)
    
    st.divider()
    st.subheader("📝 临时临时黑名单")
    temp_input = st.text_area("本次追加屏蔽地址:", height=150)
    temp_list = [a.strip().lower() for a in temp_input.split('\n') if a.strip()]
    
    if st.button("🔴 退出系统", use_container_width=True):
        st.session_state['authenticated'] = False
        st.rerun()

# --- 汇总最终过滤名单 ---
final_exclude = set(common_blacklist)
final_exclude.update(temp_list)
if filter_builtin:
    final_exclude.update([a.lower() for a in BASE_EXCLUDE])

# ==========================================
# 📑 分页逻辑 (BSC, TRC 和 ERC)
# ==========================================
tab1, tab2, tab3 = st.tabs(["🚀 BSC 链路追踪", "💎 TRC 链路追踪", "⛓️ ERC 链路追踪"])

# ------------------------------------------
# 第一页：BSC 链路追踪 (使用 Moralis)
# ------------------------------------------
with tab1:
    st.subheader("BSC (Binance Smart Chain) 穿透模式")
    col_bsc1, col_bsc2 = st.columns([3, 1])
    with col_bsc1:
        bsc_addr = st.text_input("输入 BSC 钱包地址:", key="bsc_input", placeholder="0x...")
    with col_bsc2:
        bsc_limit = st.select_slider("分析笔数", options=[10, 50, 100, 200, 500, 1000], value=100, key="bsc_limit")

    if st.button("开始 BSC 深度分析", type="primary", use_container_width=True):
        if not bsc_addr:
            st.warning("请先输入地址")
        else:
            target = bsc_addr.lower().strip()
            all_tx = []
            cursor = ""
            prog = st.progress(0)
            
            try:
                while len(all_tx) < bsc_limit:
                    batch = min(100, bsc_limit - len(all_tx))
                    params = {"address": target, "chain": "bsc", "limit": batch}
                    if cursor: params["cursor"] = cursor
                    
                    res = evm_api.token.get_wallet_token_transfers(api_key=BSC_API_KEY, params=params)
                    data = res.get("result", [])
                    all_tx.extend(data)
                    prog.progress(min(1.0, len(all_tx)/bsc_limit))
                    cursor = res.get("cursor")
                    if not cursor or not data: break
                    time.sleep(0.2)
                
                # 提取去重
                associates = set()
                for tx in all_tx:
                    f, t = (tx.get("from_address") or "").lower(), (tx.get("to_address") or "").lower()
                    for a in [f, t]:
                        if a and a != target and a not in final_exclude:
                            associates.add(a)
                
                st.success(f"BSC 分析完成！找到 {len(associates)} 个关联地址")
                res_str = f"{bsc_addr} (BSC 查询目标)\n" + "-"*35 + "\n" + "\n".join(sorted(list(associates)))
                st.text_area("结果列表:", value=res_str, height=400, key="bsc_res")
            except Exception as e:
                st.error(f"BSC 错误: {e}")

# ------------------------------------------
# 第二页：TRC 链路追踪 (使用 Requests/TRON API)
# ------------------------------------------
with tab2:
    st.subheader("TRC (Tron Network) 穿透模式")
    col_trc1, col_trc2 = st.columns([3, 1])
    with col_trc1:
        trc_addr = st.text_input("输入 TRC 钱包地址:", key="trc_input", placeholder="T...")
    with col_trc2:
        trc_limit = st.number_input("分析笔数:", min_value=10, max_value=500, value=50, key="trc_limit")

    if st.button("开始 TRC 深度分析", type="primary", use_container_width=True):
        if not trc_addr:
            st.warning("请先输入地址")
        else:
            target = trc_addr.strip()
            try:
                # TRON API 调用逻辑 (基于 Tokenview/TronGrid 结构)
                url = f"https://services.tokenview.io/vipapi/txlist/{target}/1/{trc_limit}?apikey={TRC_API_KEY}"
                response = requests.get(url).json()
                
                if response.get("code") != 1:
                    st.error(f"TRC API 报错: {response.get('msg')}")
                else:
                    txs = response.get("data", [])
                    associates = set()
                    for tx in txs:
                        f, t = tx.get("from").lower(), tx.get("to").lower()
                        for a in [f, t]:
                            # 转换为小写比对，并剔除
                            if a and a != target.lower() and a not in final_exclude:
                                associates.add(a)
                    
                    st.success(f"TRC 分析完成！找到 {len(associates)} 个关联地址")
                    res_str = f"{trc_addr} (TRC 查询目标)\n" + "-"*35 + "\n" + "\n".join(sorted(list(associates)))
                    st.text_area("结果列表:", value=res_str, height=400, key="trc_res")
            except Exception as e:
                st.error(f"TRC 系统错误: {e}")

# ------------------------------------------
# 第三页：ERC 链路追踪 (使用 Etherscan API)
# ------------------------------------------
with tab3:
    st.subheader("ERC (Ethereum Network) 穿透模式")
    col_erc1, col_erc2 = st.columns([3, 1])
    with col_erc1:
        erc_addr = st.text_input("输入 ERC 钱包地址:", key="erc_input", placeholder="0x...")
    with col_erc2:
        erc_limit = st.number_input("分析笔数:", min_value=10, max_value=100, value=50, key="erc_limit")

    if st.button("开始 ERC 深度分析", type="primary", use_container_width=True):
        if not erc_addr:
            st.warning("请先输入地址")
        else:
            target = erc_addr.lower().strip()
            try:
                # 使用 Etherscan API 获取 ERC-20 代币转移记录
                url = f"https://api.etherscan.io/api?module=account&action=tokentx&address={target}&page=1&offset={erc_limit}&sort=desc&apikey={ERC_API_KEY}"
                response = requests.get(url).json()
                
                if response.get("status") != "1":
                    st.error(f"ERC API 报错: {response.get('message')}")
                else:
                    txs = response.get("result", [])
                    associates = set()
                    for tx in txs:
                        f, t = tx.get("from").lower(), tx.get("to").lower()
                        for a in [f, t]:
                            if a and a != target and a not in final_exclude:
                                associates.add(a)
                    
                    st.success(f"ERC 分析完成！找到 {len(associates)} 个关联地址")
                    res_str = f"{erc_addr} (ERC 查询目标)\n" + "-"*35 + "\n" + "\n".join(sorted(list(associates)))
                    st.text_area("结果列表:", value=res_str, height=400, key="erc_res")
            except Exception as e:
                st.error(f"ERC 系统错误: {e}")
