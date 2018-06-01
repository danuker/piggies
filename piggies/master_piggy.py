import logging
from decimal import Decimal

import pandas as pd

from lib.utils import assert_type, config_load
from piggies.piggy_btc import PiggyBTC

logger = logging.getLogger('sys_trader_logger')

class MasterPiggy:
    """
    One Piggy to rule them all!
    This class is used to manage money in all the other piggies.

    :param config_file: Path to YML file, or dict with options
    """

    def __init__(self, config_file):
        self.piggies = {
            'BTC': PiggyBTC(config_file)
        }

        self.config = config_load(config_file)
        self._check_currency_support()

    def _check_currency_support(self):
        required = set(self.config['base_currencies'] + [self.config['counter_currency']])
        supported = set(self.piggies.keys())
        missing = required - supported

        if missing:
            raise ValueError(
                'MasterPiggy: Missing support for configured currencies: {}'.format(missing)
            )

    def start_servers(self):
        for p in self.piggies:
            logger.info("Starting RPC server for {}...".format(p))
            self.piggies[p].start_server()

    def stop_servers(self):
        for p in self.piggies:
            logger.info("Stopping RPC server for {}...".format(p))
            self.piggies[p].stop_server()

    def get_balances(self):
        balances = {}

        for p in self.piggies:
            balances[p] = self.piggies[p].get_balance()

        return pd.Series(balances)

    def get_receive_address(self, currency):
        return self.piggies[currency].get_receive_address()

    def suggest_miner_fee(self, currency):
        return self.piggies[currency].suggest_miner_fee()

    def transactions_since(self, currency, earliest_possible_received):
        earliest_possible_received = float(earliest_possible_received)
        return self.piggies[currency].transactions_since(earliest_possible_received)

    def perform_transaction(
            self,
            currency,
            amount,
            miner_fee,
            target_address
    ):
        assert_type(amount, Decimal)
        assert_type(miner_fee, Decimal)

        # TODO: Add sanity check against too large miner fee

        raise ValueError(
            'I am not allowed to perform transactions yet, but I would send {}+{} {} to {}!'.format(
                amount, miner_fee, currency, target_address
            )
        )

        self.piggies[currency].perform_transaction(amount, miner_fee, target_address)


if __name__ == '__main__':
    master = MasterPiggy('config.yml')
    master.start_servers()
    logger.warning("get_balances:\n{}\n".format(master.get_balances()))
    logger.warning("get_receive_address:\n{}\n".format(master.get_receive_address('BTC')))
    logger.warning("suggest_miner_fee:\n{}\n".format(master.suggest_miner_fee('BTC')))
    logger.warning("transactions_since:\n{}\n".format(master.transactions_since('BTC', 0)))
    master.stop_servers()
