"""
A utility module to provide standardized file dialogs for the music production platform.
This ensures consistent behavior across all components when selecting audio files.
"""

from PyQt5.QtWidgets import QFileDialog
import os

class FileDialogUtils:
    @staticmethod
    def get_audio_file(parent=None, title="Select Audio File", directory="", selected_filter=None):
        """
        Open a file dialog to select a single audio file
        
        Parameters:
        - parent: Parent widget
        - title: Dialog title
        - directory: Starting directory
        - selected_filter: Initially selected filter
        
        Returns:
        - file_path: Selected file path or empty string if canceled
        - selected_filter: The filter that was selected by the user
        """
        filters = (
            "Audio Files (*.wav *.mp3 *.ogg *.flac *.aiff);;WAV Files (*.wav);;MP3 Files (*.mp3);;"
            "OGG Files (*.ogg);;FLAC Files (*.flac);;AIFF Files (*.aiff);;All Files (*)"
        )
        
        file_path, selected_filter = QFileDialog.getOpenFileName(
            parent, title, directory, filters, selected_filter
        )
        
        return file_path, selected_filter
    
    @staticmethod
    def get_multiple_audio_files(parent=None, title="Select Audio Files", directory="", selected_filter=None):
        """
        Open a file dialog to select multiple audio files
        
        Parameters:
        - parent: Parent widget
        - title: Dialog title
        - directory: Starting directory
        - selected_filter: Initially selected filter
        
        Returns:
        - file_paths: List of selected file paths or empty list if canceled
        - selected_filter: The filter that was selected by the user
        """
        filters = (
            "Audio Files (*.wav *.mp3 *.ogg *.flac *.aiff);;WAV Files (*.wav);;MP3 Files (*.mp3);;"
            "OGG Files (*.ogg);;FLAC Files (*.flac);;AIFF Files (*.aiff);;All Files (*)"
        )
        
        file_paths, selected_filter = QFileDialog.getOpenFileNames(
            parent, title, directory, filters, selected_filter
        )
        
        return file_paths, selected_filter
    
    @staticmethod
    def get_save_audio_file(parent=None, title="Save Audio File", directory="", selected_filter=None):
        """
        Open a file dialog to save an audio file
        
        Parameters:
        - parent: Parent widget
        - title: Dialog title
        - directory: Starting directory
        - selected_filter: Initially selected filter
        
        Returns:
        - file_path: Selected file path or empty string if canceled
        - selected_filter: The filter that was selected by the user
        """
        filters = (
            "WAV Files (*.wav);;MP3 Files (*.mp3);;OGG Files (*.ogg);;"
            "FLAC Files (*.flac);;AIFF Files (*.aiff);;All Files (*)"
        )
        
        file_path, selected_filter = QFileDialog.getSaveFileName(
            parent, title, directory, filters, selected_filter
        )
        
        # Add extension if not present
        if file_path and '.' not in os.path.basename(file_path):
            # Extract extension from selected filter
            if "WAV" in selected_filter:
                file_path += ".wav"
            elif "MP3" in selected_filter:
                file_path += ".mp3"
            elif "OGG" in selected_filter:
                file_path += ".ogg"
            elif "FLAC" in selected_filter:
                file_path += ".flac"
            elif "AIFF" in selected_filter:
                file_path += ".aiff"
        
        return file_path, selected_filter
    
    @staticmethod
    def get_directory(parent=None, title="Select Directory", directory=""):
        """
        Open a file dialog to select a directory
        
        Parameters:
        - parent: Parent widget
        - title: Dialog title
        - directory: Starting directory
        
        Returns:
        - directory: Selected directory or empty string if canceled
        """
        return QFileDialog.getExistingDirectory(parent, title, directory)
