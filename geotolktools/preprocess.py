import multiprocessing
import pandas as pd
import numpy as np
from scipy.stats import trim_mean, median_absolute_deviation
from scipy.interpolate import interp1d
import scipy.special as sc
import warnings
from typing import List, Tuple
from .mappings import VALID_RANGES_TOT

warnings.simplefilter("ignore", RuntimeWarning)

_INDICATOR_COLUMNS = ["okt_rotasjon", "spyling", "slag", "pumping"]
_ID_COL = "borehole_id"
_LABEL_COL = "comment_label"
_CATEGORICAL_COLS = {"okt_rotasjon", "spyling", "slag", "pumping", "comment_label"}
_FLOAT_COLS = {"trykk", "spyle", "sek10"}
_MIN_ROWS_TOT = 5
_MAX_GAP = 2.5

def _standardize_depth(df: pd.DataFrame, float_cols: set=_FLOAT_COLS, categorical_cols: set=_CATEGORICAL_COLS,  depth_delta: float=0.04, depth_colname: str="dybde", comment_colname: str="kommentar") -> pd.DataFrame:
    # Sjekk om dybden allerede er korrekt
    if (df[depth_colname].diff().dropna() == depth_delta).all():
        return df

    # Lag ny kolonne med korrekt intervall
    out = pd.DataFrame(columns=df.columns)
    new_depth = np.arange(df[depth_colname].min(), df[depth_colname].max() + depth_delta, depth_delta)

    if len(new_depth) <= 1: 
        raise ValueError("File only contains one depth, can't standardize depth")
    assert np.allclose(np.diff(new_depth), depth_delta, atol=1E-6)
    out.loc[:, depth_colname] = new_depth

    _interpolate(depth_colname, float_cols, out, df, "linear")

    _interpolate(depth_colname, categorical_cols, out, df, "nearest")

    # Do not extrapolate last row
    max_depth = out.iloc[-1][depth_colname]
    idx = out.iloc[-1].name
    out.iloc[idx, :] = df.iloc[-1].copy()
    out.loc[idx, depth_colname] = max_depth
    """
    if comment_colname in df.columns:
        remarks = df[[depth_colname, comment_colname]].dropna(subset=[comment_colname], axis=0)
        if not remarks.empty:
            inds = np.searchsorted(new_depth, remarks[depth_colname])
            inds[inds == out.shape[0]] = -1
            out.loc[inds, comment_colname] = remarks[comment_colname].values

    """
    constant_cols = list(set(df.columns) - (float_cols | categorical_cols | {depth_colname, comment_colname}))
    for col in constant_cols:
        out.loc[:, col] = df[col].iloc[0]

    return out


def _interpolate(x_col, y_cols, new, old, kind):
    """
    Helper function for interpolation.
    """
    interp_cols = list(set(old.columns) & y_cols)
    interpolated = interp1d(old[x_col], old[interp_cols].values, kind=kind, axis=0, bounds_error=False,
                            fill_value="extrapolate")(new[x_col])
    new.loc[:, interp_cols] = interpolated


def _has_less_than_n_rows(df: pd.DataFrame, nrows: int) -> bool:
    return df.shape[0] < nrows

def _fill_indicator_cols(df: pd.DataFrame, indicator_columns: List[str]) -> pd.DataFrame:
    return df[indicator_columns].ffill().fillna(0)        


def _fill_label_col(df: pd.DataFrame, label_column: str) -> pd.DataFrame:
        return df[label_column].ffill()    


def _correct_values(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    _df = df.copy()
    for column_name in mapping:
        if column_name not in _df.columns:
            raise KeyError(f"Coulumn {column_name} not found in data")
        _df[column_name] = np.clip(_df[column_name], mapping[column_name]["min"], mapping[column_name]["max"])
    return _df


def _remove_huge_depth_gaps(df: pd.DataFrame, threshold: float) -> Tuple[pd.DataFrame, List[dict]]:
    _df = df.copy()
    # get difference between rows
    error = ""
    diff = _df["dybde"].diff().dropna()
    above_thresh = diff[np.abs(diff) > threshold]
    if len(above_thresh.index) != 0:

        error = f"Detected gap of {above_thresh.max()} above threshold of {threshold}. "
        gap_idx = above_thresh.index[0]
        start_idx = _df.iloc[0].name
        stop_idx = _df.iloc[-1].name

        n_above = gap_idx - start_idx
        n_below = stop_idx - gap_idx

        # If the amount of rows above gap is more than below, select from the start of the file to the gap
        if n_above > n_below:
            error += f"Removing the last {n_below +1} rows after gap"
            _df =  _df.iloc[start_idx:gap_idx]
        # Otherwise, return from the gap to the end of the file
        else:
            error += f"Removing the first {n_above +1} rows before gap"
            _df = _df.iloc[gap_idx:stop_idx]
    return _df, error


def preprocess(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[dict]]:
    """Preprocesses a total sounding dataframe. df may be a single sounding file or a collection of many tot-files

    Args:
        df (pd.DataFrame): Dataframe with total soundings

    Returns:
        Tuple[pd.DataFrame, List[dict]]: (<processed_dataframe>, List of errors occured during preprocessing)
    """
    _df = df.copy()
    errors = []
    groups = []
    # Group by id-column
    for name, group in _df.groupby(_ID_COL):
        # Check if it has less than n_rows:
        if not _has_less_than_n_rows(group, _MIN_ROWS_TOT):
            # Remove huge gaps
            group, error = _remove_huge_depth_gaps(group, _MAX_GAP)
            if error:
                errors.append({"filename": name, "error": error})
            # Fill indicator_columns
            group[_INDICATOR_COLUMNS] = _fill_indicator_cols(group, _INDICATOR_COLUMNS)
            # Fill label column
            group[_LABEL_COL] = _fill_label_col(group, _LABEL_COL)
            # Clip values
            group = _correct_values(group, VALID_RANGES_TOT)

            # Standardize depth
            try:
                groups.append(_standardize_depth(group))
            except ValueError as e:
                errors.append({"filename": name, "error": e})
        else:
            errors.append({"filename": name, "error": f"Skipped as it has less than {_MIN_ROWS_TOT} rows"})
    
    out = pd.concat(groups)
    out.reset_index(inplace=True, drop=True)
    return out, errors
