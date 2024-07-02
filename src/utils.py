import pandas as pd
import streamlit as st

ss = st.session_state


def init_state_bsc():
    if "width" not in ss:
        ss["width"] = 0
    if "height" not in ss:
        ss["height"] = 0
    if "dataset" not in ss:
        ss["dataset"] = []
    if "addresses" not in ss:
        ss["addresses"] = set()
    if "start_time" not in ss:
        ss["start_time"] = None
    if "end_time" not in ss:
        ss["end_time"] = None
    if "start_block" not in ss:
        ss["start_block"] = None
    if "end_block" not in ss:
        ss["end_block"] = None
    if "counter" not in ss:
        ss["counter"] = 0
    if "depth" not in ss:
        ss["depth"] = 1
    if "submit" not in ss:
        ss["submit"] = False
    if "records" not in ss:
        ss["records"] = 0
    if "tx_hashes" not in ss:
        ss["tx_hashes"] = []
    if "black_list" not in ss:
        ss["black_list"] = set()
    if "time_window" not in ss:
        ss["time_window"] = None
    if "threshold_usd" not in ss:
        ss["threshold_usd"] = None
    if "chain" not in ss:
        ss["chain"] = None
    if "wallet" not in ss:
        ss["wallet"] = None
    if "wallet_info" not in ss:
        ss["wallet_info"] = []


def clear_ss():
    ss["records"] = 0
    ss['counter'] = 0
    ss["wallet_info"].clear()
    ss["addresses"].clear()
    ss["dataset"].clear()
    ss["tx_hashes"].clear()


def json_to_csv(data_json: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(data_json)


def get_color(address: str) -> tuple[str, str]:
    if address.lower() == ss['wallet'].lower():
        prefix = ':red['
        suffix = ']'
    elif address in ss['addresses']:
        prefix = ':orange['
        suffix = ']'
    else:
        prefix = ':blue['
        suffix = ']'
    return prefix, suffix

