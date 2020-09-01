"""
Loader for .SND files.
"""
import re
import numpy as np
import pandas as pd
from datetime import datetime
import logging

from geotolkparser.helpers import find_blocks, get_xyz, match_pattern_in_block, DATE_PATTERN, GUID_PATTERN

logger = logging.getLogger(__name__)
VERBOSE = True
MIN_DATA_LENGTH = 10
TOT_ROW_PATTERN = re.compile(r" +(\d+\.\d*) +(-?\d+) +(-?\d+) +(\d+) *(.*) *")
CPT_ROW_PATTERN = re.compile(r" +(\d+\.\d*) +(\d+) +(-?\d+) +(\d+) *(.*) +(\d+) +(\d+\.\d*) +(\d+\.\d*) +(\d+\.\d*) *")
STATUS_CODE_PATTERN = re.compile("^([A-Z])([1-9])$")
GROUND_CODE_PATTERN = re.compile("^([1-9][0-9])$")


def process_snd(lines):
    """
    Process a list of lines from an .SND file.

    :param lines: Input lines
    :type lines: list of str
    :return: Dict containing data from lines
    :rtype: dict
    """
    blocks = find_blocks(lines)
    if len(blocks) < 4:
        raise RuntimeError("Did not find the expected amount of blocks")
        return None

    file_dict = {
        "type": "snd",
        "xyz": get_xyz(blocks[0]),
        "guid": match_pattern_in_block(GUID_PATTERN, blocks[2]),
        "blocks": []
    }
    data_blocks = blocks[3:]
    for block in data_blocks:
        proc = process_data_block(block)
        if proc is not None:
            file_dict["blocks"].append(proc)

    return file_dict


def process_data_block(block):
    """
    Process a data-block from the .SND file. The block can represent a total sounding or a CPT.

    :param block: Input block
    :type block: list of str
    :return: Dict with data from block.
    :rtype: dict
    """
    metadata = block[:2]
    data = block[2:]

    if len(data) < MIN_DATA_LENGTH:
        raise RuntimeError(f"Data contains {len(data)} data points which is less than the minimum amount of data "
                           f"points ({MIN_DATA_LENGTH}).")
        return None

    # Determine block type and metadata
    block_type = get_block_type(metadata, data)
    date, block_guid = get_date_and_guid(metadata)
    # Process block according to type
    if block_type == "tot":
        proc = process_tot(block)
    elif block_type == "cpt":
        proc = process_cpt(block)
    else:
        raise ValueError("Invalid block type: {}".format(block_type))

    if proc is None:
        return None

    block_dict = {
        "type": block_type,
        "date": date,
        "guid": block_guid,
        "data": proc
    }
    return block_dict


def process_cpt(block):
    """
    Get the data from a CPT block

    :param block: Input CPT block.
    :type block: list of str
    :return: Dataframe with data from CPT block
    :rtype: pd.DataFrame
    """
    rows = []
    for line in block:
        matches = CPT_ROW_PATTERN.findall(line)
        if matches:
            if len(matches[0]) >= 9:
                rows.append(get_values_from_data_row_cpt(matches[0]))
            else:
                logger.error("Less than  9 values found")
    if not rows:
        return None
    return pd.DataFrame(rows)


def get_values_from_data_row_cpt(m):
    """
    Get the values from a CPT row regex-match.
    :param m: Regex match
    :type m: tuple of str
    :return: Dict with data from row
    :rtype: dict
    """
    return {
        "depth": float(m[0]),
        "spisstrykk": float(m[1]),
        "poretrykk": float(m[2]),
        "friksjon": float(m[3]),
        "comment": m[4],
        "helning": float(m[7]),
        "temperatur": float(m[8])
    }


def process_tot(block):
    """
    Get the data from a total sounding block

    :param block: Input total sounding block.
    :type block: list of str
    :return: Dataframe with data from total sounding block
    :rtype: pd.DataFrame
    """
    rows = []
    for line in block:
        matches = TOT_ROW_PATTERN.findall(line)
        if matches:
            if len(matches[0]) >= 4:
                rows.append(get_values_from_data_row_tot(matches[0]))
            else:
                logger.error("Less than 4 values found")
    if not rows:
        return None

    df = pd.DataFrame(rows)
    fill_cols = ["okt_rotasjon", "spyling", "slag"]
    df[fill_cols] = df[fill_cols].ffill().fillna(0)
    return df


def get_values_from_data_row_tot(match):
    """
    Get the values from a regex-match of a row in a total sounding.

    :param match: Regex match
    :type match: tuple of str
    :return: Dict with data from row
    :rtype: dict
    """
    depth, pressure, flush, sek10, comments = match
    Y = R = S = np.nan
    notes = []

    if len(comments) >= 0:
        list_of_comments = comments.split()
        for element in list_of_comments:
            if STATUS_CODE_PATTERN.match(element):
                operation, mode = STATUS_CODE_PATTERN.findall(element)[0]
                if operation == "Y":
                    Y = np.abs(int(mode) - 2)
                elif operation == "R":
                    R = np.abs(int(mode) - 2)
                elif operation == "S":
                    S = np.abs(int(mode) - 2)
                elif operation == "D":
                    S = np.abs(int(mode) - 2)
                    Y = np.abs(int(mode) - 2)
            if GROUND_CODE_PATTERN.match(element):
                note = int(GROUND_CODE_PATTERN.findall(element)[0])
                if 70 <= note <= 79:
                    if note == 70:
                        R = 1
                    elif note == 71:
                        R = 0
                    elif note == 72:
                        Y = 1
                    elif note == 73:
                        Y = 0
                    elif note == 74:
                        S = 1
                    elif note == 75:
                        S = 0
                    elif note == 76:
                        S = 1
                        Y = 1
                    elif note == 77:
                        S = 0
                        Y = 0
                else:
                    notes.append(note)

    if len(notes) == 0:
        notes = np.nan

    return {"depth": float(depth), "pressure": float(pressure), "sek10": float(sek10), "spyletrykk": float(flush),
            "spyling": Y, "okt_rotasjon": R, "slag": S, "merknad": notes}


def get_block_type(metadata, data):
    """
    Determine the block type of the given data block. Type can be either 'tot' (total sounding) or 'cpt'.

    :param metadata: Metadata block
    :type metadata: list of str
    :param data: Data block
    :type data: list of str
    :return: Block type
    :rtype: str
    """
    for row in metadata:
        if "tot" in row.lower():
            return "tot"
        if "cpt" in row.lower():
            return "cpt"

    # Hacky check for TOT vs. CPT
    if (np.array([len(d) for d in data]) > 75).any():
        return "cpt"
    return "tot"


def get_date_and_guid(metadata):
    """
    Get the date and GUID from the metadata of a data block.
    :param metadata: Metadata
    :type metadata: list of str
    :return: date and guid
    :rtype: datetime.datetime, str
    """
    date = match_pattern_in_block(DATE_PATTERN, metadata)
    if date is not None:
        day, month, year = date
        try:
            date = datetime(year=int(year), month=int(month), day=int(day))
        except ValueError as e:
            logger.error(e)
            date = np.nan
    guid = match_pattern_in_block(GUID_PATTERN, metadata)
    return date, guid
