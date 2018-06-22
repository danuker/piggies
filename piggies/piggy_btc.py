import json
import logging
import numbers
import os
import pexpect
import socket
import urllib.request, urllib.error, urllib.parse

import jsonrpclib

from pexpect import popen_spawn
from decimal import Decimal

from .processing import inexact_to_decimal, wait_for_success, check_port


logger = logging.getLogger('piggy_logs')


class PiggyBTC:
    def __init__(
            self,
            wallet_bin_path,
            datastore_path,
            wallet_filename,
            wallet_password,
            rpcuser,
            rpcpassword,
            rpcport
            ):

        """Manage a Bitcoin wallet using Electrum.

        Supported wallet version:
        https://download.electrum.org/3.1.3/Electrum-3.1.3.tar.gz

        :param wallet_bin_path: Path to Electrum wallet executable
        :param datastore_path: Path to datastore directory (which includes wallet files and block headers)
        :param wallet_filename: Name of wallet file to use (must be in `datastore_path/wallets`)
        :param wallet_password: Password to enter for decrypting wallet
        :param rpcport: Local port to start the wallet RPC server on

        """

        self.wallet_bin_path = wallet_bin_path
        self.datadir = datastore_path
        self.wallet_filename = wallet_filename
        self.wallet_password = wallet_password

        self.rpcuser = rpcuser
        self.rpcpassword = rpcpassword

        self.rpcport = check_port(rpcport, 'rpcport')
        self.server = None

    def _execute_electrum_command(
            self,
            command,
            expect=None,
            stdin_text=None,
            quiet=False,
            wait_for_command=True
            ):

        """
        Runs commands using the Electrum binary

        :param command: List of string CLI arguments for the Electrum wallet
        :param expect: Command output to expect, wait for, read, and match.
        :param stdin_text: String or None; if string: pass in string as stdin to Electrum
        :param quiet: Suppress printing process details
        :param wait_for_command: Wait for the program to end (blocking call).

            If true, it uses pexpect with  a pseudo-terminal, but the terminal quits in the following cases:
                - when the command quits (and it kills the command's children processes)
                - when the Python script is interrupted
            If false, it uses Popen, which does not provide a pseudo-terminal (losing, say, password input
            capability), but it lets the spawned process and its children survive past the Python script.
        """

        done_str = 'Check stdout/stderr here.' if stdin_text else ''

        if quiet is False:
            logger.info('#######################')
            logger.info('Executing "{}". {}'.format(command, done_str))

        wallet_file = os.path.join(self.datadir, 'wallets', self.wallet_filename)

        self._check_paths(wallet_file)

        if wait_for_command:
            process = pexpect.spawn(
                self.wallet_bin_path,
                command + [
                    '--dir', self.datadir,
                    '--wallet', wallet_file
                ]
            )

            if expect:
                process.expect_exact(expect)

            if stdin_text is not None:
                process.sendline(stdin_text)

            output = process.read()

            if quiet is False:
                logger.warning(
                    'Process printed EOF.\n'
                    '### OUTPUT:\n{}\n###'.format(output)
                )

            status = process.wait()

            if quiet is False:
                logger.info("Exit code {}".format(status))

        else:
            if expect or stdin_text:
                raise ValueError(
                    "Can not properly expect or send text if we don't wait for command."
                )

            process = popen_spawn.PopenSpawn(
                [self.wallet_bin_path] +
                command + [
                    '--dir', self.datadir,
                    '--wallet', wallet_file
                ]
            )

            output = None

        return process, output

    def _check_paths(self, wallet_file):
        """
        Ensure existence of wallet binary, datadir, and wallet file

        :param wallet_file: Path to wallet file
        """

        os.stat(os.path.abspath(self.wallet_bin_path))
        try:
            os.stat(os.path.abspath(self.datadir))
        except OSError:
            os.makedirs(os.path.abspath(self.datadir))

        try:
            os.stat(os.path.abspath(wallet_file))
        except OSError:
            logger.critical(
                'Missing wallet file "{}"!\n Please create the wallet or change the path.'
                .format(os.path.abspath(wallet_file))
            )
            raise

    def _connect_if_needed(self):
        if self.server is None:
            self.server = jsonrpclib.Server("http://{}:{}@127.0.0.1:{}".format(
                    self.rpcuser,
                    self.rpcpassword,
                    self.rpcport
            ))

    def _check_version(self):
        """Check that the version is supported."""

        try:
            _, status = self._execute_electrum_command(
                    ['version'],
                    expect='3.1.3',
                    quiet=True
            )
        except pexpect.exceptions.EOF:
            raise ValueError('Electrum help payto does not match our expectation.')

    def start_server(self):
        """Start the RPC server

        Use the wallet and datastore paths specified in config.
        """

        self._execute_electrum_command(['setconfig', 'rpcuser', str(self.rpcuser)])
        self._execute_electrum_command(['setconfig', 'rpcpassword', str(self.rpcpassword)])
        self._execute_electrum_command(['setconfig', 'rpcport', str(self.rpcport)])
        self._execute_electrum_command(['daemon', 'start'], wait_for_command=False)

        # Wait for daemon to start
        wait_for_success(self._daemon_rpc_loaded, 'BTC Daemon RPC')

        # Send password (this is NOT stdin)
        self._execute_electrum_command(
                ['daemon', 'load_wallet'],
                ['Password:', 'true'], self.wallet_password
                )

        self._check_version()

    def _daemon_rpc_loaded(self):
        """Check whether RPC server responds to a trivial request"""
        self._connect_if_needed()
        try:
            self.server.version()
            return True
        except socket.error:
            return False

    def stop_server(self):
        self._connect_if_needed()
        self._execute_electrum_command(['daemon', 'stop'])

    def get_balance(self):
        """Return the amount we have in the wallet, confirmed by the blockchain"""
        self._connect_if_needed()

        return inexact_to_decimal(self.server.getbalance()['confirmed'])

    def get_receive_address(self):
        """Returns an unused address of this wallet, where we can receive BTC

        Note: if you use an imported keystore instead of a seeded wallet,
        then `getunusedaddress()` may return None.
        """
        self._connect_if_needed()

        address = self.server.getunusedaddress()
        if not address:
            raise ValueError('Error: can not get unused address!')

        return address

    @staticmethod
    def suggest_miner_fee():
        """Returns miner fee to use, for typical transaction

        We should use fee estimates from Electrum, but it has no API for this.
        """
        request = urllib.request.Request(
            'https://bitcoinfees.21.co/api/v1/fees/recommended',
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; CrOS i686 2268.111.0) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.57 Safari/536.11'
            }
        )
        response = urllib.request.urlopen(request)
        data = json.loads(response.read())

        #   The above is in Satoshis/B
        #   Multiply by 226 (typical bytes in a txn) -> Satoshis/txn
        #   Multiply by 0.00000001 (BTCs in a Sat) -> BTC/txn

        ten_min_fee_satoshi_per_byte = data['halfHourFee']
        ten_min_fee_satoshi_per_txn = ten_min_fee_satoshi_per_byte * 226
        fee = Decimal(ten_min_fee_satoshi_per_txn) * Decimal('1e-8')

        if fee > Decimal('0.001'):
            raise ValueError('Fee greater than 1 mBTC!')
        else:
            logger.warning('BTC Miner fee estimate: {}'.format(fee))

        return fee

    def transactions_since(self, since_unix_time):
        """Gets incoming transactions since specified time

        Lists all transactions of positive amount (which increased our balance)
        having the `blocktime` >= the given unix time.

        :param since_unix_time: integer or float, unix time
        :return transactions: List of transaction dictionaries
            Each dict has `amount`, `txid`, and `time` of each transaction
        """
        self._connect_if_needed()

        if not isinstance(since_unix_time, numbers.Real):
            raise ValueError('since_unix_time must be a number!')

        history = json.loads(self.server.history())['transactions']

        return self._process_history(history, since_unix_time)

    @classmethod
    def _process_history(cls, history, since_unix_time):
        """Process the transaction history data"""
        for tx in history:
            amount, currency = tx['value'].split(' ')

            if currency != 'BTC':
                raise ValueError('May not treat non-BTC currencies from PiggyBTC!')

            tx['value_decimal'] = Decimal(amount)

        recently_received = [
            tx for tx in history if
                (tx['timestamp'] >= since_unix_time) and
                (tx['confirmations'] >= 1) and
                (tx['value_decimal'] > 0)  # We received money (not sent, and not zero)
        ]

        # Only get the required fields, name them consistently, and cast value to Decimal
        recently_received = [
            {
                'txid': tx['txid'],
                'time': tx['timestamp'],
                'value': inexact_to_decimal(tx['value_decimal'])
            } for tx in recently_received
        ]

        return recently_received

    def perform_transaction(self, net_amount, miner_fee, target_address):
        """Send Bitcoins to target_address (total cost: net_amount + miner_fee)"""

        self._connect_if_needed()

        assert isinstance(net_amount, Decimal)
        assert isinstance(miner_fee, Decimal)
        self._validate_address(target_address)

        tx = self.server.payto(
            destination=str(target_address),
            amount=str(net_amount),
            fee=str(miner_fee),
            password=self.wallet_password
        )

        success, txid = self.server.broadcast(tx['hex'])

        # Signed TX: {u'hex': u'0100000001718276ce6c2298bf71352fa38fb9b4d3d40f49ec592d0dae640d9f4709e11a6a000000006b483045022100a1cbbd78b0f6f3c01bac6ea0590adbe2941b2be3d08820e1adb5b42777c4bd6202201c176a5f0a25c20f856aa91c09a7581d4d1057fa4e644c65ee34d9fd113291d6012103c64230ff95961bda955ae374e90cf4d9883432731a2df0389204162b7e6dc579feffffff0107003700000000001976a91490c235fba4b7ea93106c7439703779cba6db772e88ac00000000', u'complete': True, u'final': True}
        # Broadcast TX: [True, u'f0619d982344c12169e5fbf38f83b474be7df5a009351a6b1aeb4430566fa7ba']

        if success:
            logger.warning("Signed TX: {}".format(tx))
            logger.warning("Broadcast TX id: {}".format(txid))
            return txid
        else:
            raise BaseException("Transaction broadcast fail: {}".format(txid))

    def _validate_address(self, btc_address):
        """Raises an exception if address is invalid"""
        self.server.getaddressbalance(btc_address)
