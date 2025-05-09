import json
import hashlib
from google.cloud import firestore

import pyrebase
import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st

firebase = pyrebase.initialize_app(st.secrets["firebase_config"])
auth = firebase.auth()

KEY_PATH = "ServiceAccountKey.json"
try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate(KEY_PATH)
    firebase_admin.initialize_app(cred)
db = firestore.client()

with open("quotes.json", "r", encoding="utf-8") as f:
    quotes = json.load(f)

for q in quotes:
    key = q["author"] + "|" + q["text"]
    doc_id = hashlib.sha1(key.encode("utf-8")).hexdigest()
    db.collection("quotes").document(doc_id).set({
        "text": q["text"],
        "author": q["author"]
    })
    print(f"Imported quote by {q['author']} → doc ID {doc_id}")

print("All quotes imported!")
