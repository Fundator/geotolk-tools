"""
Loader for .PRV files.
"""
import re
import pandas as pd
import numpy as np
from uuid import uuid4

MIN_DATA_LENGTH = 1
ROW_PATTERN = re.compile(
    r"^(\d+) +(\S+) +(\S+) +(\S+) +(\S+) +(\S+) +(\S+) +(\S+) +(\S+) +(\S+) +(\S+) +(\S+) +([HV]*) +(.*)")
GUID_PATTERN = re.compile(r"(?<=GUID )(\S+)")

SYMBOL_LABELS_NEG = [
    'Leire',
    'Fyllemasse',
    'Grus',
    'Matjord',
    'Berg',
    'Sand',
    'Skjell',
    'Silt',
    'Stein & blokk',
    'Morene',
    'Torv',
    'Gytje, dy',
    'Trerester'
    'Kvikkleire'
]
SYMBOL_LABELS_POS = [
    np.nan,
    "Leire",
    "Silt",
    "Sand",
    "Grus",
    "Stein",
    "Fyllemasse",
    "Matjord",
    "Trerester",
    "Skjell",
    "Kvikkleire"
]


def prv_to_df(lines):
    """
    Convert the list of lines to a dataframe
    :param lines: Input lines
    :type lines: list of str
    :return: Dataframe with loded sample-data
    :rtype: pd.DataFrame
    """
    rows = []
    for line in lines:
        matches = ROW_PATTERN.findall(line)
        if matches:
            matches = matches[0]
            row = {
                "prove": matches[0],
                "symbol": matches[1],
                "prove_label": label_from_symbol(matches[1], float(matches[6]), float(matches[7])),
                "depth": float(matches[2]),
                "w": float(matches[3]),
                "wp": float(matches[4]),
                "wl": float(matches[5]),
                "suu": float(matches[6]),
                "suo": float(matches[7]),
                "bruddef": float(matches[8]),
                "gamma": float(matches[9]),
                "glodetap": float(matches[10]),
                "jordard": str(matches[11]),
                "position": matches[12] or np.nan,
                "comment": matches[13] or np.nan,
            }
            rows.append(row)
    if len(rows) < MIN_DATA_LENGTH:
        return None

    df = pd.DataFrame(rows)
    return df


def label_from_symbol(symbol, suu, suo):
    """
    Convert Geosuite's 'symbol' column to a list of labels.

    :param symbol: Symbol
    :type symbol: int | str
    :return: Label list
    :rtype: list of str | np.nan
    """

    symbol = int(symbol)
    if symbol < 0:
        bin_str = str(bin(abs(symbol)))[2:].zfill(13)
        label = [SYMBOL_LABELS_NEG[pos] for pos, bit in enumerate(reversed(bin_str)) if bit == "1"]
    elif symbol > 0:
        label = [SYMBOL_LABELS_POS[int(i)] for i in str(symbol)]
    elif suo != 0 and suu != 0 and suo < 2 and suu/suo >= 15:
        label = ["Kvikkleire"]
    else:
        label = np.nan
    return label or np.nan


def process_prv(lines):
    """
    Process a list of lines from a .PRV file.

    :param lines: Input lines
    :type lines: list of str
    :return: Dict with data from .PRV file.
    :rtype: dict
    """
    df = prv_to_df(lines)
    if df is None:
        return None

    guid_match = GUID_PATTERN.findall(lines[0])
    if not guid_match:
        guid = uuid4()
    else:
        guid = guid_match[0]

    file_dict = {
        "type": "prv",
        "xyz": 3 * [np.nan],
        "guid": guid,
        "data": df
    }
    return file_dict
