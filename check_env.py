
import numpy
import pandas
import scipy
import sklearn
import matplotlib
import seaborn
import joblib
import dotenv
import influxdb_client
import paho.mqtt.client
import streamlit

from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error

print("=== KIEM TRA MOI TRUONG BAI 03 ===")
print("NumPy:", numpy.__version__)
print("Pandas:", pandas.__version__)
print("Scikit-learn:", sklearn.__version__)
print("Matplotlib:", matplotlib.__version__)
print("Streamlit:", streamlit.__version__)

print("\nTat ca thu vien da import thanh cong!")
