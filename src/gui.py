import json
import random

from networkx.algorithms.community import (
    louvain_communities,
    greedy_modularity_communities,
    naive_greedy_modularity_communities,
    label_propagation_communities,
    asyn_lpa_communities,
    fast_label_propagation_communities
)
from streamlit_extras.mandatory_date_range import date_range_picker
from networkx.algorithms.cycles import (simple_cycles,
                                        cycle_basis,
                                        minimum_cycle_basis,
                                        chordless_cycles)

from pyvis.network import Network
from src.scanurl import APILink
from datetime import datetime, time
from io import StringIO, BytesIO

import streamlit.components.v1 as components
import src.utils as ut
import streamlit as st
import networkx as nx
import pandas as pd

ss = st.session_state


def load_sidebar_bsc():
    st.sidebar.header("Sybil-Tracker", divider='grey')
    with open("text/sidebar_bsc.txt") as file:
        sidebar_txt = file.read()
    with st.sidebar:
        st.write(sidebar_txt, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_css(file: str):
    with open(f"css/{file}.css") as f:
        sidebar_css = f.read()
    st.markdown(sidebar_css, unsafe_allow_html=True)


def load_ui():
    with st.form("user_input"):

        wallet_input = st.text_input(
            label="Enter any Ethereum Address",
            value=ss['wallet']
        )

        chain_input = st.selectbox(
            label="Pick a Chain",
            options=("Ethereum", "Arbitrum", "Polygon", "Optimism", "Base", "Scroll")
        )

        depth_input = st.number_input(
            label="Pick a depth",
            min_value=1,
            max_value=5,
            value=1
        )

        threshold_input = st.number_input(
            label="Select Amount USD to filter for",
            min_value=0,
            max_value=2147483647,
            value=0,
            step=500
        )

        start_date, end_date = date_range_picker(
            title="Pick a date range",
            max_date=datetime.today()
        )

        start_datetime = datetime(start_date.year, start_date.month, start_date.day)
        end_datetime = datetime(end_date.year, end_date.month, end_date.day)

        with st.expander('Advanced time settings'):
            startTime = st.time_input('Start time', value=time(0, 0, 0), key='startTime')
            endTime = st.time_input('End time', value=time(0, 0, 0), key='endTime')

        with st.expander('Searching algorithms'):
            ss['algo'] = st.radio('Choose one:',
                                  ['louvain communities', 'naive greedy modularity communities',
                                   'greedy modularity communities', 'simple cycles', 'cycle basis', 'chordless cycles',
                                   'minimum cycle basis', 'label propagation communities', 'asyn lpa communities',
                                   'fast label propagation communities']
                                  )

        submit_wallet = st.form_submit_button(label="Submit Wallet", on_click=ut.clear_ss(), use_container_width=True)
        st.info('The bigger the depth and time window, the longer the calculation will take. '
                'Increasing the USD threshold will improve this!', icon='ℹ️')

        if submit_wallet:
            ss["chain"] = chain_input
            ss["threshold_usd"] = threshold_input
            ss["wallet"] = wallet_input
            ss["addresses"] = set()
            ss["depth"] = depth_input
            ss["start_time"] = int(start_datetime.timestamp()) + int(ut.convert_time(startTime))
            ss["end_time"] = int(end_datetime.timestamp()) + int(ut.convert_time(endTime))
            ss["time_window"] = ss["end_time"] - ss["start_time"]
            ss["submit"] = True
            if ss["end_time"] <= ss["start_time"]:
                ss["end_time"] = ss["start_time"] + 86400


@st.cache_resource(show_spinner=False)
def draw_network(data: set | list, addresses: set, height: int = 615, select_menu: bool = False, legend: bool = True):
    # Function to generate the network HTML content
    def generate_network_html():
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
            if height != 615:
                net = Network(notebook=True, neighborhood_highlight=True, cdn_resources='remote', directed=True,
                              select_menu=select_menu, layout=True, height=300)
            else:
                net = Network(notebook=True, neighborhood_highlight=True, cdn_resources='remote', directed=True,
                              select_menu=select_menu, layout=True)

            net.bgcolor = "#262730"  # Background color
            net.font_color = "white"  # Font color

            # Add nodes to the network with sizes and colors
            node_degrees = dict(G.degree())
            physicsBool = True

            for address, degree in node_degrees.items():
                if address.lower() in addresses:
                    size = get_node_size(address)
                    # Set colors based on conditions
                    if address == ss['wallet'].lower():
                        color = "red"
                    elif 10 <= int(node_degrees[address]):
                        color = "yellow"
                    else:
                        color = "lightblue"

                    if 50 < int(node_degrees[address]):
                        physicsBool = False

                    net.add_node(address, color=color, size=size)

            net.options = {
                "interaction": {
                    "dragNodes": True,
                    "dragView": True,
                    "hideEdgesOnDrag": False,
                    "hideEdgesOnZoom": False,
                    "hideNodesOnDrag": False,
                    "hover": True,
                    "hoverConnectedEdges": True,
                    "multiselect": False,
                    "navigationButtons": False,
                    "selectable": True,
                    "selectConnectedEdges": True,
                    "tooltipDelay": 300,
                    "zoomSpeed": .5,
                    "zoomView": True,
                },
                "physics": {
                    "enabled": physicsBool,
                }
            }
            # Add edges (transactions) to the network
            for tx in data:
                from_address = tx["From"]
                to_address = tx["To"]
                if from_address in net.node_ids and to_address in net.node_ids:
                    net.add_edge(from_address, to_address)

            # Save the network to a BytesIO object
            html_bytes = BytesIO(net.generate_html().encode('utf-8'))
            html_bytes.seek(0)

            return html_bytes.read().decode('utf-8'), G
        else:
            return None, None

    # Use the identifier to create a unique key for session state
    session_key = f'network_html_{random.randint(1, 1000000)}'

    if session_key not in st.session_state:
        st.session_state[session_key], G = generate_network_html()
    else:
        G = None

    html_content = st.session_state[session_key]

    # Output the HTML content in Streamlit
    if html_content:
        if legend:
            rCol, lCol = st.columns([10, 1])

            lCol.write(":red[Origin Wallet]")
            lCol.write(":orange[High Activity]")
            lCol.write(":blue[Normal Activity]")

            with rCol:
                components.html(html_content, height=height)

        else:
            components.html(html_content, height=height)

    return G


def load_df_analysis(G, data):
    if ss['algo'] == 'louvain communities':
        communities = list(louvain_communities(G))
    elif ss['algo'] == 'naive greedy modularity communities':
        communities = list(naive_greedy_modularity_communities(G))
    elif ss['algo'] == 'greedy modularity communities':
        communities = list(greedy_modularity_communities(G))
    elif ss['algo'] == 'simple cycles':
        communities = list(simple_cycles(G))
    elif ss['algo'] == 'cycle basis':
        communities = list(cycle_basis(G))
    elif ss['algo'] == 'chordless cycles':
        communities = list(chordless_cycles(G))
    elif ss['algo'] == 'minimum cycle basis':
        communities = list(minimum_cycle_basis(G))
    elif ss['algo'] == 'label propagation communities':
        communities = list(label_propagation_communities(G))
    elif ss['algo'] == 'asyn lpa communities':
        communities = list(asyn_lpa_communities(G))
    elif ss['algo'] == 'fast label propagation communities':
        communities = list(fast_label_propagation_communities(G))
    else:
        communities = []

    communities = [list(item) for item in communities]

    for i, item in enumerate(communities):
        with st.container(border=True):
            st.header(f'Cluster {i + 1}')
            _lCol, _, _rCol = st.columns([1, .05, 1])

            ss['addresses'] = set(item)
            dfCom = pd.DataFrame(item, columns=['wallet'])

            with _lCol:
                with st.expander('Wallets'):
                    load_search_options(item)
                    st.download_button('Download csv', dfCom.to_csv(index=False),
                                       file_name=f'{ss["wallet"]}_cluster{i + 1}.csv', use_container_width=True,
                                       on_click=ut.save_state)

            with _rCol:
                draw_network(data, addresses=ss['addresses'], select_menu=False, legend=False)

            with st.expander('**Transaction Data**'):
                load_fake_df(data)


def load_fake_df(data: list[dict]):
    if data:
        hcol1, hcol2, hcol3, hcol4, hcol5, hcol6, hcol7, hcol8 = st.columns([1, 1, 1, 1, 1, 1, 1, 1])

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
            if data[i]['From'].lower() in ss['addresses'] and data[i]['To'].lower() in ss['addresses']:
                prefixTo, suffixTo = '', ''  # ut.get_color(data[i]['To'])
                prefixFrom, suffixFrom = '', ''  # ut.get_color(data[i]['From'])

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


def load_search_options(data: list):
    if data:
        for i, wallet in enumerate(data):
            with st.container(border=True):
                lCol, rCol = st.columns([3, 1])
                lCol.write(wallet)
                rCol.button(
                    'Search', on_click=ut.set_new_wallet, args=(wallet,),
                    key=f'{wallet}_{random.randint(1, 2000000000)}', use_container_width=True
                )
