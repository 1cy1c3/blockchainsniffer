import streamlit as st

import src.scan as scan
import src.utils as utils
import src.gui as gui

ss = st.session_state

st.set_page_config(page_icon="🐽", layout="wide")
lCol, rCol = st.columns([1, 1])
lCol.header('Blockchain Sniffer', divider='grey')


utils.init_state_bsc()

with st.sidebar:
    gui.load_ui()
    gui.load_sidebar_bsc()

gui.load_css('footer')
gui.load_css('header')
gui.load_css('sidebar')

if ss.get("submit"):
    wallet = scan.check_wallet(ss["wallet"])

    if wallet:
        start_time = ss["start_time"]
        end_time = ss["end_time"]
        ss["start_block"] = scan.get_block_by_timestamp(start_time, ss['chain'])
        ss["end_block"] = scan.get_block_by_timestamp(end_time, ss['chain'])

        with lCol.status('Searching the Blockchain'):
            func_data = scan.main(
                ss["wallet"], ss['depth'], ss['threshold_usd'], ss["start_block"], ss["end_block"], ss['chain']
            )

        if func_data:
            ss['addresses'] = set([item['From'] for item in func_data])
            ss['addresses'].update(set([item['To'] for item in func_data]))

            st.divider()
            network_data = gui.draw_network(func_data)
            st.divider()
            gui.load_df_analysis(network_data, func_data)
            st.divider()
            gui.load_fake_df(func_data)

        else:
            lCol.warning("**No transactions for this parameters**")
        ss["submit"] = False

    else:
        lCol.warning("**Wallet not found!**")
