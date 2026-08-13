def last_folder():
    """Reads the last-used folder path and its return value.
    If the folder does not exist or cannot be found, function returns a temporary directory."""
    from qaequilibrae.modules.common_tools.get_output_file_name import last_accessed_folder

    return last_accessed_folder()
