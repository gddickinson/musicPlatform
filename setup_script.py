#!/usr/bin/env python3
"""
Setup script for the Music Production Platform
Installs all required dependencies and sets up the environment
"""

import sys
import os
import platform
import subprocess
import argparse
import shutil
import site
import pkg_resources

def check_python_version():
    """Check if Python version is compatible"""
    required_version = (3, 8)
    current_version = sys.version_info
    
    if current_version < required_version:
        print(f"Error: Python {required_version[0]}.{required_version[1]} or higher is required")
        print(f"Current version: Python {current_version.major}.{current_version.minor}")
        return False
    
    return True

def install_pip_package(package, version=None):
    """Install a pip package with optional version specification"""
    try:
        if version:
            package_spec = f"{package}=={version}"
        else:
            package_spec = package
            
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_spec])
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing {package}: {e}")
        return False

def install_dependencies(advanced=False, audio_export=False, midi=False, force=False):
    """Install all required dependencies"""
    # Base dependencies
    base_packages = {
        "PyQt5": "5.15.0",
        "numpy": "1.19.0",
        "pyaudio": None,  # Latest version
        "pygame": "2.0.0",
        "scipy": "1.5.0",
        "pyqtgraph": "0.12.0"
    }
    
    # Advanced dependencies
    advanced_packages = {
        "soundfile": "0.10.0",
        "librosa": "0.8.0",
        "matplotlib": "3.3.0"
    }
    
    # Audio export dependencies
    audio_export_packages = {
        "soundfile": "0.10.0",
        "pydub": None  # Latest version
    }
    
    # MIDI dependencies
    midi_packages = {
        "rtmidi": "1.4.0",
        "mido": None  # Latest version
    }
    
    # First update pip itself
    print("Updating pip...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    
    # Install base packages
    print("\nInstalling base dependencies...")
    for package, version in base_packages.items():
        print(f"Installing {package}...", end=" ")
        success = install_pip_package(package, version)
        print("Done" if success else "Failed")
        
    # Install advanced packages if requested
    if advanced:
        print("\nInstalling advanced dependencies...")
        for package, version in advanced_packages.items():
            print(f"Installing {package}...", end=" ")
            success = install_pip_package(package, version)
            print("Done" if success else "Failed")
            
    # Install audio export packages if requested
    if audio_export:
        print("\nInstalling audio export dependencies...")
        for package, version in audio_export_packages.items():
            print(f"Installing {package}...", end=" ")
            success = install_pip_package(package, version)
            print("Done" if success else "Failed")
            
    # Install MIDI packages if requested
    if midi:
        print("\nInstalling MIDI dependencies...")
        for package, version in midi_packages.items():
            print(f"Installing {package}...", end=" ")
            success = install_pip_package(package, version)
            print("Done" if success else "Failed")
            
    # Try to install pyo (optional)
    if advanced or force:
        print("\nAttempting to install pyo (optional)...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyo"])
            print("pyo installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"Pyo installation failed: {e}")
            print("This is not critical - the application will use the alternative implementation")

def setup_samples_folder():
    """Create and populate the samples folder with example drum samples"""
    samples_dir = "samples"
    
    # Create the directory if it doesn't exist
    if not os.path.exists(samples_dir):
        os.makedirs(samples_dir)
        print(f"Created samples directory: {samples_dir}")
    
    # Check if any samples already exist
    sample_files = [f for f in os.listdir(samples_dir) if f.endswith(('.wav', '.mp3', '.ogg'))]
    
    if sample_files:
        print(f"Found {len(sample_files)} existing samples in {samples_dir} directory")
    else:
        print("No samples found. Creating example samples is not implemented yet.")
        # This would download or create some example samples
        # For now, it's left as an exercise for the user

def setup_macos_specific():
    """Perform macOS-specific setup"""
    print("Setting up macOS-specific configurations...")
    
    # Check for Homebrew
    try:
        subprocess.check_call(["which", "brew"])
        have_brew = True
    except subprocess.CalledProcessError:
        have_brew = False
        
    if have_brew:
        print("Homebrew found, installing required libraries...")
        
        # Try to install libsndfile and FLAC with Homebrew for pyo
        try:
            subprocess.check_call(["brew", "install", "libsndfile"])
            subprocess.check_call(["brew", "install", "flac"])
            print("Installed libsndfile and flac")
            
            # Try to link FLAC to the location pyo is looking for
            flac_path = subprocess.check_output(["brew", "--prefix", "flac"]).decode().strip()
            lib_path = os.path.join(flac_path, "lib")
            
            if os.path.exists(lib_path):
                # Check for the library file
                lib_files = [f for f in os.listdir(lib_path) if f.startswith("libFLAC") and f.endswith(".dylib")]
                
                if lib_files:
                    # Create the link directories if needed
                    os.makedirs("/opt/homebrew/opt/flac/lib", exist_ok=True)
                    
                    # Link the first library file found
                    src = os.path.join(lib_path, lib_files[0])
                    dst = "/opt/homebrew/opt/flac/lib/libFLAC.12.dylib"
                    
                    try:
                        os.symlink(src, dst)
                        print(f"Created symbolic link from {src} to {dst}")
                    except FileExistsError:
                        print(f"Link already exists: {dst}")
                    except PermissionError:
                        print(f"Permission denied when creating link. Try running with sudo")
                else:
                    print("No FLAC library files found")
            else:
                print(f"Library path not found: {lib_path}")
                
        except subprocess.CalledProcessError as e:
            print(f"Error installing libraries with Homebrew: {e}")
    else:
        print("Homebrew not found. To install required libraries, first install Homebrew from https://brew.sh")
        
    # Create a shell script with the DYLD_LIBRARY_PATH setting
    with open("run_music_platform.sh", "w") as f:
        f.write("#!/bin/bash\n")
        f.write("# Automatically generated by setup.py\n\n")
        
        # Try to locate the actual library paths
        python_path = os.path.dirname(sys.executable)
        site_packages = site.getsitepackages()[0]
        
        f.write("# Set the library path for pyo\n")
        f.write(f"export DYLD_LIBRARY_PATH={site_packages}/pyo:/opt/homebrew/lib:$DYLD_LIBRARY_PATH\n\n")
        f.write("# Run the application\n")
        f.write("python main.py\n")
        
    # Make the script executable
    os.chmod("run_music_platform.sh", 0o755)
    
    print("Created run_music_platform.sh script with necessary environment variables")

def setup_linux_specific():
    """Perform Linux-specific setup"""
    print("Setting up Linux-specific configurations...")
    
    # Check for package manager
    if shutil.which("apt-get"):
        # Debian/Ubuntu
        print("Detected Debian/Ubuntu system")
        print("Installing required packages...")
        
        try:
            subprocess.check_call(["sudo", "apt-get", "update"])
            subprocess.check_call([
                "sudo", "apt-get", "install", "-y",
                "libportaudio2", "libportaudiocpp0", "portaudio19-dev",
                "libsndfile1", "libsndfile1-dev",
                "libflac8", "libflac-dev"
            ])
            print("Installed required packages")
        except subprocess.CalledProcessError as e:
            print(f"Error installing packages: {e}")
            
    elif shutil.which("dnf"):
        # Fedora/RHEL
        print("Detected Fedora/RHEL system")
        print("Installing required packages...")
        
        try:
            subprocess.check_call([
                "sudo", "dnf", "install", "-y",
                "portaudio", "portaudio-devel",
                "libsndfile", "libsndfile-devel",
                "flac", "flac-libs", "flac-devel"
            ])
            print("Installed required packages")
        except subprocess.CalledProcessError as e:
            print(f"Error installing packages: {e}")
            
    elif shutil.which("pacman"):
        # Arch Linux
        print("Detected Arch Linux system")
        print("Installing required packages...")
        
        try:
            subprocess.check_call([
                "sudo", "pacman", "-S", "--noconfirm",
                "portaudio", "libsndfile", "flac"
            ])
            print("Installed required packages")
        except subprocess.CalledProcessError as e:
            print(f"Error installing packages: {e}")
            
    else:
        print("Could not detect package manager. Please install the following packages manually:")
        print("  - portaudio or portaudio19")
        print("  - libsndfile")
        print("  - flac")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Setup script for Music Production Platform")
    parser.add_argument("--advanced", action="store_true", help="Install advanced dependencies")
    parser.add_argument("--audio-export", action="store_true", help="Install audio export dependencies")
    parser.add_argument("--midi", action="store_true", help="Install MIDI dependencies")
    parser.add_argument("--all", action="store_true", help="Install all dependencies")
    parser.add_argument("--force", action="store_true", help="Force installation of optional dependencies")
    
    args = parser.parse_args()
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
        
    # Set flags for dependency installation
    install_advanced = args.advanced or args.all
    install_audio_export = args.audio_export or args.all
    install_midi = args.midi or args.all
    
    # Install dependencies
    install_dependencies(
        advanced=install_advanced,
        audio_export=install_audio_export,
        midi=install_midi,
        force=args.force
    )
    
    # Create samples folder
    setup_samples_folder()
    
    # Platform-specific setup
    system = platform.system()
    if system == "Darwin":
        setup_macos_specific()
    elif system == "Linux":
        setup_linux_specific()
    elif system == "Windows":
        # Windows-specific setup would go here
        pass
        
    print("\nSetup completed!")
    print("\nTo run the application:")
    
    if system == "Darwin":
        print("  ./run_music_platform.sh")
    else:
        print("  python main.py")
        
    print("\nIf you encounter any issues, please check the documentation or report them on the project GitHub page.")

if __name__ == "__main__":
    main()
