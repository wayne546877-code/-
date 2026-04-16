import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import os
from moralis import evm_api

# ==========================================
# 🛠️ 核心内置配置 (TRC + BSC + ERC)
# ==========================================
TRON_API_KEY = "685c8cd0-1c17-4301-90af-ccb0ce655f02" 
MORALIS_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6IjY1ZmY0OWNiLWI2YTAtNDgwZC1hNjcyLTZiMDZmYjM2OTlkOCIsIm9yZ0lkIjoiNTA4NTM3IiwidXNlcklkIjoiNTIzMjQxIiwidHlwZSI6IlBST0pFQ1QiLCJ0eXBlSWQiOiIyMGNjMDVkYS1kYzI1LTQxNjUtYjYxNS1hY2NjYzMwZWU4NjMiLCJpYXQiOjE3NzU0ODQxODcsImV4cCI6NDkzMTI0NDE4N30.lKDIBSKI5u5M9KsQ39TFfOyrpJ1Sw9jWayjwJlXVnDg"
ETHERSCAN_API_KEY = "A71YIBIEZHTRR4669IS65A45QEFX24EY7N"

ACCESS_PASSWORD = "0224"

BASE_EXCLUDE = [
    "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t", 
    "T9yD14Nj9j7xMB4UXP2VJC2Bcg5NCtoL93", 
    "0x55d398326f99059ff775485246999027b3197955", 
    "0x8894e0a0c962cb723c1976a4421c95949be2d4e3", 
    "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c", 
    "0x10ed43c718714eb63d5aa57b78b54704e256024e", 
    "0xdac17f958d2ee523a2206206994597c13d831ec7", # 新增: ERC USDT 合约地址防干扰
]

def load_cloud_blacklist():
    cloud_file = "config/blacklist.txt"
    if os.path.exists(cloud_file):
        try:
            with open(cloud_file, "r", encoding="utf-8") as f:
                return [line.strip().lower() for line in f.readlines() if line.strip()]
        except: return []
    return []

st.set_page_config(page_title="USDT 智能追踪系统", layout="centered")

# --- 登录界面 ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; color: #00ffcc;'>🔐 系统登录</h1>", unsafe_allow_html=True)
        pwd = st.text_input("", type="password", placeholder="请输入 4 位授权码...", label_visibility="collapsed")
        if st.button("🚀 解锁系统", use_container_width=True):
            if pwd == ACCESS_PASSWORD:
                st.session_state['authenticated'] = True
                st.rerun()
            else: st.error("❌ 密码错误")
    st.stop()

