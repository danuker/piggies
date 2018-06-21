# Command used by Ethereum Wallet for fast sync:
# /home/dan/.config/Ethereum Wallet/binaries/Geth/unpacked/geth --syncmode fast --cache 1024 --datadir /media/dan/Wilderness/Blockchains/eth/

import logging
import jsonrpclib
import socket

from pexpect import popen_spawn
from decimal import Decimal

from processing import wait_for_success, check_port

logger = logging.getLogger('piggy_logs')

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
        :param wallet_filename: Name of wallet file to use (must be in `datastore_path/keys/ethereum/`)
        :param wallet_password: Password to enter for decrypting wallet
        :param rpcport: Local port to start the wallet RPC server on
        """

        self.wallet_bin_path = wallet_bin_path
        self.datastore_path = datastore_path
        self.wallet_filename = wallet_filename
        self.wallet_password = wallet_password
        self.rpcport = check_port(rpcport, 'rpcport')

        self.server = None
        self.process = None
        self.accounts = None

    def start_server(self):
        if self._rpc_loaded():
            return

        command = [
            self.wallet_bin_path,
            '-d', self.datastore_path,
            '--jsonrpc-port', str(self.rpcport),
            '--light',
        ]

        logger.info("Starting ETH wallet: {}".format(' '.join(command)))
        wallet_proc = popen_spawn.PopenSpawn(command)

        wait_for_success(self._rpc_loaded, 'ETH RPC')


    def _rpc_loaded(self):
        """Attempt a connection to the RPC"""
        self._connect_if_needed()
        try:
            import ipdb; ipdb.set_trace()
            self.server.eth_syncing()
            return True
        except socket.error:
            return False

    def _connect_if_needed(self):
        if self.server is None:
            self.server = jsonrpclib.Server(
                "http://127.0.0.1:{}".format(self.rpcport)
            )