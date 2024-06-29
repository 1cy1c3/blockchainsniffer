from typing import Any, Set, List, Dict, Optional

import streamlit as st
from datetime import datetime
import requests
import json
import asyncio
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

from src.scanurl import APILink
import src.defillama as defillama

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
                timest = timestamp_to_date(int(timestamp))
                dataset["Hash"] = tx_hash
                dataset["Time"] = timest
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


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10))
def _erc20_transactions(wallet: str, depth: int, visited: set = None) -> list[dict] | None:
    if visited is None:
        visited = set()

    if depth > ss["depth"] + 1 or wallet in visited:
        return None

    visited.add(wallet)
    dataset = []

    max_tx = 10 * (ss["time_window"] / 86400)

    # Buidl URL
    url = APILink(address=wallet, tx_type="erc20").get_api_link()

    # Send Request
    response = requests.get(url)
    response.raise_for_status()  # Raises a HTTPError if the response status is 4XX or 5XX
    data = json.loads(response.text)

    if data['status'] != '1':
        print('Anfrage fehlgeschlagen')
        return None

    transactions = data['result']

    if len(transactions) > max_tx:
        print("Too much txs - EXC or phishing")
        return None

    for tx in transactions:
        func_data = create_dataset(tx, wallet)
        if func_data is not None:
            dataset.append(func_data[0])
            from_address = func_data[0]['From']
            to_address = func_data[0]['To']

            # Recursive call for the 'From' and 'to' address
            child_dataset_from = erc20_transactions(from_address, depth + 1, visited)
            child_dataset_to = erc20_transactions(to_address, depth + 1, visited)
            if child_dataset_from:
                dataset.extend(child_dataset_from)
            if child_dataset_to:
                dataset.extend(child_dataset_to)

    return dataset


async def fetch_data(url: str, session: aiohttp.ClientSession) -> Optional[Dict]:
    async with session.get(url) as response:
        response.raise_for_status()
        data = await response.json()
        if data['status'] != '1':
            print('Anfrage fehlgeschlagen')
            return None
        return data


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10))
async def fetch_data(url: str, session: aiohttp.ClientSession) -> Optional[Dict]:
    async with session.get(url) as response:
        response.raise_for_status()
        data = await response.json()
        if data['status'] != '1':
            print('Anfrage fehlgeschlagen')
            return None
        return data


async def erc20_transactions(wallet: str, depth: int, visited: Set[str] = None, sem: asyncio.Semaphore = None,
                             session: aiohttp.ClientSession = None) -> List[Dict]:
    if visited is None:
        visited = set()

    if depth > ss["depth"] + 1 or wallet in visited:
        return []

    visited.add(wallet)
    dataset = []

    max_tx = 10 * (ss["time_window"] / 86400)

    # Build URL
    url = APILink(address=wallet, tx_type="erc20").get_api_link()

    async with sem:  # Ensure semaphore limits concurrency
        data = await fetch_data(url, session)
        if data is None:
            return []

    transactions = data['result']

    if len(transactions) > max_tx:
        print("Too much txs - EXC or phishing")
        return []

    tasks = []
    for tx in transactions:
        func_data = create_dataset(tx, wallet)
        if func_data is not None:
            dataset.append(func_data[0])
            from_address = func_data[0]['From']
            to_address = func_data[0]['To']

            # Create tasks for recursive calls
            tasks.append(erc20_transactions(from_address, depth + 1, visited, sem, session))
            tasks.append(erc20_transactions(to_address, depth + 1, visited, sem, session))

    # Await all tasks concurrently
    child_datasets = await asyncio.gather(*tasks)
    for child_dataset in child_datasets:
        if child_dataset:
            dataset.extend(child_dataset)

    return dataset


def run_asyncio_task(task):
    try:
        return asyncio.run(task)
    except RuntimeError as e:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(task)


def main(wallet: str, depth: int):
    sem = asyncio.Semaphore(10)  # Limit to 10 concurrent requests

    async def async_main():
        async with aiohttp.ClientSession() as session:
            result = await erc20_transactions(wallet, depth, sem=sem, session=session)
            return result

    return run_asyncio_task(async_main())
