import discord
from discord.ext import commands
from web3 import Web3
import os
from dotenv import load_dotenv
import logging
import time


load_dotenv()

TOKEN_DISCORD = os.getenv("TOKEN_DISCORD")
MONAD_RPC = os.getenv("MONAD_RPC")
NFT_CONTRACT = os.getenv("NFT_CONTRACT")
TOKEN_ID = int(os.getenv("TOKEN_ID", 0))
ROLE_NAME = os.getenv("ROLE_NAME") 
MINIMUM_MON_AMOUNT = 0.0001 
VALIDATION_TIME_LIMIT = 600


logging.basicConfig(level=logging.INFO)

# ABI for ERC-1155 (balanceOf(wallet, tokenId))
CONTRACT_ABI_ERC1155 = [
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_id", "type": "uint256"}
        ],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    }
]

# Inicialize Web3
w3 = Web3(Web3.HTTPProvider(MONAD_RPC))

# Converte address to checksum
NFT_CONTRACT = Web3.to_checksum_address(NFT_CONTRACT)

# Bot Config
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True  # Permite gerenciar cargos dos membros
bot = commands.Bot(command_prefix="!", intents=intents)

pending_wallets = {}


class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Link Your Wallet", style=discord.ButtonStyle.blurple, custom_id="link_wallet")
    async def link_wallet(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Opens a modal window for the user to enter the wallet."""
        await interaction.response.send_modal(WalletModal())

    @discord.ui.button(label="Submit Transaction", style=discord.ButtonStyle.gray, custom_id="submit_transaction")
    async def submit_transaction(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Opens a modal for the user to enter the transaction hash."""
        await interaction.response.send_modal(TransactionModal())

# Modal para o usuário inserir a Wallet
class WalletModal(discord.ui.Modal, title="Enter Your Wallet Address"):
    wallet = discord.ui.TextInput(label="Wallet Address", placeholder="0x123456789...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        """Called when the user submits the wallet for validation."""
        carteira = self.wallet.value

        if not Web3.is_address(carteira):
            await interaction.response.send_message("❌ Wallet Invalid. Please enter a valid wallet address.", ephemeral=True)
            return

        carteira = Web3.to_checksum_address(carteira)

        # Armazena a carteira e o tempo da solicitação
        pending_wallets[interaction.user.id] = {"wallet": carteira, "timestamp": time.time()}

        await interaction.response.send_message(
            f"⚠️ Please send **exactly {MINIMUM_MON_AMOUNT} MON** to your own wallet `{carteira}` to verify ownership.\n"
            "This must be done on **Monad Testnet**.\n"
            "You have **10 minutes** to complete this transaction.\n\n"
            "Once you've sent the MON, click **Submit Transaction** and enter the transaction hash.",
            ephemeral=True
        )

# Modal para o usuário inserir o Hash da Transação
class TransactionModal(discord.ui.Modal, title="Enter Your Transaction Hash"):
    tx_hash = discord.ui.TextInput(label="Transaction Hash", placeholder="0x...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        """Called when the user enters the transaction hash."""
        tx_hash = self.tx_hash.value

        # Verifica a transação na blockchain
        await check_transaction(interaction, tx_hash)

### ⬇️ FUNÇÃO PARA CHECAR A TRANSAÇÃO NA BLOCKCHAIN ⬇️ ###
async def check_transaction(interaction: discord.Interaction, tx_hash: str):
    """Validates whether the transaction was made correctly and continues with the NFT verification."""
    user_id = interaction.user.id

    if user_id not in pending_wallets:
        await interaction.response.send_message("❌ No pending wallet validation found. Please start again by clicking **Link Your Wallet**.", ephemeral=True)
        return

    wallet_info = pending_wallets[user_id]
    carteira = wallet_info["wallet"]
    start_time = wallet_info["timestamp"]

    # Verifica se o tempo expirou
    if time.time() - start_time > VALIDATION_TIME_LIMIT:
        del pending_wallets[user_id]
        await interaction.response.send_message("❌ Validation time expired. Please start again by clicking **Link Your Wallet**.", ephemeral=True)
        return

    try:
        # Busca a transação na blockchain
        tx = w3.eth.get_transaction(tx_hash)

        if tx is None:
            await interaction.response.send_message("❌ Transaction not found. Please check the hash and try again.", ephemeral=True)
            return

        # Verifica se a transação foi enviada da carteira para ela mesma e com o valor correto
        if tx["from"].lower() == carteira.lower() and tx["to"].lower() == carteira.lower() and tx["value"] >= Web3.to_wei(MINIMUM_MON_AMOUNT, "ether"):
            del pending_wallets[user_id]
            await verificar_wallet(interaction, carteira)
        else:
            await interaction.response.send_message("⚠️ Invalid transaction. Ensure you sent MON to **yourself** with the correct amount.", ephemeral=True)

    except Exception as e:
        logging.error(f"Error checking transaction: {e}")
        await interaction.response.send_message("⚠️ Error fetching transaction. Please try again later.", ephemeral=True)

### ⬇️ FUNÇÃO PARA VERIFICAR NFT E ATRIBUIR CARGO ⬇️ ###
async def verificar_wallet(interaction: discord.Interaction, carteira: str):
    """Checks if a wallet has the ERC-1155 NFT and assigns the role."""
    try:
        # Interage com o contrato ERC-1155
        contrato_nft = w3.eth.contract(address=NFT_CONTRACT, abi=CONTRACT_ABI_ERC1155)

        try:
            balance = contrato_nft.functions.balanceOf(carteira, TOKEN_ID).call()
        except Exception as e:
            logging.error(f"balanceOf call error: {e}")
            await interaction.response.send_message(f"⚠️ Error checking NFT balance: {str(e)}", ephemeral=True)
            return

        if balance > 0:
            await atribuir_cargo(interaction, ROLE_NAME)
            await interaction.response.send_message(f"✅ You own `{balance}` Sky Guardian NFTs and have been verified! 🎉", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ You do not own 5 Sky Guardian NFTs.", ephemeral=True)

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        await interaction.response.send_message(f"⚠️ Unexpected error: {str(e)}", ephemeral=True)

### ⬇️ FUNÇÃO PARA ATRIBUIR O CARGO ⬇️ ###
async def atribuir_cargo(interaction: discord.Interaction, role_name: str):
    """Assigns the role to the user if they own NFTs."""
    guild = interaction.guild
    member = interaction.user

    role = discord.utils.get(guild.roles, name=role_name)
    if role and role not in member.roles:
        await member.add_roles(role)

### ⬇️ COMANDO PARA ENVIAR O PAINEL DE VERIFICAÇÃO ⬇️ ###
@bot.command(name="panel")
async def panel(ctx):
    """Sends a panel with verification buttons."""
    embed = discord.Embed(
        title="Sky Guardian NFT Verification",
        description="1️⃣ Click **Link Your Wallet** to register your wallet.\n"
                    "2️⃣ Send MON to yourself to verify ownership.\n"
                    "3️⃣ Click **Submit Transaction** and enter the transaction hash.\n"
                    "4️⃣ If verified, you will receive the **Early Holder** role. \n"
                    "PS: You must be the holder of at least 5 Sky Guardian NFTs.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=VerifyView())

# Inicia o bot
bot.run(TOKEN_DISCORD)
