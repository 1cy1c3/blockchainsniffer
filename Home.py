import streamlit as st

import src.scan as scan
import src.utils as utils
import src.gui as gui

ss = st.session_state

st.set_page_config(page_icon="🐽", layout="wide")
st.header('Blockchain Sniffer', divider='grey')

utils.init_state_bsc()

with st.sidebar:
    gui.load_sidebar_bsc()

gui.load_footer()
gui.load_header()
gui.load_ui_bsc()


if ss.get("submit"):
    wallet = scan.check_wallet(ss["wallet"])

    if wallet:
        start_time = ss["start_time"]
        end_time = ss["end_time"]
        ss["start_block"] = scan.get_block_by_timestamp(start_time)
        ss["end_block"] = scan.get_block_by_timestamp(end_time)

        with st.status('Searching the Blockchain'):
            func_data = scan.main(ss["wallet"], ss['depth'], ss['threshold_usd'], ss["start_block"], ss["end_block"], ss['chain'])

        if func_data:
            st.divider()
            gui.draw_network(func_data)
            st.divider()
            gui.load_fake_df(func_data)

        else:
            st.write("No transactions for this parameters")
        ss["submit"] = False

    else:
        st.write("Wallet not found! Or has no known transactions for this time window")
