import pandas as pd
import numpy as np
import logging

from azure.cosmosdb.table.models import Entity, EntityProperty, EdmType
from azure.cosmosdb.table.tableservice import TableService
from azure.cosmosdb.table.tablebatch import TableBatch

from datetime import date

logger = logging.getLogger(__name__)

def batch_upload_data_to_table_storage(data, table, connection_string):
    """
    Upload a list of dictionaries to Azure TableStorage
    
    :param data: A list of dictionaries containing data. All rows must contain the fields PartitionKey and RowKey
    :type data: list of dict
    :param table: The name of the table where the data will be inserted
    :type table: str
    :return: Number of uploaded rows
    :rtype: int
    """
    # Batch insertion in Azure requires all data in one batch to have the same PartitionKey
    sorted_data = {}
    uploaded = 0

    for row_entity in data:
        partitionKey = row_entity["PartitionKey"]
        if partitionKey not in sorted_data.keys():
            sorted_data[partitionKey] = []
        sorted_data[partitionKey].append(row_entity)
    
    for partitionKey in sorted_data.keys():
        _upload_batches_to_database(sorted_data[partitionKey], table, connection_string)
        uploaded += len(sorted_data[partitionKey])

    return uploaded

def _upload_batches_to_database(data, table, connection_string):
    """
    Upload data with the same PartitionKey in batches of up to 100 entities

    :param data: A list of dictionaries containing data. All rows must contain the fields PartitionKey and RowKey and have the same PartitionKey
    :type data: list of dict
    :param table: The name of the table where the data will be inserted
    :type table: str
    """
    table_service = TableService(connection_string=connection_string)

    batch = TableBatch()
    for row_entity in data:
        if len(batch._row_keys) == 100 or row_entity["RowKey"] in batch._row_keys:
            table_service.commit_batch(table, batch)
            batch = TableBatch()

        batch.insert_or_merge_entity(row_entity)

    table_service.commit_batch(table, batch)

def upload_data_to_table_storage(data, table, connection_string):
    """
    Upload a list of dictionaries to Azure TableStorage using single inserts
    
    :param data: A list of dictionaries containing data. All rows must contain the fields PartitionKey and RowKey
    :type data: list of dict
    :param table: The name of the table where the data will be inserted
    :type table: str
    :param connection_string: Connection string to Azure Storage
    :type connection_string: str
    :return: Number of uploaded rows
    :rtype: int
    """
    uploaded = 0

    table_service = TableService(connection_string=connection_string)

    try:
        for entity in data:
            table_service.insert_or_merge_entity(table, entity)
            uploaded += 1
    except Exception:
        logger.error(f"Single insert to table {table} failed", exc_info=True)

    return uploaded

def fetch_from_database(table, connection_string, partition_key=None):
    """
    Fetch all data from the table. The data can be filtered by partition key.

    :param table: The name of the table where the data will be inserted
    :type table: str
    :param connection_string: Connection string to Azure Storage
    :type connection_string: str
    :param partition_key: Name of PartitionKey to filter on
    :type partition_key: str
    """
    table_service = TableService(connection_string=connection_string)

    filter = "PartitionKey eq '{}'".format(partition_key) if partition_key else ""

    return list(table_service.query_entities(table, filter=filter))

def merge_rows_database(table, connection_string, merge_row):
    """
    Try to merge entity in Table Storage with new values

    :param table: The name of the table where the row to merge should exist
    :type table: str
    :param connection_string: Connection string to Azure Storage
    :type connection_string: str
    :param merge_row: Dictionary or entity containing PartitionKey and RowKey for
    the row to be updated, and also the new/updated values
    :type merge_row: Dict or entity
    """
    table_service = TableService(connection_string=connection_string)

    try:
        table_service.merge_entity(table, merge_row)
    except Exception as e:
        logger.error(f"Updating entity with PartitionKey '{merge_row['PartitionKey']}' and RowKey '{merge_row['RowKey']}' failed: {e}")

