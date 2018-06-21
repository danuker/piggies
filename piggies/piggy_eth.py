# Command used by Ethereum Wallet for fast sync:
# /home/dan/.config/Ethereum Wallet/binaries/Geth/unpacked/geth --syncmode fast --cache 1024 --datadir /media/dan/Wilderness/Blockchains/eth/

from pexpect import popen_spawn

from decimal import Decimal

class PiggyETH:
    wei_per_eth = Decimal('1e18')

     def __init__(self,
                  wallet_bin_path,
                  datastore_path,
                  wallet_filename,
                  wallet_password,
                  rpcport,
                  ):
        """
        Manage an Ethereum Parity wallet

        :param wallet_bin_path: Path to Parity wallet executable
        :param datastore_path: Path to datastore directory (which includes wallet files and blockchain)
        :param wallet_filename: Name of wallet file to use (must be in `datastore_path/keys`)
        :param wallet_password: Password to enter for decrypting wallet
        :param rpcport: Local port to start the wallet RPC server on
        """

        self.wallet_bin_path = wallet_bin_path
        self.datastore_path = datastore_path
        self.wallet_filename = wallet_filename
        self.wallet_password = wallet_password
        self.rpcport = rpcport
