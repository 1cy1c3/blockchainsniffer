from typing import Any

import streamlit as st
from datetime import datetime
import requests
import json

from functions.scanurl import APILink
import functions.defillama as defillama

ss = st.session_state


@st.cache_data(show_spinner=False)
def is_contract(address: str) -> bool:
    # Build URL
    url = APILink(address=address, tx_type=None).check_for_contract()

    # Send Request
    response = requests.get(url)
    if response.status_code != 200:
        print("Error for request:", response.status_code)
        return False

    data = json.loads(response.text)

    # Überprüfen Sie, ob die Anfrage erfolgreich war
    if data['result'] != '0x':
        return True
    else:
        return False


@st.cache_data(show_spinner=False)
def check_wallet(address: str) -> bool:
    url = APILink(address=address, tx_type=None).check_wallet()

    response = requests.get(url)
    data = response.json()

    if data['message'] == 'OK':
        return True  # Wallet exists
    else:
        return False


@st.cache_data(show_spinner=False)
def get_block_by_timestamp(timestamp: int) -> str:
    url = APILink(address=None, tx_type=None).get_block_number(timestamp)
    response = requests.get(url)
    data = response.json()
    if data['status'] != '1':
        print('Anfrage fehlgeschlagen')
        return "0"
    return data['result']


def create_dataset(tx: dict, wallet: str) -> tuple[dict[Any], str]:
    dataset = {}
    ss["records"] += 1
    sender = tx["from"]
    to = tx["to"]
    symbol = tx["tokenSymbol"]
    decimals = tx["tokenDecimal"]
    tx_hash = tx["hash"]
    name = tx["tokenName"]
    timestamp = tx["timeStamp"]
    value_raw = tx["value"]

    if (not is_contract(sender) and not is_contract(to)
            and to != st.secrets["null"] and sender != st.secrets["null"]
            and tx_hash not in ss["tx_hashes"]):

        token_price = defillama.get_historical_price(tx["timeStamp"], tx["contractAddress"])
        token_amount = int(value_raw) * 10 ** - int(decimals)

        if token_price and token_amount:
            value_usd = round(token_amount * token_price, 0)
            threshold_usd = ss["threshold_usd"]

            if value_usd >= threshold_usd:
                time = timestamp_to_date(int(timestamp))
                dataset["Hash"] = tx_hash
                dataset["Time"] = time
                dataset["From"] = sender
                dataset["To"] = to
                dataset["Token_Amount"] = token_amount
                dataset["Value_USD"] = value_usd
                dataset["Token"] = name
                dataset["Symbol"] = symbol

                ss["tx_hashes"].append(tx_hash)
                ss["counter"] += 1
                print(f"counter: {ss['counter']} _________________________")

                if sender != wallet.lower() and sender not in ss["addresses"]:
                    wallet = sender

                elif to != wallet.lower() and to not in ss["addresses"]:
                    wallet = to

                return dataset, wallet


@st.cache_data(show_spinner=False)
def timestamp_to_date(timestamp: int) -> str:
    # Convert timestamp to date
    date = datetime.fromtimestamp(timestamp)
    return date.strftime('%Y/%m/%d %H:%M:%S')


def erc20_transactions(wallet: str) -> tuple[list[dict], list] | None:
    max_tx = 10 * (ss["time_window"] / 86400)

    # Buidl URL
    url = APILink(address=wallet, tx_type="erc20").get_api_link()

    # Send Request
    response = requests.get(url)
    response.raise_for_status()  # Raises a HTTPError if the response status is 4XX or 5XX
    data = json.loads(response.text)

    if data['status'] != '1':
        print('Anfrage fehlgeschlagen')
        return

    transactions = data['result']

    if len(transactions) > max_tx:
        print("Too much txs - EXC or phishing")
        return

    dataset = []
    add_list = []

    for tx in transactions:
        func_data = create_dataset(tx, wallet)
        if func_data is not None:
            dataset.append(func_data[0])
            if func_data[1] not in add_list:
                add_list.append(func_data[1])

    return dataset, add_list
