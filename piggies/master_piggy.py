import logging
from decimal import Decimal

from .piggy_btc import PiggyBTC
from .piggy_xmr import PiggyXMR
from .piggy_eth import PiggyETH

logger = logging.getLogger('piggy_logs')

class MasterPiggy:
    """
    One Piggy to rule them all!
    This class is used to manage money in all the other piggies.

    :param piggy_settings: Dictionary to specify piggy options. Example:
        `{'BTC': {'wallet_path': '/path/btcwallet/', [...]}, [...]}
    """

    supported = {
            'BTC': PiggyBTC,
            'XMR': PiggyXMR,
            'ETH': PiggyETH,
    }

    def __init__(self, piggy_settings):
        self.currencies = piggy_settings.keys()
        self._check_currency_support()

        # Initialize the requested piggies
        self.piggies = {
            currency: self.supported[currency](
                **(piggy_settings[currency])
            )
            for currency in self.currencies
        }

    def _check_currency_support(self):
        """Check that all required piggies have been initialized"""

        required = set(self.currencies)
        supported = set(self.supported.keys())
        missing = required - supported

        if missing:
            raise ValueError(
                'MasterPiggy: Missing support for configured currencies: {}'.format(missing)
            )

    def start_servers(self):
        for p in self.currencies:
            logger.info("Starting RPC server for {}...".format(p))
            self.piggies[p].start_server()

    def stop_servers(self):
        for p in self.currencies:
            logger.info("Stopping RPC server for {}...".format(p))
            self.piggies[p].stop_server()

    def get_balances(self):
        return {p: self.piggies[p].get_balance() for p in self.currencies}

    def get_receive_address(self, currency):
        return self.piggies[currency].get_receive_address()

    def suggest_miner_fee(self, currency):
        return self.piggies[currency].suggest_miner_fee()

    def transactions_since(self, currency, earliest_possible_received=0):
        return self.piggies[currency].transactions_since(earliest_possible_received)

    def perform_transaction(
            self,
            currency,
            net_amount,
            miner_fee,
            target_address
    ):
        assert isinstance(net_amount, Decimal)
        assert isinstance(miner_fee, Decimal)

        self.piggies[currency].perform_transaction(net_amount, miner_fee, target_address)
