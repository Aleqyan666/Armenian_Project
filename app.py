import streamlit as st
from streamlit_option_menu import option_menu
import json, random, base64, urllib.parse, os, hashlib
import pandas as pd
from pathlib import Path
from datetime import datetime

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
    cred = credentials.Certificate(dict(st.secrets["firebase_sa_key"]))
    firebase_admin.initialize_app(cred)
db = firestore.client()


def quote_id(quote: dict) -> str:
    return hashlib.sha1((quote["author"] + "|" + quote["text"]).encode()).hexdigest()

def get_favorites_for_user(uid: str) -> set[str]:
    doc = db.collection("favorites").document(uid).get()
    return set(doc.to_dict().get("quote_ids", [])) if doc.exists else set()

def save_favorites_for_user(uid: str, favs: set[str]):
    db.collection("favorites").document(uid).set({"quote_ids": list(favs)})

def DisplayQuoteCard(quote: dict, user_uid: str, favorites: set[str]):
    qid = quote_id(quote)
    is_fav = (qid in favorites)

    # Quote styling
    st.markdown(f"""
    <div style="
      background:#f9f9f9;
      padding:1em;
      margin-bottom:1em;
      border-radius:8px;
      box-shadow:1px 1px 8px rgba(0,0,0,0.1);
    ">
      <p style="font-style:italic;">"{quote['text']}"</p>
      <p style="text-align:right; font-weight:bold;">– {quote['author']}</p>
    </div>
    """, unsafe_allow_html=True)

    # Add or Remove button
    if is_fav:
        if st.button("Remove from Favorites", key=f"rm_{qid}"):
            favorites.remove(qid)
            save_favorites_for_user(user_uid, favorites)
            st.rerun()
    else:
        if st.button("Add to Favorites", key=f"add_{qid}"):
            favorites.add(qid)
            save_favorites_for_user(user_uid, favorites)
            st.rerun()

# --- 3) Helper: Firestore operations ---
def get_posts():
    docs = db.collection("posts") \
             .order_by("time", direction=firestore.Query.DESCENDING) \
             .stream()
    return [doc.to_dict() for doc in docs]

def add_post(post):
    db.collection("posts").document(str(post["id"])).set(post)


# --- 4) Authentication UI ---
def LoginUI():
    st.subheader("🔑 Մուտք")
    email = st.text_input("էլ. հասցե", key="login_email")
    pwd = st.text_input("Գաղտնաբառ", type="password", key="login_pwd")
    if st.button("Մուտք գործել"):
        try:
            user = auth.sign_in_with_email_and_password(email, pwd)
            st.session_state.user = user
            st.success("Դուք մուտք գործեցիք:")
        except Exception as e:
            st.error("Մուտք գործելիս տեղի ունեցավ սխալ:")
            # st.error("Login failed: " + str(e))

def RegisterUI():
    st.subheader("🆕 Գրանցում")
    email = st.text_input("էլ. հասցե", key="reg_email")
    pwd   = st.text_input("Գաղտնաբառ", type="password", key="reg_pwd")
    if st.button("Ստեղծել հաշիվ"):
        try:
            user = auth.create_user_with_email_and_password(email, pwd)
            st.success("Հաշիվը ստեղծվեց: Խնդրում ենք այժմ մուտք գործել:")
        except Exception as e:
            st.error("Գրանցվելիս տեղի ունեցավ սխալ:")
            # st.error("Registration failed: " + str(e))

def RequireLogin():
    if "user" not in st.session_state:
        choice = st.radio("Ունե՞ք հաշիվ:", ["Մուտք","Գրանցում"])
        if choice == "Մուտք":
            LoginUI()
        else:
            RegisterUI()
        st.stop()  # halt further rendering until logged in


st.set_page_config(page_title="Հասարակական Բռնաճնշումներ", layout="wide")
st.markdown("""
    <style>
        html, body, [class*="css"] {
            font-family: 'Georgia', serif;
            font-size: 16px;
        }
        h1, h2, h3, .stSubheader {
            color: #1c1c1c;
        }
        .stButton>button {
            background-color: #f5c518;
            color: black;
            border: none;
            padding: 0.5rem 1.5rem;
            border-radius: 8px;
        }
        .stButton>button:hover {
            background-color: #e4b911;
        }
        .stTextInput>div>div>input, .stTextArea textarea {
            background-color: #fffef8;
            border: 1px solid #e4dcd0;
        }
        .stTextInput>div>div>input:focus, .stTextArea textarea:focus {
            border-color: #f5c518;
        }
        .block-container {
            padding-top: 2rem;
        }
    </style>
""", unsafe_allow_html=True)



