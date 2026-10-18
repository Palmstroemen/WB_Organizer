import os
import sys

# Make the addon modules importable without installing them into FreeCAD.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
