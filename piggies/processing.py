from decimal import Decimal


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
