# Command used by Ethereum Wallet for fast sync:
# /home/dan/.config/Ethereum Wallet/binaries/Geth/unpacked/geth --syncmode fast --cache 1024 --datadir /media/dan/Wilderness/Blockchains/eth/

import calendar
import datetime
import logging
import os
import pexpect
import web3

from decimal import Decimal
from pexpect import popen_spawn
from pyetherchain.pyetherchain import EtherChain
from web3 import Web3

from .processing import wait_for_success, check_port

logger = logging.getLogger('piggy_logs')

class PiggyETH:
    TXN_GAS_LIMIT = 21000

    def __init__(self,
                  wallet_bin_path,
                  datastore_path,
                  wallet_password,
                  ):
        """
        Manage a Parity wallet for Ethereum.

        The wallet key file must be in `datastore_path/keys/ethereum/`.
	Multiple "accounts" (wallet key files) are not supported - see the `accounts` property.

        :param wallet_bin_path: Path to Parity wallet executable
        :param datastore_path: Path to datastore directory (which includes wallet files and blockchain)
        :param wallet_password: Password to enter for decrypting the account
        """

        self.wallet_bin_path = wallet_bin_path
        self.datastore_path = datastore_path
        self.wallet_password = wallet_password

        self._server = None
        self._accounts = None
        self._block_timestamps = {}
        self.ec = EtherChain()

    @property
    def server(self):
        if self._server is None:
            ipc = Web3.IPCProvider(
                os.path.join(self.datastore_path, 'jsonrpc.ipc')
            )

            self._server = Web3(ipc)
        return self._server

    @property
    def accounts(self):
        if self._accounts is None:
            self._accounts = self.server.eth.accounts

            # We only handle 1 account (address) as of now.
            # In order to support multiple accounts you need to alter:
            # `get_receive_address`, `get_balance`, `transactions_since`, `perform_transaction`
            assert len(self.accounts) == 1
        return self._accounts

    def start_server(self):
        if self._rpc_loaded():
            return

        command = [
            self.wallet_bin_path,
            '-d', self.datastore_path,
            '--log-file', os.path.join(os.getcwd(), self.datastore_path, 'parity_log.txt'),
            '--no-ancient-blocks',
            '--no-ws',
            '--no-jsonrpc',
            '--ipc-apis=web3,eth,personal', # We need personal to actually perform a transaction
            '--warp-barrier', '5842205',
        ]

        logger.info("Starting ETH wallet: {}".format(' '.join(command)))
        popen_spawn.PopenSpawn(command)

        wait_for_success(self._rpc_loaded, 'ETH RPC')

    def stop_server(self):
        """Use pkill to kill the parity wallet."""
        p = pexpect.spawn('/usr/bin/pkill', ['-f', self.wallet_bin_path])
        p.wait()
        if p.status is not 0:
            raise ValueError('Error pkilling ETH:\n{}'.format(p.read()))

    def _rpc_loaded(self):
        """Attempt a connection to the RPC"""
        try:
            self.server.eth.getBlock(self.server.eth.blockNumber)
            return True
        except (web3.utils.threads.Timeout, ConnectionRefusedError, FileNotFoundError):
            return False

    def _from_wei(self, wei):
        """Convert wei to ether"""
        return self.server.fromWei(wei, 'ether')

    def get_receive_address(self):
        return self.accounts[0]

    def get_balance(self):
        wei = self.server.eth.getBalance(self.get_receive_address(), 'latest')
        return self._from_wei(wei)

    def suggest_miner_fee(self):
        gas_needed = self.server.eth.estimateGas(
            {
                'from': self.get_receive_address(),
                'to': self.get_receive_address(),
                'value': 1
            }
        )

        # Get the gas price in the latest unconfirmed block
        gas_price = self.server.eth.gasPrice

        return self._from_wei(gas_price * gas_needed)

    def transactions_since(self, since_unix_time, only_look_at=10):
        """
        Gets transactions since specified unix timestamp.
        We use Etherchain.org's server, because it's impractical to create an index for ETH
            transactions ourselves.
        Caveats:
            - this has privacy implications (you reveal your ETH address to Etherchain)
            - only looks at last `only_look_at` transactions to avoid abusing the server
            - only shows 5 decimals after the point (minimum value 0.00001 ETH)
        """


        acc = self.ec.account(self.accounts[0])
        raw_txns = acc.transactions(length=only_look_at, direction='in')
        return self._process_history(raw_txns, since_unix_time, self._timestamp_getter)

    @classmethod
    def _process_history(cls, raw_txns, since_unix_time, timestamp_getter):
        def to_eth(value_string):
            value, unit = value_string.split()
            if unit != 'ETH':
                raise ValueError('Txn not valued in ETH: {}'.format(value_string))
            return Decimal(value)

        txn_list = [
            {
                'txid': tx['parenthash'],
                'time': timestamp_getter(int(tx['blocknumber'])),
                'value': to_eth(tx['value'])
            }
            for tx in raw_txns['data'] if
                tx['direction'].lower() == 'in' and
                tx['value'] != '0 ETH'
        ]

        return [tx for tx in txn_list if tx['value'] > 0 and tx['time'] >= since_unix_time]

    def _timestamp_getter(self, blocknumber):
        if blocknumber not in self._block_timestamps:
            # Try the local Eth server
            logger.debug('Retrieving block #{}...'.format(blocknumber))
            block = self.server.eth.getBlock(blocknumber, full_transactions=False)
            if block:
                self._block_timestamps[blocknumber] = block.timestamp
            else:
                # Fallback to Etherchain.org
                block = self.ec.api.get_block(3865982)
                ts = self._parse_utc_time(block['time'])
                self._block_timestamps[blocknumber] = ts

        return self._block_timestamps[blocknumber]

    @classmethod
    def _parse_utc_time(cls, timestr):
        dt = datetime.datetime.strptime(
                timestr, "%Y-%m-%dT%H:%M:%S.%fZ"
        )
        return calendar.timegm(dt.timetuple())

    def perform_transaction(self, net_amount, miner_fee, target_address):
        """
        Send Ether to target_address (total cost: net_amount + miner_fee)
        """
        assert isinstance(net_amount, Decimal)
        assert isinstance(miner_fee, Decimal)

        net_amount_wei = self.server.toWei(net_amount, 'ether')
        if net_amount_wei != net_amount*Decimal('1e18'):
            raise ValueError('net_amount is not an integer multiple of wei.')

        gas_price_wei = self._get_gas_price(miner_fee)

        txid = self.server.personal.sendTransaction(
            {
                'to': target_address,
                'gas': self.TXN_GAS_LIMIT,
                'gasPrice': gas_price_wei,
                'value': net_amount_wei,
            },
            self.wallet_password
        )

        return txid

    def _get_gas_price(self, eth_to_spend):
        assert isinstance(eth_to_spend, Decimal)

        wei_to_spend = self.server.toWei(eth_to_spend, 'ether');
        gas_price_wei = wei_to_spend/self.TXN_GAS_LIMIT
        if gas_price_wei != int(gas_price_wei):
            raise ValueError('Transaction fee is not an integer multiple of the gas price.')

        return int(gas_price_wei)
