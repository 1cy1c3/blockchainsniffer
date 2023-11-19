import streamlit as st

import functions.scan as scan
import functions.utils as utils
import functions.gui as gui


ss = st.session_state

st.set_page_config(page_title="Blockchain Sniffer 🐽", page_icon="🐽", layout="wide")


# Rest of the page
st.sidebar.header("Blockchain Sniffer")

utils.init_state_bsc()
with st.sidebar:
    gui.load_sidebar_bsc()
    gui.load_button("ref_buttons")

gui.load_footer()
gui.load_header()
gui.load_main_bsc()
gui.load_ui_bsc()

if ss.get("submit"):
    wallet = scan.check_wallet(ss["wallet"])

    if wallet:
        dataset = []
        address_list = set()
        count = st.empty()
        start_time = ss["start_time"]
        end_time = ss["end_time"]
        ss["start_block"] = scan.get_block_by_timestamp(start_time)
        ss["end_block"] = scan.get_block_by_timestamp(end_time)
        count_tx_pre = count.text(f"Starting to sniff the Blockchain")

        for i in range(ss["depth"] + 1):
            addresses = ss["addresses"]
            for address in addresses:
                address_list = []
                try:
                    with st.spinner(f"Sniffing the Blockchain - {ss['records']} Transactions sniffed"):
                        func_data = scan.erc20_transactions(address)
                        if i == 0:
                            ss["wallet_info"] = func_data[0]
                        if func_data is not None:
                            for item in func_data[0]:
                                if item:
                                    ss["dataset"].append(item)

                            for item in func_data[1]:
                                if item:
                                    if item not in address_list:
                                        address_list.append(item)
                            count_tx_post = count.text(f"{ss['counter']} Records added")

                except TypeError as e:
                    print(e)

            for item in address_list:
                if item not in ss["addresses"]:
                    ss["addresses"].append(item)

        network_data = ss["dataset"]

        if network_data:
            knot_dia = gui.draw_network(network_data)
            #wallet_record = gui.load_record(ss["wallet_info"])

        else:
            st.write("No transactions for this parameters")
        ss["submit"] = False

    else:
        st.write("Wallet not found! Or has no known transactions for this time window")
