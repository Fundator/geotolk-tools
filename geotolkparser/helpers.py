"""
Misc. helpers for io functions
"""

import re
import pandas as pd


GUID_PATTERN = re.compile(r".*GUID (.*)$")
DATE_PATTERN = re.compile(r".*([0-9]{2})\.([0-9]{2})\.([0-9]{4})")


def match_pattern_in_block(pattern, block):
    """
    Find the first match for 'pattern' in 'block'

    :param pattern: Regex pattern to match
    :type pattern: re.Pattern
    :param block: Strings to match pattern against
    :type block: list of str
    :return: Matches or None if no matches were found
    :rtype: tuple of str | None
    """
    for line in block:
        matches = pattern.findall(line)
        if matches:
            return matches[0]


def find_blocks(lines):
    """
    Split the given list of strings into blocks. A block is defined as all lines contained between lines containing only
    asterisks (*). E.g.:
    *
    <block 0, line 0>
    <block 0, line 1>
    *
    <block 1, line 0>
    *

    :param lines: Input list of lines
    :type lines: list of str
    :return: List of blocks
    :rtype: list of list of str
    """
    blocks, current_block = [], []
    for line in lines:
        if line == "*\n":
            blocks.append(current_block)
            current_block = []
        else:
            current_block.append(line)
    if current_block:
        blocks.append(current_block)
    return blocks


def get_xyz(block):
    """
    Get (x,y,z) coordinates from an xyz-block

    :param block:
    :type block:
    :return: x,y,z coordinates
    :rtype: tuple of float
    """
    x = float(block[0])
    y = float(block[1])
    z = float(block[2])
    return x, y, z


def merge_dfs(dfs, reset_index=True, sort_by=["id", "depth"]):
    """
    Combine a list of dataframes into a single dataframe with fixed indices and sorted rows.

    :param dfs: Dataframes to concatenate
    :type dfs: list of pd.DataFrame
    :param reset_index: Reset the index of the concatenated DataFrame?
    :type reset_index: bool
    :param sort_by: parameter passed to df.sort_values
    :type sort_by: str | list of str
    :return: Concatenated dataframe
    :rtype: pd.DataFrame
    """
    df = pd.concat(dfs, sort=False)
    if reset_index:
        df.reset_index(drop=True, inplace=True)
    df.sort_values(by=sort_by, inplace=True)
    return df
