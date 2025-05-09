# import toml, json
# conf = toml.load(".streamlit/secrets.toml")
# sa_str = conf.get("firebase_sa_key")
# if not sa_str:
#     print("❌ Key ‘firebase_sa_key’ not found in TOML.")
# else:
#     try:
#         sa = json.loads(sa_str)
#         print("✅ Successfully parsed firebase_sa_key; service_account email:", sa["client_email"])
#     except Exception as e:
#         print("❌ Error parsing firebase_sa_key JSON:", e)


import streamlit as st
import pyrebase
import firebase_admin
from firebase_admin import credentials, firestore

# Init Firebase Auth (Pyrebase) 
firebase = pyrebase.initialize_app(st.secrets["firebase_config"])
auth = firebase.auth()

KEY_PATH = "ServiceAccountKey.json"
try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate(KEY_PATH)
    firebase_admin.initialize_app(cred)
db = firestore.client()
docs = db.collection("posts").stream()
posts = [doc.to_dict() for doc in docs]
print(posts)

def get_user_count() -> int:
    return len(list(db.collection("users").stream()))
print(get_user_count())
