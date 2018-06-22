import logging
import os
import socket
import subprocess
import pexpect
from pexpect import popen_spawn
from decimal import Decimal
from time import time

import jsonrpclib
import requests

from .processing import inexact_to_decimal, wait_for_success, check_port

logger = logging.getLogger('piggy_logs')

class PiggyXMR:
    # Atomic units in 1 XMR
    ATOMS = Decimal('1e12')

    def __init__(self,
                 daemon_bin_path,
                 wallet_bin_path,
                 datastore_path,
                 wallet_filename,
                 wallet_password,
                 daemon_port,
                 rpcport,
                 ):
        """
        Manage a Monero wallet

        :param daemon_bin_path: Path to Monero daemon executable
        :param wallet_bin_path: Path to Monero RPC wallet executable
        :param datastore_path: Path to datastore directory (which includes wallet files and blockchain)
        :param wallet_filename: Name of wallet file to use (must be in `datastore_path/wallets`)
        :param wallet_password: Password to enter for decrypting wallet
        :param daemon_port: Local port to start Monero daemon on
        :param rpcport: Local port to start the wallet RPC server on
        """

        self.daemon_bin_path = daemon_bin_path
        self.wallet_bin_path = wallet_bin_path
        self.datadir = datastore_path
        self.wallet_filename = wallet_filename
        self.wallet_password = wallet_password

        self.rpcport = check_port(rpcport, 'rpcport')
        self.daemon_port = check_port(daemon_port, 'daemon_port')
        self.daemon_address = '127.0.0.1:{}'.format(self.daemon_port)
        self.server = None

    def start_server(self):
        """Start the daemon and the wallet RPC server"""

        self._check_version()
        self._start_monero_daemon()
        self._start_monero_wallet()

    def _check_version(self):
        """Check that we have the correct version"""
        process = pexpect.spawn(self.wallet_bin_path, ['--version'])

        try:
            process.expect_exact("Monero 'Lithium Luna' (v0.12.2.0-release)")
        except pexpect.exceptions.EOF:
            print('############### OUTPUT ###############')
            print(repr(process.read()))
            print('############### OUTPUT ###############')
            raise ValueError('Error! Version changed on XMR wallet.')

    def _start_monero_daemon(self):
        """Run the Monero daemon"""
        if self._daemon_rpc_loaded():
            logger.info('XMR Daemon already loaded!')
            return

        command = [
            self.daemon_bin_path,

            '--data-dir',
            self.datadir,  # Where to keep data & config

            '--rpc-bind-port={}'.format(self.daemon_port),

            '--detach',
            '--non-interactive',
            '--log-level', '1',
        ]

        logger.info("Starting XMR daemon: {}".format(' '.join(command)))
        subprocess.Popen(command)

        wait_for_success(self._daemon_rpc_loaded, 'Daemon RPC')

    def _daemon_rpc_loaded(self):
        try:
            requests.post("http://{}/getheight".format(self.daemon_address), json={})
            return True
        except requests.exceptions.ConnectionError:
            return False

    def _start_monero_wallet(self):
        """Run the Monero wallet, which connects to the daemon"""

        if self._wallet_rpc_loaded():
            logger.info('XMR Wallet already loaded!')
            return

        command = [
            self.wallet_bin_path,
            '--trusted-daemon',  # We trust our own daemon. If you use a different daemon, remove this
            '--daemon-address',
            self.daemon_address,
            '--rpc-bind-port={}'.format(self.rpcport),
            '--wallet-file',
            os.path.join(self.datadir, 'wallets', self.wallet_filename),
            '--disable-rpc-login',
            '--prompt-for-password'
        ]

        logger.info("Starting XMR wallet: {}".format(' '.join(command)))
        wallet_proc = popen_spawn.PopenSpawn(command)
        logger.info("Sending password")
        wallet_proc.sendline(self.wallet_password)
        logger.info("Sent password")

        wait_for_success(self._wallet_rpc_loaded, 'Wallet RPC')

    def _wallet_rpc_loaded(self):
        try:
            self.get_balance()
            return True
        except socket.error:
            return False

    def stop_server(self):
        """Stop the wallet and the daemon"""
        self._connect_if_needed()

        try:
            self.server.stop_wallet()
            logger.info("stopped wallet")
        except TypeError:
            logger.warn('Not sure if wallet stopped. Received None response!')

        req = requests.post("http://{}/stop_daemon".format(self.daemon_address))

        if req.status_code == 200:
            logger.info("stopped daemon")
        else:
            raise ValueError('Unable to stop daemon!\nSTATUS: {}\nText:{}'.format(req.status, req.text))

    def _connect_if_needed(self):
        if self.server is None:
            self.server = jsonrpclib.Server("http://127.0.0.1:{}/json_rpc".format(self.rpcport))

    def get_balance(self):
        """Return the amount we have in the wallet, confirmed by the blockchain"""
        self._connect_if_needed()

        # Money is unlocked 10 Monero blocks after receiving (~15 minutes)
        return Decimal(self.server.getbalance()['unlocked_balance']) / self.ATOMS

    def get_receive_address(self):
        """Returns a new address where we can receive XMR"""
        self._connect_if_needed()

        result = self.server.make_integrated_address()
        return result['integrated_address']

    def suggest_miner_fee(self):
        """
        Returns miner fee to use, for typical transaction
        Note: Sadly, we can only do this if we have SOME funds, as far as I know.
            Please submit a pull request if you can do it some other way!
        """

        # TODO: Use get_fee_estimate in the daemon

        self._connect_if_needed()

        result = self.server.transfer(
            destinations=[
                {'address': self.get_receive_address(), 'amount': 1}
            ],
            do_not_relay=True
        )

        return Decimal(result['fee']) / self.ATOMS

    def transactions_since(self, since_unix_time):
        """Gets incoming transactions since specified time

        :param since_unix_time: integer or float, unix time
        :return transactions: DataFrame of transactions
            Each row in the DataFrame has amount, txid, and time of each transaction
        """

        self._connect_if_needed()

        history = self.server.get_transfers(**{'in': True})

        return self._process_history(history, since_unix_time)

    @classmethod
    def _process_history(cls, history, since_unix_time):
        """Process the transaction history data"""

        if 'in' in history.keys():
            history_income = history['in']
            return [
                {
                    'txid': txn['txid'],
                    'time': txn['timestamp'],
                    'value': inexact_to_decimal(txn['amount']) / cls.ATOMS,
                }
                for txn in history_income
                if
                    txn['timestamp'] >= float(since_unix_time)
                and
                    txn['type'] == 'in'
                and
                    txn['amount'] > 0
            ]
        else:
            # We don't have the "in" key in the dict, so we don't have any incoming transactions.
            return []

    def perform_transaction(self, net_amount, miner_fee, target_address):
        """
        Send Monero to target_address (total cost: net_amount + miner_fee)

        Note: here, miner_fee is only used as a check (must equal recent `suggest_miner_fee` output).
        """

        self._connect_if_needed()

        assert isinstance(net_amount, Decimal)
        assert isinstance(miner_fee, Decimal)

        # Convert units (Multiply by ATOMS)
        net_amount_atoms = net_amount * self.ATOMS
        miner_fee_atoms = miner_fee * self.ATOMS

        # Check that the amounts are expressible as integer atoms
        assert int(net_amount_atoms) == net_amount_atoms
        assert int(miner_fee_atoms) == miner_fee_atoms

        tx = self.server.transfer(
            destinations=[
                {'address': target_address, 'amount': int(net_amount_atoms)}
            ],
            do_not_relay=True,
            get_tx_hex=True
        )

        if tx['fee'] != miner_fee_atoms:
            raise ValueError(
                'Miner fee no longer equals the desired fee. Please use a freshly estimated fee, and make sure the wallet is up-to-date with the blockchain.\n'
                'Desired fee: {}\n'
                'New estimated fee: {}\n'.format(
                    miner_fee, Decimal(tx['fee']) / self.ATOMS
                )
            )

        success = self._broadcast( tx)

        if success:
            logger.warning("Signed TX: {}".format(tx))
            logger.warning("Broadcast TX ID: {}".format(tx['tx_hash']))
            return tx['tx_hash']
        else:
            raise BaseException("XRP Transaction broadcast fail for: {}".format(tx))

    def _broadcast(self, tx):
        """Broadcast the transaction to the blockchain

        :param tx: Dictionary containing transaction data (tx_blob is mandatory)
        """

        req = requests.post(
            "http://{}/send_raw_transaction".format(self.daemon_address),
            json={'tx_as_hex': tx['tx_blob'], 'do_not_relay': False}
        )

        error = req.json().get('error')
        logger.warning("Broadcasted transaction: {}".format(req.json()))

        if error is not None or req.json()['status'] == 'Failed':
            raise ValueError(
                "Error Broadcasting transaction: ({})\n"
                "TXN: {}\n".format(error, tx)
            )
        elif req.ok:
            return True
        else:
            raise ValueError("Unsuccessful request to broadcast transaction: {}")

    def _refresh(self):
        logger.debug('Rescanning blockchain for wallet...')
        t1 = time()
        res = self.server.rescan_blockchain()
        t2 = time()
        logger.debug("Blockchain Rescanned (took {}s): {}".format(t2-t1, res))

        logger.debug('flushing tx pool for daemon...')
        t1 = time()
        res = requests.post(
            "http://{}/flush_txpool".format(self.daemon_address),
            json={}
        )
        t2 = time()
        logger.debug("Flushed tx pool (took {}s): {}".format(t2-t1, res))
