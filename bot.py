import time
import requests
from web3 import Web3
from dotenv import dotenv_values

# ====== Load .env dan multi akun ======
def load_private_keys(path=".env"):
    keys = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("PRIVATE_KEY="):
                keys.append(line.split("=", 1)[1])
    return keys

PRIVATE_KEYS = load_private_keys()
RPC_URL = "https://sepolia-rollup.arbitrum.io/rpc"
CHAIN_ID = 421614

# ====== Faucet Config ======
FAUCETS = [
    {"name": "ATH", "url": "https://app.x-network.io/maitrix-faucet/faucet"},
    {"name": "USDE", "url": "https://app.x-network.io/maitrix-usde/faucet"},
    {"name": "LVL", "url": "https://app.x-network.io/maitrix-lvl/faucet"},
    {"name": "Virtual USD", "url": "https://app.x-network.io/maitrix-virtual/faucet", "retry": True},
]

def format_time(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h} jam {m} menit {s} detik"

def claim_faucet(address, faucet):
    headers = {"Content-Type": "application/json"}
    url = faucet["url"]
    name = faucet["name"]
    retry = faucet.get("retry", False)
    attempt = 1
    while attempt <= 3:
        try:
            res = requests.post(url, json={"address": address}, headers=headers)
            result = res.json()
            if "please wait" in result["message"].lower():
                seconds = int("".join(filter(str.isdigit, result["message"])))
                print(f"⏳   [{name}][{address}] Cooldown: {format_time(seconds)}")
            else:
                print(f"✅   [{name}][{address}] {result['message']} | Amount: {result.get('data', {}).get('amount')} | Tx: {result.get('data', {}).get('txHash', '-')}")
            break
        except Exception as e:
            if retry and attempt < 3:
                print(f"⚠️  [{name}][{address}] Error: {e}, retrying (attempt {attempt})...")
                time.sleep(3)
                attempt += 1
            else:
                print(f"❌   [{name}][{address}] Error: {e}")
                break

def run_faucet_bot():
    print(f"\n🕒 {time.ctime()} | Mulai proses faucet...\n")
    for pk in PRIVATE_KEYS:
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        account = w3.eth.account.from_key(pk)
        address = account.address
        print(f"---- Wallet: {address} ----")
        for faucet in FAUCETS:
            claim_faucet(address, faucet)
            time.sleep(1.5)
        print(f"---- Selesai wallet {address} ----\n")
        time.sleep(2)
    print("✅   Semua faucet selesai diproses.\n")

# ====== Mint & Stake Config ======

CONTRACTS = {
    "ausd": {
        "name": "Mint AUSD dari ATH",
        "mint_contract": "0x2cFDeE1d5f04dD235AEA47E1aD2fB66e3A61C13e",
        "token_contract": "0x1428444Eacdc0Fd115dd4318FcE65B61Cd1ef399",
        "selector": "0x1bf6318b",
        "decimals": 18
    },
    "vusd": {
        "name": "Mint vUSD dari VIRTUAL",
        "mint_contract": "0x3dCACa90A714498624067948C092Dd0373f08265",
        "token_contract": "0xFF27D611ab162d7827bbbA59F140C1E7aE56e95C",
        "selector": "0xa6d67510",
        "decimals": 9
    }
}

STAKING = {
    "ausd": {
        "staking_contract": "0x054de909723ECda2d119E31583D40a52a332f85c",
        "token_contract": "0x78De28aABBD5198657B26A8dc9777f441551B477",
        "decimals": 18
    },
    "vusd": {
        "staking_contract": "0x5bb9Fa02a3DCCDB4E9099b48e8Ba5841D2e59d51",
        "token_contract": "0xc14A8E2Fc341A97a57524000bF0F7F1bA4de4802",
        "decimals": 9
    },
    "usde": {
        "staking_contract": "0x3988053b7c748023a1aE19a8ED4c1Bf217932bDB",
        "token_contract": "0xf4BE938070f59764C85fAcE374F92A4670ff3877",
        "decimals": 18
    },
    "lvlusd": {
        "staking_contract": "0x5De3fBd40D4c3892914c3b67b5B529D776A1483A",
        "token_contract": "0x8802b7bcF8EedCc9E1bA6C20E139bEe89dd98E83",
        "decimals": 18
    }
}

def get_web3():
    return Web3(Web3.HTTPProvider(RPC_URL))

