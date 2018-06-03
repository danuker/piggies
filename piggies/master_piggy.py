import logging
from decimal import Decimal

import pandas as pd

from piggy_btc import PiggyBTC
#from piggy_xmr import PiggyXMR

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
#            'XMR': PiggyXMR not yet supported
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
        balances = {}

        for p in self.currencies:
            balances[p] = self.piggies[p].get_balance()

        return pd.Series(balances)

    def get_receive_address(self, currency):
        return self.piggies[currency].get_receive_address()

    def suggest_miner_fee(self, currency):
        return self.piggies[currency].suggest_miner_fee()

    def transactions_since(self, currency, earliest_possible_received=0):
        earliest_possible_received = float(earliest_possible_received)
        return self.piggies[currency].transactions_since(earliest_possible_received)

    def perform_transaction(
            self,
            currency,
            amount,
            miner_fee,
            target_address
    ):
        assert isinstance(amount, Decimal)
        assert isinstance(miner_fee, Decimal)

        # TODO: Add sanity check against too large miner fee

        raise ValueError(
            'I am not allowed to perform transactions yet, but I would send {}+{} {} to {}!'.format(
                amount, miner_fee, currency, target_address
            )
        )

        self.piggies[currency].perform_transaction(amount, miner_fee, target_address)
