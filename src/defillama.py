import requests
import time

import streamlit as st


ss = st.session_state


@st.cache_data(show_spinner=False)
def get_historical_price(timestamp: str, contract_address: str) -> float:
    chain = ss["chain"].lower()
    time.sleep(0.12)
    url = f"https://coins.llama.fi/prices/historical/{timestamp}/{chain}:{contract_address}"
    response = requests.get(url)
    data = response.json()
    try:
        price = data["coins"][f"{chain}:{contract_address}"]["price"]
        return price
    except KeyError:
        return False