def GetQuotes(json_path: str = "quotes.json") -> list[dict]: # TODO
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback to an empty list if file is missing
        return []

def GetYoutubeId(url):
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    return qs.get("v", [None])[0]

def VideoCard(title, url):
    vid_id = GetYoutubeId(url)
    thumb = f"https://img.youtube.com/vi/{vid_id}/hqdefault.jpg"
    card_html = f"""
            <div style="
                border: 1px solid #ddd;
                border-radius: 10px;
                padding: 10px;
                margin-bottom: 1rem;
                background-color: #fff;
                box-shadow: 0 2px 6px rgba(0,0,0,0.1);
                transition: transform .2s;
            " onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
                <a href="{url}" target="_blank" style="text-decoration:none; color:inherit;">
                    <img src="{thumb}" style="width:100%; height:auto; border-radius:8px;"/>
                    <h4 style="margin:0.5rem 0 0.2rem;">{title}</h4>
                    <p style="color:#555; font-size:0.9rem;">Watch on YouTube ▶️</p>
                </a>
            </div>
            """
    st.markdown(card_html, unsafe_allow_html=True)

# 5) Main app
def main():
    with st.sidebar:
        page = option_menu(
            menu_title="Navigation",
            options=["Home", "About Us", "Forum", "Quotes", "Reportages", "Resources"],
            icons=["house", "info-circle", "chat-left-text", "file-earmark-text", "camera-video", "book"],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"padding": "5!important", "background-color": "#fafafa"},
                "icon": {"color": "fff", "font-size": "20px"},
                "nav-link": {
                    "font-size": "18px",
                    "text-align": "left",
                    "margin": "5px",
                    "--hover-color": "#eee",
                },
                "nav-link-selected": {"background-color": "#e4b911", "color": "white"},
            }
        )

    # Home
    if page == "Home":
        # CATEGORIES = ["Ethics", "Metaphysics", "Logic", "Politics", "Aesthetics", "Other"]

        st.title("🏛️ Welcome to the Philosophy Portal")
        st.write("Explore thoughts, discussions, and ideas from the greatest minds and community voices.")

        posts = get_posts()

        # 2. Key metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("📄 Total Posts", len(posts))
        #! col2.metric("👥 Registered Users", get_user_count())
        # col3.metric("🏷️ Categories", len(CATEGORIES))

        st.markdown("---")

        # 3. Search bar & quick filter
        st.subheader("🔍 Search Forum Posts")
        query = st.text_input("", placeholder="Type to search by title or content…")
        if query:
            filtered_posts = [
                p for p in posts
                if query.lower() in p["title"].lower() or query.lower() in p["content"].lower()
            ]
        else:
            filtered_posts = posts

        # Prepare latest posts (filtered or all)
        sorted_posts = sorted(
            filtered_posts,
            key=lambda x: datetime.strptime(x["time"], "%Y-%m-%d %H:%M:%S"),
            reverse=True,
        )

        # 4. Latest Forum Posts
        st.subheader("📰 Latest Forum Posts")
        if sorted_posts:
            for post in sorted_posts[:5]:
                st.markdown(f"**{post['title']}**")
                st.markdown(f"*By {post['name']} on {post['time']}*")
                st.markdown("---")
        else:
            st.info("No posts match your search. Try a different keyword!")

        # 7. Call-to-Action Button
        if st.button("📝 Jump to Forum"):
            st.info("Use the sidebar to select **Forum** and join the discussion!")

        st.markdown("---")

        # 4. Quote of the Day
        st.subheader("💬 Quote of the Day")
        quote = random.choice(GetQuotes())
        st.markdown(f"> _“{quote['text']}”_  \n— **{quote['author']}**")
    
        st.markdown("---")


    elif page == "About Us":
        st.title("About Us")

        # Mission & Vision
        st.subheader("🌟 Our Mission")
        st.write(
            "At the Philosophy Portal, we strive to make philosophical discourse "
            "accessible, inclusive, and vibrant. We connect thinkers from around the world "
            "to explore timeless questions and contemporary issues."
        )

        # Team Profiles
        team_html = """
        ### 👤 Meet the Founders  
        <div style="display:flex; flex-wrap: wrap; gap:2rem;">
        <div style="flex: 1 1 200px; text-align:center;">
            <img src="https://your-cdn.com/you.jpg" alt="Your Name" 
                style="width:120px;border-radius:50%;"/>
            <p><strong>Your Name</strong><br/>
            Data Scientist & Lead Developer</p>
            <p>✉️ <a href="mailto:you@example.com">you@example.com</a><br/>
            📞 +1 (555) 123-4567<br/>
            🔗 <a href="https://linkedin.com/in/yourprofile" target="_blank">LinkedIn</a>
            </p>
        </div>
        <div style="flex: 1 1 200px; text-align:center;">
            <img src="https://your-cdn.com/cofounder.jpg" alt="Co-founder" 
                style="width:120px;border-radius:50%;"/>
            <p><strong>Co-Founder Name</strong><br/>
            Philosophy Enthusiast & Community Manager</p>
            <p>✉️ <a href="mailto:cofounder@example.com">cofounder@example.com</a><br/>
            📞 +1 (555) 987-6543<br/>
            🔗 <a href="https://twitter.com/cofounder" target="_blank">Twitter</a>
            </p>
        </div>
        </div>
        """
        st.markdown(team_html, unsafe_allow_html=True)

        st.markdown("---")

    # Forum
    elif page == "Forum":
        st.title("🗣️ Forum")
        RequireLogin()

        user_email = st.session_state.user["email"]
        st.title(f"Logged in as {user_email}")

        name = user_email.split("@")[0]  
        title = st.text_input("📝 Topic Title")
        content = st.text_area("💬 Your message")

        if st.button("Submit Post"):
            if title and content:
                post = {
                    "id": int(datetime.now().timestamp()*1000),
                    "name": name,
                    "title": title,
                    "content": content,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                add_post(post)
                st.success("Posted!")
            else:
                st.error("Fill in both title and content.")

        st.subheader("📚 All Posts")
        # CATEGORIES = ["Ethics", "Metaphysics", "Logic", "Politics", "Aesthetics", "Other"]
        # theme = st.selectbox("🔖 Filter by theme", CATEGORIES)
        all_posts = get_posts()

        # filtered = [p for p in all_posts if p.get("category") == theme]
        filtered = all_posts
        # st.subheader(f"📚 Showing posts: {theme}")
        if filtered:
            for p in filtered:
                st.markdown(f"#### {p['title']}")
                st.write(p["content"])
                st.caption(f"By {p['name']} at {p['time']}")
                st.markdown("---")
        else:
            st.info("No posts in this category.")
            
            for p in get_posts():
                st.markdown(f"#### {p['title']}")
                st.write(p["content"])
                st.caption(f"By {p['name']} at {p['time']}")
                st.markdown("---")

    # Quotes
    elif page == "Quotes": 
        st.title("Հայտնի Խոսքեր և Մտքեր")

        if "user" not in st.session_state:
            st.error("Խնդրում ենք մուտք գործել կայքեջ:")
            st.stop()
        user_uid = st.session_state.user["localId"]

        quotes = GetQuotes()
        authors = sorted({q["author"] for q in quotes})

        # Author filter and “Show My Favorites” toggle
        col1, col2 = st.columns([3,1])
        with col1:
            author_filter = st.selectbox("Filter by author", ["All"] + authors)
        with col2:
            show_favs = st.checkbox("Իմ Հավանածները")

        # Fetch current favorites once
        favorites = get_favorites_for_user(user_uid)

        # Filter quotes
        def matches(q):
            return (
                (author_filter == "All" or q["author"] == author_filter)
                and (not show_favs or quote_id(q) in favorites)
            )

        filtered = [q for q in quotes if matches(q)]
        st.write(f"Ցուցադրվում են {len(filtered)} խոսքեր")

        # Render each, passing in the same `favorites` set
        for q in filtered:
            DisplayQuoteCard(q, user_uid, favorites)


    # Reportages
    elif page == "Reportages":

        st.title("🎥 Reportages & Videos")

        videos = [
    (
        "Understanding Nietzsche: Philosophy in Modern Times",
        "https://www.youtube.com/watch?v=fLJBzhcSWTk"
    ),  
    (   
        "The Case for Idealism: Truth, Facts, and Existence",
        "https://www.youtube.com/watch?v=7quW8AlngH0&ab_channel=NathanHawkins"
    ),
    (
        "OSHO: Nobody Allows Anybody to Be Just Himself",
        "https://www.youtube.com/watch?v=UngV-qwNkW0&ab_channel=OSHOInternational"
    ),
    (
        "We’re wired for conformity. That’s why we have to practice dissent. Todd Rose for Big Think",
        "https://www.youtube.com/watch?v=rd8VHbIYqRs&ab_channel=BigThink"
    ),
    (
        "Nietzsche - Follow No One, Trust Yourself",
        "https://www.youtube.com/watch?v=e-k7b8Zmh70&ab_channel=FreedominThought"
    ),
    (
        "Existentialism Explained: Key Concepts of Jean-Paul Sartre",
        "https://www.youtube.com/watch?v=VtP-N9pqoKk"
    ),  
    (
        "The Philosophy of Absurdism: Albert Camus and the Absurd",
        "https://www.youtube.com/watch?v=DTRJx1d4eks"
    ),  
    (
        "Nietzsche’s Will to Power: An In-depth Analysis",
        "https://www.youtube.com/watch?v=bb7Q8Wu1HNA"
    ),  
    (
        "Heidegger and Being: Exploring the Concept of Being",
        "https://www.youtube.com/watch?v=0-yvwlKTTbk"
    )   
]

        # render in 2-column grid
        for i in range(0, len(videos), 2):
            cols = st.columns(2, gap="large")
            for col, (title, url) in zip(cols, videos[i:i+2]):
                with col:
                    VideoCard(title, url)

    # Resources
    elif page == "Resources":
        st.title("Resources")
        resource_dir = Path("resources")
        if not resource_dir.exists():
            st.info("No resources folder found.")
        else:
            resources = [
                ("Այսպես Խոսեց Զրադաշտը.pdf", resource_dir / "Այսպես Խոսեց Զրադաշտը.pdf"),
                ("Բարուց և Չարից Անդին.pdf", resource_dir / "Բարուց և Չարից Անդին.pdf"),
                ("The Power of Conformity.pdf", resource_dir / "The Power of Conformity.pdf"),
                ("Festinger, Leon - A theory of cognitive dissonance (1968, Stanford University Press).pdf", resource_dir / "Festinger, Leon - A theory of cognitive dissonance (1968, Stanford University Press).pdf"),
                ("Cognitive Dissonance. Reexamining a Pivotal Theory in Psychology, Second Edition.pdf", resource_dir / "Cognitive Dissonance. Reexamining a Pivotal Theory in Psychology, Second Edition.pdf")
            ]
            icon_map = {
                '.pdf': '📄', '.docx': '📝', '.xlsx': '📊', '.xls': '📊',
                '.csv': '📑', '.png': '🖼️', '.jpg': '🖼️', '.jpeg': '🖼️', '.txt': '📃'
            }
            for name, _ in resources:
                key = f"view_{name}"
                if key not in st.session_state:
                    st.session_state[key] = False

            for name, path_obj in resources:
                if path_obj.exists():
                    ext = path_obj.suffix.lower()
                    icon = icon_map.get(ext, '📁')
                    col1, col2, col3 = st.columns([6,1,1])
                    with col1:
                        st.write(f"{icon} **{name}**")
                    with col2:
                        if not st.session_state[f"view_{name}"]:
                            if st.button("View", key=f"btn_view_{name}"):
                                st.session_state[f"view_{name}"] = True
                    with col3:
                        data = path_obj.read_bytes()
                        st.download_button(label="Download", data=data, file_name=name, key=f"btn_down_{name}")

                    # Show preview if flagged
                    if st.session_state[f"view_{name}"]:
                        with st.expander(f"Preview: {name}", expanded=True):
                            if ext == '.csv':
                                df = pd.read_csv(path_obj)
                                st.dataframe(df)
                            elif ext in ['.xlsx', '.xls']:
                                df = pd.read_excel(path_obj)
                                st.dataframe(df)
                            elif ext in ['.png', '.jpg', '.jpeg']:
                                st.image(str(path_obj), caption=name)
                            elif ext == '.pdf':
                                pdf_bytes = path_obj.read_bytes()
                                b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                                pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="800" height="500" type="application/pdf"></iframe>'
                                st.markdown(pdf_display, unsafe_allow_html=True)
                            elif ext == '.docx':
                                try:
                                    from docx import Document
                                    doc = Document(str(path_obj))
                                    text = ''.join([p.text for p in doc.paragraphs])
                                    st.text_area("Document Preview", text, height=300)
                                except ImportError:
                                    st.warning("Install python-docx to preview DOCX files.")
                            # Close button
                            if st.button("Close Preview", key=f"btn_close_{name}"):
                                st.session_state[f"view_{name}"] = False
                else:
                    st.error(f"Resource not found: {name}")

if __name__ == "__main__":
    main() 