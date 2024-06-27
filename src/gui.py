import os
import json
import tempfile

from streamlit_extras.mandatory_date_range import date_range_picker
from streamlit_pandas_profiling import st_profile_report
from streamlit.components.v1 import components
from pyvis.network import Network
from src.scanurl import APILink
from datetime import datetime

import src.utils as utils
import streamlit as st
import networkx as nx
import pandas as pd

import datetime

ss = st.session_state


def load_button(name):
    if name == "ref_buttons":
        with open("style/ref_buttons.css", "r") as f:
            ref_buttons_css = f.read()
        st.markdown(ref_buttons_css, unsafe_allow_html=True)


def load_sidebar_bsc():
    with open("text/sidebar_bsc.txt") as file:
        sidebar_txt = file.read()
    with st.sidebar:
        st.write(sidebar_txt, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_main_bsc():
    st.header("Blockchain Sniffer")


@st.cache_data(show_spinner=False)
def load_header():
    with open("style/header.css") as f:
        header_css = f.read()
    st.markdown(header_css, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_footer():
    with open("style/footer.css") as f:
        footer_css = f.read()
    st.markdown(footer_css, unsafe_allow_html=True)


def load_ui_bsc():
    with st.form("user_input"):
        wallet_input = st.text_input(
            label="Enter any Ethereum Address",
            value="0x9E29A34dFd3Cb99798E8D88515FEe01f2e4cD5a8"
        )
        depth_input = st.number_input(
            label="Pick a depth",
            min_value=0,
            max_value=2,
            value=0
        )
        chain_input = st.selectbox(
            label="Pick a Chain",
            options=("Ethereum", "Arbitrum", "Polygon", "Optimism", "Base")
        )

        start_date, end_date = date_range_picker(
            title="Pick a date range",
            max_date=datetime.datetime.today()
        )
        start_datetime = datetime.datetime(start_date.year, start_date.month, start_date.day)
        end_datetime = datetime.datetime(end_date.year, end_date.month, end_date.day)
        threshold_input = st.slider(
            label="Select Amount USD to filter for",
            min_value=0,
            max_value=100000,
            step=5000
        )
        submit_wallet = st.form_submit_button(label="Submit Wallet", on_click=utils.clear_ss())
        if submit_wallet:
            ss["chain"] = chain_input
            ss["threshold_usd"] = threshold_input
            ss["wallet"] = wallet_input
            ss["addresses"] = [wallet_input]
            ss["depth"] = depth_input
            ss["start_time"] = int(start_datetime.timestamp())
            ss["end_time"] = int(end_datetime.timestamp())
            ss["time_window"] = ss["end_time"] - ss["start_time"]
            if ss["end_time"] <= ss["start_time"]:
                ss["end_time"] = ss["start_time"] + 86400
            ss["submit"] = True


def draw_network(data: set | list):
    data_str = json.dumps(data)
    df = pd.read_json(data_str)
    G = nx.from_pandas_edgelist(
        df, source="From", target="To", edge_attr="Value_USD"
    )

    if data:
        # Erstellen Sie die Knoten und Kanten aus den Transaktionsdaten
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
        net = Network(notebook=True)
        # net.bgcolor = "#262730" # BG Color

        net.options = {
            "interaction": {
                "dragNodes": True,
                "dragView": True,
                "hideEdgesOnDrag": False,
                "hideEdgesOnZoom": False,
                "hideNodesOnDrag": False,
                "hover": False,
                "hoverConnectedEdges": False,
                "multiselect": False,
                "navigationButtons": False,
                "selectable": True,
                "selectConnectedEdges": True,
                "tooltipDelay": 300,
                "zoomSpeed": 1,
                "zoomView": True
            }
        }

        # Add nodes to the network with sizes and colors
        node_degrees = dict(G.degree())
        for address in volume_per_address:
            size = get_node_size(address)
            # Set colors based on conditions
            if 10 <= int(node_degrees[address]):
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
            net.add_edge(from_address, to_address)

        if not os.path.exists("temp"):
            os.makedirs("temp")

        file_descriptor, temp_name = tempfile.mkstemp(suffix=".html", dir="temp")
        os.close(file_descriptor)
        net.show(temp_name)

        # HTML-Datei öffnen und den Inhalt lesen
        with open(temp_name, "r", encoding="utf-8") as file:
            html_content = file.read()

        # Löschen der temporären Datei
        os.remove(temp_name)

        # Geben Sie den HTML-Inhalt in Streamlit aus
        st.write("Red: Origin Wallet; "
                 "Yellow: Exchanges; "
                 "Blue: Unknown")
        st.components.v1.html(html_content, height=615)

        df = pd.DataFrame(data)

        # Add a new column for the hyperlinks
        base_tx_url = APILink(address=None, tx_type=None).get_tx_url()
        base_wallet_url = APILink(address=None, tx_type=None).get_wallet_url()

        df["From"] = df["From"].apply(
            lambda x: base_wallet_url + x)
        df["To"] = df["To"].apply(
            lambda x: base_wallet_url + x)
        df["Hash"] = df["Hash"].apply(
            lambda x: base_tx_url + x)

        # Display the DataFrame in Streamlit with links
        st.data_editor(
            df,
            column_config={
                "From": st.column_config.LinkColumn(),
                "To": st.column_config.LinkColumn(),
                "Hash": st.column_config.LinkColumn()
            },
            hide_index=True,
        )


@st.cache_data(show_spinner=False, experimental_allow_widgets=True)
def load_record(data_json: list[dict]):
    data_csv = utils.json_to_csv(data_json)
    data_report = data_csv.profile_report()

    st_profile_report(data_report)
