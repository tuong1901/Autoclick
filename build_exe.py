"""
Build script to create standalone EXE for CTAutoClick Pro
"""
import PyInstaller.__main__
import os
import sys

def build_exe():
    """Build the executable using PyInstaller"""
    
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(script_dir, 'auto_clicker', 'advanced_main.py')
    
    # PyInstaller arguments
    args = [
        main_script,
        '--name=CTAutoClickPro',
        '--onefile',
        '--windowed',  # No console window
        '--icon=NONE',  # Add icon path if you have one
        
        # Hidden imports that PyInstaller might miss
        '--hidden-import=pynput.keyboard._win32',
        '--hidden-import=pynput.mouse._win32',
        '--hidden-import=PIL._tkinter_finder',
        
        # Add data files if needed
        # '--add-data=icon.ico;.',
        
        # Output directory
        '--distpath=dist',
        '--workpath=build',
        '--specpath=build',
        
        # Clean build
        '--clean',
        
        # Optimization
        '--optimize=2',
    ]
    
    print("=" * 60)
    print("Building CTAutoClick Pro EXE...")
    print("=" * 60)
    print(f"Main script: {main_script}")
    print()
    
    # Run PyInstaller
    PyInstaller.__main__.run(args)
    
    print()
    print("=" * 60)
    print("Build complete!")
    print("=" * 60)
    print(f"Executable location: {os.path.join(script_dir, 'dist', 'CTAutoClickPro.exe')}")
    print()

if __name__ == "__main__":
    build_exe()
