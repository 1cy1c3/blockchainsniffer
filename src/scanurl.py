import streamlit as st

ss = st.session_state


class APILink:
    def __init__(self, address, tx_type, chain=None, start_block=None, end_block=None):
        self.chain = self.chain = chain if chain else ss["chain"]
        self.api_check = "module=account&action=txlist&address="
        self.address = address
        self.start_block = start_block if start_block else ss["start_block"]
        self.end_block = end_block if end_block else ss["end_block"]
        self.url = self.get_url()  # Ruft die Methode get_url auf, um self.url zu setzen
        self.attribute = self.get_attribute(tx_type)  # Ruft die Methode get_attribute auf, um self.attribute zu setzen
        self.key = self.get_key()  # Ruft die Methode get_key auf, um self.key zu setzen

    def get_url(self):
        if self.chain == "Ethereum":
            self.url = "https://api.etherscan.io/api?"
        elif self.chain == "Optimism":
            self.url = "https://api-optimistic.etherscan.io/api?"
        elif self.chain == "Arbitrum":
            self.url = "https://api.arbiscan.io/api?"
        elif self.chain == "Polygon":
            self.url = "https://api.polygonscan.com/api?"
        elif self.chain == "Base":
            self.url = "https://api.basescan.org/api?"
        elif self.chain == "Scroll":
            self.url = "https://api.scrollscan.com/api?"
        return self.url

    def get_attribute(self, tx_type):
        if tx_type == "erc20":
            self.attribute = "module=account&action=tokentx&address="
        elif tx_type == "normal":
            self.attribute = "module=account&action=txlist&address="
        else:
            self.attribute = None
        return self.attribute

    def get_key(self):
        if self.chain == "Ethereum":
            self.key = st.secrets["etherscan_api_key"]
        elif self.chain == "Optimism":
            self.key = st.secrets["optiscan_api_key"]
        elif self.chain == "Arbitrum":
            self.key = st.secrets["arbiscan_api_key"]
        elif self.chain == "Polygon":
            self.key = st.secrets["polyscan_api_key"]
        elif self.chain == "Base":
            self.key = st.secrets["basescan_api_key"]
        elif self.chain == "Scroll":
            self.key = st.secrets["scrollscan_api_key"]
        return self.key

    def get_api_link(self) -> str:
        api_url = (
                self.url + self.attribute + self.address + "&startblock=" + str(self.start_block) +
                "&endblock=" + str(self.end_block) + "&sort=asc&apikey=" + self.key
        )
        return api_url

    def check_wallet(self) -> str:
        api_url = (
                self.url + self.api_check + self.address + "&startblock=0" +
                "&endblock=99999999" + "&sort=asc&apikey=" + self.key
        )
        return api_url

    def check_for_contract(self) -> str:
        api_url = (
                self.url + "module=proxy&action=eth_getCode&address=" + self.address +
                "&tag=latest&apikey=" + self.key
        )
        return api_url

    def get_block_number(self, timestamp: int) -> str:
        api_url = (
                self.url + f"module=block&action=getblocknobytime&timestamp={timestamp}"
                           f"&closest=before&apikey={self.key}"
        )
        return api_url

    def get_block_reward(self, blocknumber: int):
        api_url = (
                self.url + f"module=block&action=getblockreward&blockno={blocknumber}"
                           f"&closest=before&apikey={self.key}"
        )
        return api_url

    def get_wallet_url(self) -> str:
        if self.chain == "Ethereum":
            return "https://etherscan.io/address/"
        elif self.chain == "Optimism":
            return "https://optimistic.etherscan.io/address/"
        elif self.chain == "Arbitrum":
            return "https://arbiscan.io/address/"
        elif self.chain == "Polygon":
            return "https://polygonscan.io/address/"
        elif self.chain == "Base":
            return "https://basescan.io/address/"
        elif self.chain == "Scroll":
            return "https://scrollscan.com/address/"

    def get_tx_url(self) -> str:
        if self.chain == "Ethereum":
            return "https://etherscan.io/tx/"
        elif self.chain == "Optimism":
            return "https://optimistic.etherscan.io/tx/"
        elif self.chain == "Arbitrum":
            return "https://arbiscan.io/tx/"
        elif self.chain == "Polygon":
            return "https://polygonscan.io/tx/"
        elif self.chain == "Base":
            return "https://basescan.io/tx/"
        elif self.chain == "Scroll":
            return "https://scrollscan.com/tx/"

    def get_int_tx(self):
        api_url = (
                self.url + "module=account&action=txlistinternal&address=" + self.address + "&startblock=0" +
                "&endblock=99999999" + "&sort=asc&apikey=" + self.key
        )
        return api_url
