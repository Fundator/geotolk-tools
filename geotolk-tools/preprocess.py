import multiprocessing
import pandas as pd
import numpy as np
from scipy.stats import trim_mean, median_absolute_deviation
from scipy.interpolate import interp1d

def bortid(df: pd.DataFrame) -> pd.Series:
    """
    Compute "bortid" for the given total sounding
    :param df: Input total sounding
    :type df: pd.DataFrame
    :return: Bortid
    :rtype: pd.Series
    """
    return (df["sek10"] / 10) / df["depth"].diff().fillna(method="bfill")


def standardize_depth(df: pd.DataFrame, depth_delta: float=0.04) -> pd.DataFrame:
    """e the values of 'df' so that the depth-axis has the specified resolution.

    :param df:
    InterpolatInput total sounding
    :type df: pd.DataFrame
    :param depth_delta: New depth-resolution (in meters)
    :type depth_delta: float
    :return: Interpolated total sounding
    :rtype: pd.DataFrame.
    """
    if (df["depth"].diff().dropna() == depth_delta).all():
        return df

    out = pd.DataFrame(columns=df.columns)
    new_depth = np.arange(df["depth"].min(), df["depth"].max() + depth_delta, depth_delta)

    assert len(new_depth) > 1
    assert np.allclose(np.diff(new_depth), depth_delta, atol=1E-6)
    out.loc[:, "depth"] = new_depth

    float_cols = {"pressure", "sek10", "spyletrykk", "bortid"}
    _interpolate("depth", float_cols, out, df, "linear")

    categorical_cols = {"spyling", "okt_rotasjon", "slag", "label"}
    _interpolate("depth", categorical_cols, out, df, "nearest")

    if "merknad" in df.columns:
        remarks = df[["depth", "merknad"]].dropna(subset=["merknad"], axis=0)
        if not remarks.empty:
            inds = np.searchsorted(new_depth, remarks["depth"])
            inds[inds == out.shape[0]] = -1
            out.loc[inds, "merknad"] = remarks["merknad"].values

    constant_cols = list(set(df.columns) - (float_cols | categorical_cols | {"depth", "merknad"}))
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


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute the smoothed differentiated pressure, and its rolling standard deviation, which can be used in the synthetic
    labeling process.

    :param df: Input total sounding
    :type df: pd.DataFrame
    :return: Dataframe containing diff'd, smoothed, and std'd pressure
    :rtype: pd.DataFrame
    """
    df["bortid"] = bortid(df)
    diff_pressure = df["pressure"].diff().bfill()
    window_length = 20
    smoother = lambda x: trim_mean(x, proportiontocut=0.3)

    df["smoothed_diff_pressure"] = diff_pressure.rolling(window_length, center=True, min_periods=1).apply(smoother, raw=True)
    df["pressure_std"] = df["smoothed_diff_pressure"].rolling(2 * window_length, center=True, min_periods=1).std()
    return df


def apply_parallel(df_grouped, func):
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


def preprocess_total_sounding(df: pd.DataFrame, multiprocessing: bool=True) -> pd.DataFrame:
    """Applies preprocessing functions to the data

    Args:
        df (pd.DataFrame): Data to be preprocessed
        multiprocessing (bool, optional): If multiprocessing is to be used. Defaults to True.

    Returns:
        pd.DataFrame: Preprocessed dataframe
    """
    if multiprocessing:
        df = apply_parallel(df.groupby("id", group_keys=False), standardize_depth)
        df.reset_index(drop=True, inplace=True)
        df = apply_parallel(df.groupby("id", group_keys=False), preprocess)
    else:
        df = standardize_depth(df).reset_index(drop=True)
        df = preprocess(df)

    return df

def extract_features(df: pd.DataFrame) -> pd.DataFrame:
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
    cont_features = ["pressure", "sek10", "spyletrykk", "bortid"]
    cat_features = ["okt_rotasjon", "spyling", "slag"]

    for l in window_lengths:
        for col in cont_features:
            features["{}_rolling_median_{}".format(col, l)] = df[col].rolling(l, center=True, min_periods=1).median()
            features["{}_rolling_median_absolute_deviation_{}".format(col, l)] = df[col].rolling(l, center=True,
                                                                                                 min_periods=1).apply(
                lambda row: median_absolute_deviation(row))
            features["{}_rolling_sum_{}".format(col, l)] = df[col].rolling(l, center=True, min_periods=1).apply(
                lambda row: sum(row))
        for col in cat_features:
            features["{}_rolling_sum_{}".format(col, l)] = df[col].rolling(l, center=True, min_periods=1).sum()

    features["pressure_diff"] = df["pressure"].rolling(3, center=True, min_periods=1).median().diff().bfill()

    return features


def extract_features_total_sounding(df: pd.DataFrame, multiprocessing: bool=True) -> pd.DataFrame:
    """
    Extract features for the given preprocessed total sounding
    :param df: Input preprocessed total sounding
    :type df: pd.DataFrame
    :return: Extracted features,
    :rtype: df: pd.DataFrame
    """

    features = df[["depth", "pressure", "sek10", "spyletrykk", "spyling", "okt_rotasjon", "slag"]]

    if multiprocessing:
        rolling_features = apply_parallel(df.groupby("id", group_keys=False), extract_features)
    else:
        rolling_features = extract_features(df)

    features = pd.concat([features, rolling_features], axis=1)
    return features