def fetch_existing_RowKeys_from_database(table, connection_string, partition_key=None):
    """
    Fetch all RowKeys from the table. The data can be filtered by partition key.

    :param table: The name of the table where the data will be inserted
    :type table: str
    :param connection_string: Connection string to Azure Storage
    :type connection_string: str
    :param partition_key: Name of PartitionKey to filter on
    :type partition_key: str
    :return: list of unique RowKeys
    :rtype: list(str)
    """
    table_service = TableService(connection_string=connection_string)

    filter = "PartitionKey eq '{}'".format(partition_key) if partition_key else ""

    entities = list(table_service.query_entities(table, filter=filter, select='RowKey'))
    keys = list(map(lambda x : x['RowKey'], entities))
    
    return list(set(keys))

def map_dataframe_features_to_entity_features(df: pd.DataFrame):
    """
    Map dataframe features to entity features allowed in Azure TableStorage

    :param file_data: Dataframe containing sounding data
    :type file_data: pandas DataFrame
    :return: Dataframe containing sounding data, with features accepted by Table Storage
    :rtype table_row: pd.DataFrame
    """

    date_cols = [c for c in df if df[c].dtype == "datetime64[ns]"]
    if date_cols:
        df[date_cols] = df[date_cols].apply(lambda r: EntityProperty(EdmType.DATETIME, r), axis=1)

    cat_cols = [c for c in df if df[c].dtype == "object"]
    if cat_cols:
        df[cat_cols] = df[cat_cols].astype(str)
    
    # Azure Table Storage cannot accept column names with spaces
    df.rename(columns= lambda c: c.replace(" ", "_"), inplace=True)

    return df

def map_dictionary_properties_to_entity_properties(file_data, table_row=None):
    """
    Map dictionary properties to entity properties allowed in Azure TableStorage

    :param file_data: dictionary containing data
    :type file_data: dict
    :param table_row: dictionary to be uploaded to Table Storage
    :type table_row: dict
    :return: dictionary ready for upload to Table Storage
    :rtype: dict
    """

    if not table_row:
        table_row = {}

    for name, value in file_data.items():
        if type(value) == np.float64:
            value = float(value)
        if isinstance(value, list):
            value = ','.join(map(str, value))
        if isinstance(value, pd.Timestamp):
            value = EntityProperty(EdmType.DATETIME, value)
        table_row[name] = value
    
    return table_row

def delete_table(table_name, connection_string):
    """
    Delete table from Azure Table Storage. Note that deleting a table in Azure
    only happens during Garbage Collection so there could be up to one minute
    from calling this function until you can create a table with the same name.

    :param table_name: Name of table to delete
    :type table_name: str
    :param connection_string: Connection string to Azure Storage
    :type connection_string: str
    """

    table_service = TableService(connection_string=connection_string)

    table_service.delete_table(table_name)

def create_table(table_name, connection_string):
    """
    Create new table in Azure Table Storage

    :param table_name: Name of table to create
    :type table_name: str
    :param connection_string: Connection string to Azure Storage
    :type connection_string: str
    """

    table_service = TableService(connection_string=connection_string)

    table_service.create_table(table_name)

def delete_and_create_table(table_name, connection_string):
    """
    Delete a table containing 'table_name' and create a new one with 'table_name' and todays date

    :param table_name: Name of table to create
    :type table_name: str
    :param connection_string: Connection string to Azure Storage
    :type connection_string: str
    """

    table_service = TableService(connection_string=connection_string)

    tables = table_service.list_tables()

    for table in tables:
        if table_name in table.name:
            delete_table(table.name, connection_string)
    
    create_table(f"{table_name}{str(date.today()).replace("-","")}", connection_string)

def get_table_name(table_name_keyword, connection_string):
    """
    Get name of table containing 'table_name_keyword' as a keyword

    :param table_name: Table name keyword
    :type table_name: str
    :param connection_string: Connection string to Azure Storage
    :type connection_string: str
    """

    table_service = TableService(connection_string=connection_string)

    tables = table_service.list_tables()

    for table in tables:
        if table_name_keyword in table.name:
            return table.name

    return ""
