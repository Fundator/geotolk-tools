from azure.storage.file import FileService, ContentSettings
import sys
import os

def upload_folder_to_file_storage(fileshare_name: str, account_name: str, account_key: str, folderpath: str, overwrite_existing: bool = False) -> None:
    """Uploads all content of a folder to azure file storage. Creates a new file storage if the name is not found

    Args:
        fileshare_name (str): Name of the fileshare
        account_name (str): Storage account name
        account_key (str): Storage account key
        folderpath (str): Local path of the folder to be uploaded. Needs to contain directories with sounding files in it
        overwrite_existing (bool, optional): Whether files with the same name on the storage account should be overwritten or not. Defaults to False.
    """
    def directory_exists(file_service_name, directory_name):
        return directory_name in [i.name for i in list(file_service.list_directories_and_files(file_service_name))]
    
    def file_exists(file_service_name, directory_name, filename):
        return filename in [i.name for i in list(file_service.list_directories_and_files(file_service_name, directory_name))]
    
    # Create file service
    file_service = FileService(account_name=account_name, account_key=account_key)
    # Check if file service exists, otherwise create it
    if not file_service.exists(fileshare_name):
        file_service.create_share(fileshare_name, quota=5)
    
    for directoryname in os.listdir(folderpath):
        if not directory_exists(fileshare_name, directoryname):
            file_service.create_directory(fileshare_name, directoryname)

        directory_abspath = os.path.join(folderpath, directoryname)
        for filename in os.listdir(directory_abspath):
            if not file_exists(fileshare_name, directoryname, filename) or overwrite_existing:
                file_abspath = os.path.join(directory_abspath, filename)
                file_service.create_file_from_path(share_name=fileshare_name, directory_name=directoryname, file_name=filename, local_file_path=file_abspath, content_settings=ContentSettings(content_type="text/plain"))
    
    