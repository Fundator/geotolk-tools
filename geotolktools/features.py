import pandas as pd
import numpy as np
from scipy.stats import trim_mean, median_absolute_deviation
import multiprocessing
from typing import Callable

_DEPTH_COLNAME = "dybde"
_PRESSURE_COLNAME = "trykk"
_FLUSH_COLNAME = "spyle"
_ID_COLNAME = "borehole_id"
_FEATURES = [_DEPTH_COLNAME, _PRESSURE_COLNAME, "sek10", "bortid", "smoothed_diff_pressure", "pressure_std", _FLUSH_COLNAME, "spyling", "okt_rotasjon", "slag"]

def _apply_parallel(df_grouped: pd.core.groupby.generic.DataFrameGroupBy, func: Callable) -> pd.DataFrame:
    """
    Pandas groupby.apply in parallel.
    :param df_grouped: Grouped dataframe (result of df.groupby(...))
    :type df_grouped: pd.GroupBy
    :param func: function to apply to grouped dataframes
    :type func: function
    :return: Resulting dataframe
    :rtype: pd.DataFrame
    """
    n_cores = multiprocessing.cpu_count()
    with multiprocessing.Pool(np.maximum(1, n_cores-1)) as p:
        ret_list = p.map(func, [group for name, group in df_grouped])
    return pd.concat(ret_list)


def _bortid(df: pd.DataFrame) -> pd.Series:
    """
    Compute "bortid" for the given total sounding
    :param df: Input total sounding
    :type df: pd.DataFrame
    :return: Bortid
    :rtype: pd.Series
    """
    return (df["sek10"] / 10) / df[_DEPTH_COLNAME].diff().fillna(method="bfill")


def _get_smoothed_diff_pressure_std(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute the smoothed differentiated pressure, and its rolling standard deviation, which can be used in the synthetic
    labeling process.
    :param df: Input total sounding
    :type df: pd.DataFrame
    :return: Dataframe containing diff'd, smoothed, and std'd pressure
    :rtype: pd.DataFrame
    """
    df["bortid"] = _bortid(df)
    diff_pressure = df[_PRESSURE_COLNAME].diff().bfill()
    window_length = 20
    smoother = lambda x: trim_mean(x, proportiontocut=0.3)

    df["smoothed_diff_pressure"] = diff_pressure.rolling(window_length, center=True, min_periods=1).apply(smoother, raw=True)
    df["pressure_std"] = df["smoothed_diff_pressure"].rolling(2 * window_length, center=True, min_periods=1).std()
    return df

def _extract_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract temporal features from a total sounding dataframe. The features are rolling median/std for continuous
    features, and rolling sums for binary features.
    :param df: Input total sounding
    :type df: pd.DataFrame
    :return: Extracted features
    :rtype: pd.DataFrame
    """
    features = pd.DataFrame(index=df.index)
    window_lengths = [10, 50, 100]
    cont_features = [_PRESSURE_COLNAME, "sek10", _FLUSH_COLNAME, "bortid"]
    cat_features = ["okt_rotasjon", "spyling", "slag", "pumping"]

    for l in window_lengths:
        for col in cont_features:
            features[f"{col}_rolling_median_{l}"] = df[col].rolling(l, center=True, min_periods=1).median()
            features[f"{col}_rolling_median_absolute_deviation_{l}"] = df[col].rolling(l, center=True, min_periods=1).apply(lambda row: median_absolute_deviation(row))
            features[f"{col}_rolling_sum_{l}"] = df[col].rolling(l, center=True, min_periods=1).apply(lambda row: sum(row))
        for col in cat_features:
            features[f"{col}_rolling_sum_{l}"] = df[col].rolling(l, center=True, min_periods=1).sum()

    features["pressure_diff"] = df[_PRESSURE_COLNAME].rolling(3, center=True, min_periods=1).median().diff().bfill()

    return features


def extract_features_tot(df: pd.DataFrame, multiprocessing: bool=True) -> pd.DataFrame:
    """
    Extract features for the given preprocessed total sounding
    :param df: Input preprocessed total sounding
    :type df: pd.DataFrame
    :return: Extracted features,
    :rtype: df: pd.DataFrame
    """


    if multiprocessing:
        df = _apply_parallel(df.groupby(_ID_COLNAME, group_keys=False), _get_smoothed_diff_pressure_std)
        rolling_features = _apply_parallel(df.groupby(_ID_COLNAME, group_keys=False), _extract_rolling_features)
    else:
        df = df.groupby(_ID_COLNAME).apply(_get_smoothed_diff_pressure_std)
        rolling_features = df.groupby(_ID_COLNAME).apply(_extract_rolling_features)

    features = df
    features = pd.concat([features, rolling_features], axis=1)
    features [_ID_COLNAME] = df[_ID_COLNAME]
    return features