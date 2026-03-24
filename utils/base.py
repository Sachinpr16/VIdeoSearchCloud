import os
import json
import time
import uuid
import threading
import cv2
import numpy as np
import torch
import torchvision.transforms as transforms
from PIL import Image
from flask import Blueprint, Flask, jsonify, current_app, request, abort, send_file, render_template
import faiss
import pickle

import subprocess
from db_utils import get_db_manager

from datetime import datetime
# from dotenv import load_dotenv
from generate_key import *
from config import get_config

app = Flask(__name__)

# Get the global configuration instance
config = get_config()

def load_index(index_path, embedding_dim=768):  #used in index and remove
    """Helper function to load an index from a file"""
    if os.path.exists(index_path):
        try:
            index = faiss.read_index(index_path)
        except Exception as e:
            print(f"Failed to load existing FAISS index from {index_path}: {e}")
            index = faiss.IndexIDMap(faiss.IndexFlatIP(embedding_dim))
    else:
        index = faiss.IndexIDMap(faiss.IndexFlatIP(embedding_dim))
    return index

def save_index(index_path, index):  #used in index and remove
    """Helper function to save an index to a file"""
    try:
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        faiss.write_index(index, index_path)
        return True
    except Exception as e:
        print(f"Failed to save FAISS index to {index_path}: {e}")
        return False

def initialize_config(app):  #used in app
    """Initialize configuration from Flask app"""
    config.initialize_config(app)

def initialize_db_config(app):  #used in app 
    """Initialize database configuration from Flask app"""
    config.initialize_db_config(app)

def get_index_files(db_name="_default_db"):  #used in other files
    """Get index file paths for different types"""
    return config.get_index_files(db_name)

def is_online():
    return config.is_online()