st.markdown("<h1 style='text-align: center; color: #00ffcc;'>🕵️ USDT 智能关联穿透系统</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.title("🛡️ 状态面板")
    c_list = load_cloud_blacklist()
    st.success(f"📂 已载入黑名单: {len(c_list)} 条")
    st.divider()
    if st.button("🔴 退出系统"):
        st.session_state['authenticated'] = False
        st.rerun()

# --- 新增了 tab_erc 分页 ---
tab_trc, tab_bsc, tab_erc = st.tabs(["💎 TRC-20 批量穿透", "🔥 BSC 批量穿透", "⛓️ ERC-20 批量穿透"])

# --- TRC 分页 (完全没动) ---
with tab_trc:
    st.markdown("### ⚙️ TRC 配置")
    trc_days = st.number_input("分析时间范围 (限 1-30 天)：", min_value=1, max_value=30, value=7, key="td")
    trc_input = st.text_area("粘贴 TRC 目标地址 (一行一个):", height=180, key="ti")

    if st.button("🚀 执行 TRC 批量穿透", use_container_width=True):
        if trc_input:
            safe_days = min(30, trc_days)
            full_black_lower = set([a.lower() for a in (BASE_EXCLUDE + load_cloud_blacklist())])
            targets = [a.strip() for a in trc_input.split('\n') if a.strip()]
            start_ms = int((datetime.now() - timedelta(days=safe_days)).timestamp() * 1000)
            
            for target in targets:
                with st.status(f"🎯 TRC 查询: {target}", expanded=True) as status:
                    api_url = "https://apilist.tronscanapi.com/api/token_trc20/transfers"
                    params = {"limit": 100, "address": target, "start_timestamp": start_ms, "relatedAddress": target}
                    headers = {"TRON-PRO-API-KEY": TRON_API_KEY}
                    try:
                        r = requests.get(api_url, params=params, headers=headers).json()
                        transfers = r.get('token_transfers', [])
                        peers = set()
                        for tx in transfers:
                            f_addr, t_addr = tx.get('from_address'), tx.get('to_address')
                            peer = f_addr if t_addr == target else t_addr
                            tag = tx.get('fromAddressTag') if t_addr == target else tx.get('toAddressTag')
                            is_contract = tx.get('fromAddressIsContract') if t_addr == target else tx.get('toAddressIsContract')
                            if peer.lower() in full_black_lower or tag or is_contract or peer == target: continue
                            peers.add(peer)
                        if peers: st.code("\n".join(peers), language="text")
                        else: st.write("❌ 查无有效关联")
                        status.update(label=f"✅ 完成: {target}", state="complete")
                    except: st.error(f"❌ 失败: {target}")
                time.sleep(0.3)
            st.success("🏁 TRC 任务全部完成")

# --- BSC 分页 (完全没动) ---
with tab_bsc:
    st.markdown("### ⚙️ BSC 批量配置")
    bsc_limit = st.number_input("分析交易笔数 (限 1-100)：", min_value=1, max_value=100, value=50, step=1)
    min_amount = st.number_input("过滤掉小于此金额的记录 (U)：", min_value=0.0, value=1.0, step=0.1)
    bsc_input = st.text_area("粘贴 BSC 目标地址 (一行一个):", height=180, key="bi")

    if st.button("🚀 执行 BSC 批量穿透", use_container_width=True):
        if bsc_input:
            safe_limit = min(100, bsc_limit)
            full_black_lower = set([a.lower() for a in (BASE_EXCLUDE + load_cloud_blacklist())])
            targets = [a.strip().lower() for a in bsc_input.split('\n') if a.strip()]
            for target in targets:
                with st.status(f"🎯 BSC 查询: {target}", expanded=True) as status:
                    all_txs = []
                    cursor = ""
                    try:
                        while len(all_txs) < safe_limit:
                            fetch_now = min(100, safe_limit - len(all_txs))
                            params = {"address": target, "chain": "bsc", "limit": fetch_now}
                            if cursor: params["cursor"] = cursor
                            res = evm_api.token.get_wallet_token_transfers(api_key=MORALIS_API_KEY, params=params)
                            batch = res.get("result", [])
                            all_txs.extend(batch)
                            cursor = res.get("cursor")
                            if not cursor or not batch: break
                            time.sleep(0.2)
                        
                        associated_set = set()
                        for tx in all_txs:
                            # 🛡️ 容错保护：确保 value 和 decimals 存在
                            val_raw = tx.get("value")
                            dec_raw = tx.get("token_decimals")
                            
                            if val_raw is None: continue # 如果没金额，直接跳过
                            
                            # 转换逻辑：若精度不存在则默认为 18
                            try:
                                actual_val = int(val_raw) / (10 ** int(dec_raw if dec_raw is not None else 18))
                            except:
                                actual_val = 0
                                
                            if actual_val < min_amount: continue
                                
                            f, t = tx.get("from_address", "").lower(), tx.get("to_address", "").lower()
                            peer = f if t == target else t
                            if peer and peer != target and peer not in full_black_lower:
                                associated_set.add(peer)
                        
                        if associated_set:
                            st.code("\n".join(sorted(list(associated_set))), language="text")
                        else: st.write("❌ 查无有效关联")
                        status.update(label=f"✅ 完成: {target}", state="complete")
                    except Exception as e: st.error(f"❌ 错误 ({target}): {e}")
                time.sleep(0.3)
            st.success("🏁 BSC 任务全部完成")

# --- 新增的 ERC 分页 ---
with tab_erc:
    st.markdown("### ⚙️ ERC 批量配置")
    # Etherscan 接口支持一次性拉取，所以这里直接复用类似 BSC 的输入格式
    erc_limit = st.number_input("分析交易笔数 (限 1-500)：", min_value=1, max_value=500, value=50, step=1, key="erc_lim")
    erc_min_amount = st.number_input("过滤掉小于此金额的记录 (U)：", min_value=0.0, value=1.0, step=0.1, key="erc_min")
    erc_input = st.text_area("粘贴 ERC 目标地址 (一行一个):", height=180, key="ei")

    if st.button("🚀 执行 ERC 批量穿透", use_container_width=True):
        if erc_input:
            safe_limit = min(500, erc_limit)
            full_black_lower = set([a.lower() for a in (BASE_EXCLUDE + load_cloud_blacklist())])
            targets = [a.strip().lower() for a in erc_input.split('\n') if a.strip()]
            
            for target in targets:
                with st.status(f"🎯 ERC 查询: {target}", expanded=True) as status:
                    try:
                        # 呼叫 Etherscan Token Transfers 接口
                        url = f"https://api.etherscan.io/api?module=account&action=tokentx&address={target}&page=1&offset={safe_limit}&sort=desc&apikey={ETHERSCAN_API_KEY}"
                        r = requests.get(url).json()
                        
                        if r.get("status") == "1":
                            txs = r.get("result", [])
                            associated_set = set()
                            
                            for tx in txs:
                                val_raw = tx.get("value", "0")
                                dec_raw = tx.get("tokenDecimal", "18")
                                
                                try:
                                    actual_val = int(val_raw) / (10 ** int(dec_raw if dec_raw else 18))
                                except:
                                    actual_val = 0
                                    
                                if actual_val < erc_min_amount: continue
                                
                                f, t = tx.get("from", "").lower(), tx.get("to", "").lower()
                                peer = f if t == target else t
                                
                                if peer and peer != target and peer not in full_black_lower:
                                    associated_set.add(peer)
                                    
                            if associated_set:
                                st.code("\n".join(sorted(list(associated_set))), language="text")
                            else: 
                                st.write("❌ 查无有效关联")
                            status.update(label=f"✅ 完成: {target}", state="complete")
                            
                        else:
                            # 过滤掉查无数据的正常情况
                            if r.get("message") == "No transactions found":
                                st.write("❌ 查无代币转移记录")
                                status.update(label=f"✅ 完成: {target}", state="complete")
                            else:
                                st.error(f"❌ API 报错: {r.get('message')}")
                                status.update(label=f"❌ 失败: {target}", state="error")
                                
                    except Exception as e: 
                        st.error(f"❌ 错误 ({target}): {e}")
                        status.update(label=f"❌ 失败: {target}", state="error")
                # 防封锁延迟
                time.sleep(0.3)
            st.success("🏁 ERC 任务全部完成")
