# Monad NFT Verifier Bot for Discord

A Discord bot written in Python that verifies whether a user holds a specific ERC-1155 NFT on the **Monad Testnet** and automatically assigns them a role in the server if eligible.

---

## 🚀 Features

- Verifies wallet ownership by checking a self-transaction.
- Confirms ERC-1155 NFT balance.
- Automatically assigns a Discord role (e.g., `early-holder`) to verified users.
- Secure and private interaction using ephemeral messages.
- Built-in time limit for verification to prevent abuse.

---

## 📦 Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
```

Required Python packages include:

- `discord.py==2.3.2`
- `web3==6.11.1`
- `python-dotenv==1.0.1`
- `requests==2.31.0`
- `aiohttp==3.9.3`

---

## ⚙️ Environment Setup

Create a `.env` file or copy from `.env.example`:

```bash
cp .env.example .env
```

Set the following environment variables:

```env
TOKEN_DISCORD=your_discord_bot_token
MONAD_RPC=https://testnet-rpc.monad.xyz
NFT_CONTRACT=0x...         # Address of the ERC-1155 contract
TOKEN_ID=0                 # Token ID of the NFT to check
ROLE_NAME=early-holder     # Role to assign upon successful verification
```

---

## 🧠 How It Works

1. A user clicks **Link Wallet** and submits their wallet address.
2. They are asked to send a small amount of MON to themselves to verify ownership.
3. They submit the transaction hash.
4. If valid, the bot checks for NFT balance.
5. If the user owns the NFT, they receive the specified role.

---

## 🛠 Usage

Run the bot with:

```bash
python checker.py
```

In Discord, use the command:

```
!panel
```

This will post a verification panel with interactive buttons.

---

## 🛡 Security Notes

- Wallet addresses and transaction hashes are only temporarily stored during the verification window.
- All user messages are sent as ephemeral, visible only to the user.

---

## 📄 License

MIT License. Feel free to use and modify this bot for your community.
