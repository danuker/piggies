import logging

from decimal import Decimal
from time import sleep

logger = logging.getLogger('piggy_logs')


def inexact_to_decimal(inexact_float):
    """
    Transforms a float to decimal, through its __str__() method.

    >>> inexact_to_decimal(3.14)
    Decimal('3.14')

    Avoids doing the following:

    >>> Decimal(3.14)
    Decimal('3.140000000000000124344978758017532527446746826171875')

    """

    return Decimal(str(inexact_float))


def wait_for_success(success_check, description, max_seconds=120):
    """
    Wait until calling `success_check` returns a truthy value.

    :param success_check: Callable returning truthy on success, false otherwise
    :param description: What the task is about (to log)
    :param max_seconds: Maximum amount of time to wait, before giving up
    """
    logger.info('Waiting for {} (at most {} seconds)'.format(description, max_seconds))
    for wait in range(max_seconds):
        if success_check():
            return
        else:
            logger.info('Waited for {} ({} seconds so far)'.format(description, wait))
            sleep(1)

    if not success_check():
        raise ValueError('{} failed after {} seconds'.format(description, max_seconds))


def check_port(port_num, name='port'):
    """Check that the port is a valid number. You'd be surprised."""

    if not isinstance(port_num, int):
        raise ValueError('Error! {} ({}) is not an integer!'.format(name, port_num))
    elif port_num > 65535:
        raise ValueError('Error! {} number too large ({}})'.format(name, port_num))
    else:
        return port_num