def get_raw_balance(w3, token_address, address):
    abi = [{
        "name": "balanceOf",
        "type": "function",
        "inputs": [{"name": "owner", "type": "address"}],
        "outputs": [{"name": "balance", "type": "uint256"}],
        "stateMutability": "view"
    }]
    contract = w3.eth.contract(address=w3.to_checksum_address(token_address), abi=abi)
    return contract.functions.balanceOf(address).call()

def get_erc20_balance(w3, token_address, decimals, address):
    raw = get_raw_balance(w3, token_address, address)
    return raw / (10 ** decimals)

def approve_erc20(w3, private_key, token_address, spender, amount_wei, address):
    abi = [{
        "name": "approve",
        "type": "function",
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable"
    }]
    contract = w3.eth.contract(address=w3.to_checksum_address(token_address), abi=abi)
    nonce = w3.eth.get_transaction_count(address)
    tx = contract.functions.approve(spender, amount_wei).build_transaction({
        "from": address,
        "gas": 100000,
        "gasPrice": w3.eth.gas_price,
        "nonce": nonce,
        "chainId": CHAIN_ID
    })
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"[+] Transaksi approve dikirim: {tx_hash.hex()}")
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print("[+] Approve sukses!")
    time.sleep(5)

def mint_token(w3, account, private_key, token):
    c = CONTRACTS[token]
    address = account.address
    raw_balance = get_raw_balance(w3, c["token_contract"], address)
    if raw_balance == 0:
        print(f"[!] Tidak ada saldo {token.upper()} untuk mint.")
        return
    approve_erc20(w3, private_key, c["token_contract"], c["mint_contract"], raw_balance, address)
    encoded_amount = hex(raw_balance)[2:].zfill(64)
    data = c["selector"] + encoded_amount
    nonce = w3.eth.get_transaction_count(address)
    tx = {
        "to": c["mint_contract"],
        "value": 0,
        "gas": 300000,
        "gasPrice": w3.eth.gas_price,
        "nonce": nonce,
        "data": data,
        "chainId": CHAIN_ID
    }
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"[+] Mint {token.upper()} tx: {tx_hash.hex()}")
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"[+] Mint {token.upper()} sukses!")
    time.sleep(5)

def stake_token(w3, account, private_key, token):
    c = STAKING[token]
    address = account.address
    raw_balance = get_raw_balance(w3, c["token_contract"], address)
    if raw_balance == 0:
        print(f"[!] Tidak ada saldo {token.upper()} untuk stake.")
        return
    approve_erc20(w3, private_key, c["token_contract"], c["staking_contract"], raw_balance, address)
    data = "0xa694fc3a" + hex(raw_balance)[2:].zfill(64)
    nonce = w3.eth.get_transaction_count(address)
    tx = {
        "to": w3.to_checksum_address(c["staking_contract"]),
        "value": 0,
        "gas": 300000,
        "gasPrice": w3.eth.gas_price,
        "nonce": nonce,
        "data": data,
        "chainId": CHAIN_ID
    }
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"[+] Stake {token.upper()} tx: {tx_hash.hex()}")
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"[+] Stake {token.upper()} sukses!")
    time.sleep(5)

def run_for_account(index, private_key):
    w3 = get_web3()
    account = w3.eth.account.from_key(private_key)
    address = account.address
    print(f"\n=== Akun ke-{index+1}: {address} ===")
    print("[*] Cek saldo ATH & VIRTUAL:")
    for t in ["ausd", "vusd"]:
        src = "ATH" if t == "ausd" else "VIRTUAL"
        bal = get_erc20_balance(w3, CONTRACTS[t]["token_contract"], CONTRACTS[t]["decimals"], address)
        print(f"{src}: {bal}")
        if bal > 0:
            mint_token(w3, account, private_key, t)
    print("[*] Cek saldo untuk staking:")
    for k in STAKING:
        bal = get_erc20_balance(w3, STAKING[k]["token_contract"], STAKING[k]["decimals"], address)
        print(f"{k.upper()}: {bal}")
        if bal > 0:
            stake_token(w3, account, private_key, k)
    print("[✓] Selesai untuk akun ini.")

# ====== Menu Utama ======
def show_menu():
    print("=== MAITRIX BOT MENU ===")
    print("1. Claim faucet")
    print("2. Auto stake")
    choice = input("Pilih opsi (1/2): ").strip()
    if choice == "1":
        run_faucet_bot()
    elif choice == "2":
        for i, pk in enumerate(PRIVATE_KEYS):
            run_for_account(i, pk)
    else:
        print("[!] Pilihan tidak valid.")

if __name__ == "__main__":
    show_menu() 
