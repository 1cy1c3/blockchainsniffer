import os
import json
import tempfile
import datetime

from streamlit_extras.mandatory_date_range import date_range_picker
from streamlit_pandas_profiling import st_profile_report
from pyvis.network import Network
from src.scanurl import APILink
from io import StringIO

import streamlit.components.v1 as components
import src.utils as ut
import streamlit as st
import networkx as nx
import pandas as pd

ss = st.session_state


def load_sidebar_bsc():
    st.sidebar.header("Blockchain Sniffer", divider='grey')
    with open("text/sidebar_bsc.txt") as file:
        sidebar_txt = file.read()
    with st.sidebar:
        st.write(sidebar_txt, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_header():
    with open("css/header.css") as f:
        header_css = f.read()
    st.markdown(header_css, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_footer():
    with open("css/footer.css") as f:
        footer_css = f.read()
    st.markdown(footer_css, unsafe_allow_html=True)


def load_ui_bsc():
    with st.form("user_input"):
        lCol, rCol = st.columns([1, 1])
        wallet_input = lCol.text_input(
            label="Enter any Ethereum Address",
            value="0x9E29A34dFd3Cb99798E8D88515FEe01f2e4cD5a8"
        )

        chain_input = lCol.selectbox(
            label="Pick a Chain",
            options=("Ethereum", "Arbitrum", "Polygon", "Optimism", "Base")
        )

        with rCol:
            start_date, end_date = date_range_picker(
                title="Pick a date range",
                max_date=datetime.datetime.today()
            )

        depth_input = rCol.number_input(
            label="Pick a depth",
            min_value=1,
            max_value=5,
            value=1
        )

        start_datetime = datetime.datetime(start_date.year, start_date.month, start_date.day)
        end_datetime = datetime.datetime(end_date.year, end_date.month, end_date.day)

        threshold_input = rCol.slider(
            label="Select Amount USD to filter for",
            min_value=0,
            max_value=100000,
            step=1000
        )

        submit_wallet = lCol.form_submit_button(label="Submit Wallet", on_click=ut.clear_ss())
        st.info('The bigger the depth and time window, the longer the calculation will take. '
                'Increasing the USD threshold will improve this!', icon='ℹ️')

        if submit_wallet:
            ss["chain"] = chain_input
            ss["threshold_usd"] = threshold_input
            ss["wallet"] = wallet_input
            ss["addresses"] = set()
            ss["depth"] = depth_input
            ss["start_time"] = int(start_datetime.timestamp())
            ss["end_time"] = int(end_datetime.timestamp())
            ss["time_window"] = ss["end_time"] - ss["start_time"]
            if ss["end_time"] <= ss["start_time"]:
                ss["end_time"] = ss["start_time"] + 86400
            ss["submit"] = True


def draw_network(data: set | list, edge_threshold: int = 0):
    df = pd.read_json(StringIO(json.dumps(data)))
    G = nx.from_pandas_edgelist(df, source="From", target="To", edge_attr="Value_USD")

    if data:
        # Create the volume_per_address dictionary
        volume_per_address = {}
        for tx in data:
            from_address = tx["From"]
            to_address = tx["To"]
            value = tx["Value_USD"]

            volume_per_address[from_address] = volume_per_address.get(from_address, 0) + value
            volume_per_address[to_address] = volume_per_address.get(to_address, 0) + value

        # Normalize node sizes for better visualization
        max_volume = max(volume_per_address.values())
        min_size = 10  # Minimum node size
        max_size = 50  # Maximum node size

        # Create a function to scale node sizes
        def get_node_size(wallet):
            return min_size + (volume_per_address[wallet] / max_volume) * (max_size - min_size)

        # Create the network
        net = Network(notebook=True, neighborhood_highlight=True, cdn_resources='remote', directed=True)
        net.bgcolor = "#262730"  # Background color
        net.font_color = "white"  # Font color

        net.options = {
            "interaction": {
                "dragNodes": True,
                "dragView": True,
                "hideEdgesOnDrag": False,
                "hideEdgesOnZoom": False,
                "hideNodesOnDrag": False,
                "hover": True,
                "hoverConnectedEdges": True,
                "multiselect": True,
                "navigationButtons": False,
                "selectable": True,
                "selectConnectedEdges": True,
                "tooltipDelay": 300,
                "zoomSpeed": .5,
                "zoomView": True
            }
        }

        # Add nodes to the network with sizes and colors
        node_degrees = dict(G.degree())
        for address, degree in node_degrees.items():
            if degree > edge_threshold:
                size = get_node_size(address)
                # Set colors based on conditions
                if 10 <= int(node_degrees[address]):
                    ss['addresses'].add(address)
                    color = "yellow"
                elif address == ss["wallet"].lower():
                    color = "red"
                else:
                    color = "lightblue"

                net.add_node(address, color=color, size=size)

        # Add edges (transactions) to the network
        for tx in data:
            from_address = tx["From"]
            to_address = tx["To"]
            if from_address in net.node_ids and to_address in net.node_ids:
                net.add_edge(from_address, to_address)

        if not os.path.exists("temp"):
            os.makedirs("temp")

        file_descriptor, temp_name = tempfile.mkstemp(suffix=".html", dir="temp")
        os.close(file_descriptor)
        net.show(temp_name)

        # HTML file open and read the content
        with open(temp_name, "r", encoding="utf-8") as file:
            html_content = file.read()

        # Delete the temporary file
        os.remove(temp_name)

        # Output the HTML content in Streamlit
        rCol, lCol = st.columns([10, 1])

        lCol.write(":red[Origin Wallet]")
        lCol.write(":orange[High Activity]")
        lCol.write(":blue[Normal Activity]")

        with rCol:
            components.html(html_content, height=615)


@st.cache_data(show_spinner=False)
def load_record(data_json: list[dict]):
    data_csv = ut.json_to_csv(data_json)
    data_report = data_csv.profile_report()

    st_profile_report(data_report)


def load_fake_df(data: list[dict]):
    if data:
        hcol1, hcol2, hcol3, hcol4, hcol5, hcol6, hcol7, hcol8 = st.columns([1, 1, 1, 1, 1, 1, 1, 1, ])

        st.divider()

        hcol1.write('**Time [UTC]**')
        hcol2.write('**Hash**')
        hcol3.write('**From**')
        hcol4.write('**To**')
        hcol5.write('**TokenAmount**')
        hcol6.write('**ValueUSD**')
        hcol7.write('**Token**')
        hcol8.write('**Ticker**')

        for i in range(len(data)):
            prefixTo, suffixTo = ut.get_color(data[i]['To'])
            prefixFrom, suffixFrom = ut.get_color(data[i]['From'])

            with st.container(border=True):
                base_tx_url = APILink(address=None, tx_type=None).get_tx_url()
                base_wallet_url = APILink(address=None, tx_type=None).get_wallet_url()

                col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1, 1, 1, 1, 1, 1, 1, 1, ])

                col1.write(data[i]['Time'])

                col2.link_button(
                    f"{data[i]['Hash'][:6]}...{data[i]['Hash'][-5:]}",
                    url=f"{base_tx_url}{data[i]['Hash']}",
                    use_container_width=True
                )
                col3.link_button(
                    f"{prefixFrom}{data[i]['From'][:6]}...{data[i]['From'][-5:]}{suffixFrom}",
                    url=f"{base_wallet_url}{data[i]['From']}",
                    use_container_width=True
                )
                col4.link_button(
                    f"{prefixTo}{data[i]['To'][:6]}...{data[i]['To'][-5:]}{suffixTo}",
                    url=f"{base_wallet_url}{data[i]['To']}",
                    use_container_width=True
                )

                col5.write(str(int(data[i]['Token_Amount'])))
                col6.write(str(int(data[i]['Value_USD'])))
                col7.write(data[i]['Token'])
                col8.write(data[i]['Symbol'])
