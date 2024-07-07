import requests
import json
import asyncio
import aiohttp

import streamlit as st
import src.defillama as defillama

from typing import Any, Set, List, Dict, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from src.scanurl import APILink
from datetime import datetime

ss = st.session_state


@st.cache_data(show_spinner=False)
def is_contract(address: str, chain: str) -> bool:
    # Build URL
    url = APILink(address=address, tx_type=None, chain=chain).check_for_contract()

    # Send Request
    response = requests.get(url)
    if response.status_code != 200:
        print("Error for is_contract:", response.status_code)
        return False

    data = json.loads(response.text)

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
def get_block_by_timestamp(timestamp: int, chain: str) -> str:
    url = APILink(address=None, tx_type=None, chain=chain).get_block_number(timestamp)
    response = requests.get(url)
    data = response.json()

    if data['message'] != 'OK':
        return "0"
    return data['result']


def create_dataset(tx: dict, min_value: int, chain: str) -> dict[str, str | int | Any]:
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

    if (not is_contract(sender, chain) and not is_contract(to, chain)
            and to != st.secrets["null"] and sender != st.secrets["null"]
            and tx_hash not in ss["tx_hashes"]):

        token_price = defillama.get_historical_price(tx["timeStamp"], tx["contractAddress"], chain)
        token_amount = int(value_raw) * 10 ** - int(decimals)

        if token_price and token_amount:
            value_usd = round(token_amount * token_price, 0)
            if value_usd >= min_value:

                dataset["Hash"] = tx_hash
                dataset["Time"] = timestamp_to_date(int(timestamp))
                dataset["From"] = sender
                dataset["To"] = to
                dataset["Token_Amount"] = token_amount
                dataset["Value_USD"] = value_usd
                dataset["Token"] = name
                dataset["Symbol"] = symbol

                ss["tx_hashes"].append(tx_hash)
                ss["counter"] += 1
                print(f"counter: {ss['counter']}")

                return dataset


@st.cache_data(show_spinner=False)
def timestamp_to_date(timestamp: int) -> str:
    # Convert timestamp to date
    date = datetime.fromtimestamp(timestamp)
    return date.strftime('%Y/%m/%d %H:%M:%S')


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10))
async def fetch_data(url: str, session: aiohttp.ClientSession) -> Optional[Dict]:
    async with session.get(url) as response:
        response.raise_for_status()
        data = await response.json()
        if data['status'] != '1':
            raise ValueError("Error for fetch_data:", data['status'])
        return data


async def erc20_transactions(wallet: str, depth: int, min_value: int, start_block: int, end_block: int, chain: str,
                             visited: Set[str] = None, _sem: asyncio.Semaphore = None,
                             _session: aiohttp.ClientSession = None) -> List[Dict]:
    if visited is None:
        visited = set()

    if depth < 1 or wallet in visited:
        return []

    visited.add(wallet)
    dataset = []

    max_tx = 10 * (ss["time_window"] / 86400)

    # Build URL
    url = APILink(
        address=wallet, tx_type="erc20", start_block=start_block, end_block=end_block, chain=chain,
                  ).get_api_link()

    async with _sem:  # Ensure semaphore limits concurrency
        data = await fetch_data(url, _session)
        if data['message'] == 'NOTOK':
            return []

    transactions = data['result']

    if len(transactions) > max_tx:
        print("Too much txs - EXC or phishing")
        return []

    tasks = []

    for tx in transactions:
        func_data = create_dataset(tx, min_value, chain)
        if func_data is not None:
            dataset.append(func_data)
            from_address = func_data['From']
            to_address = func_data['To']

            # Create tasks for recursive calls
            if func_data['To'].lower() == wallet.lower():
                tasks.append(erc20_transactions(
                    from_address, depth - 1, min_value, start_block, end_block, chain, visited, _sem, _session)
                )
            else:
                tasks.append(erc20_transactions(
                    to_address, depth - 1, min_value, start_block, end_block, chain, visited, _sem, _session)
                )

    # Await all tasks concurrently
    child_datasets = await asyncio.gather(*tasks)
    for child_dataset in child_datasets:
        if child_dataset:
            dataset.extend(child_dataset)

    return dataset


def run_asyncio_task(task):
    try:
        return asyncio.run(task)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(task)


@st.cache_resource(show_spinner=False)
def main(wallet: str, depth: int, min_value: int, start_block: int, end_block: int, chain: str) -> List[Dict]:
    sem = asyncio.Semaphore(5)  # Limit to 5 concurrent requests

    async def async_main():
        async with aiohttp.ClientSession() as session:
            result = await erc20_transactions(wallet, depth, min_value, start_block, end_block, chain, _sem=sem,
                                              _session=session)
            return result

    return run_asyncio_task(async_main())
