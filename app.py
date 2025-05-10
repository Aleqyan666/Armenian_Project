import streamlit as st
from streamlit_option_menu import option_menu
import json, random, base64, urllib.parse, os, hashlib, toml
import pandas as pd
from pathlib import Path
from datetime import datetime

import pyrebase
import firebase_admin
from firebase_admin import credentials, firestore

# Init Firebase Auth (Pyrebase) 
firebase = pyrebase.initialize_app(st.secrets["firebase_config"])
auth = firebase.auth()

try:
    firebase_admin.get_app()
except ValueError:
    with open(".streamlit/secrets.toml", "r") as f:
        toml_data = toml.load(f)
    json_data = json.dumps(toml_data["firebase_sa_key"])
    cred = credentials.Certificate(toml_data["firebase_sa_key"])
    # cred = credentials.Certificate(dict(st.secrets["firebase_sa_key"]))
    firebase_admin.initialize_app(cred)
db = firestore.client()

def get_user_count():
    from firebase_admin import auth as admin_auth
    page = admin_auth.list_users()
    count = 0
    while page:
        count += len(page.users)
        page = page.get_next_page()
    return count

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
        if st.button("Հեռացնել հավանածներից", key=f"rm_{qid}"):
            favorites.remove(qid)
            save_favorites_for_user(user_uid, favorites)
            st.rerun()
    else:
        if st.button("Հավանել", key=f"add_{qid}"):
            favorites.add(qid)
            save_favorites_for_user(user_uid, favorites)
            st.rerun()

# --- 3) Helper: Firestore operations ---
def get_posts():
    docs = db.collection("posts") \
             .order_by("time", direction=firestore.Query.DESCENDING) \
             .stream()
    return [doc.to_dict() for doc in docs]

def add_post(post, reply_to_id=None):
    if reply_to_id:
        ref = db.collection("posts").document(str(reply_to_id))
        doc = ref.get()
        if doc.exists:
            replies = doc.to_dict().get("replies", [])
            replies.append(post)
            ref.update({"replies": replies})
    else:
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
    pwd   = st.text_input("Գաղտնաբառ (առնվազն 6 նիշ)", type="password", key="reg_pwd")
    if st.button("Ստեղծել հաշիվ"):
        if len(pwd) < 6:
            st.warning("Գաղտնաբառը պետք է պարունակի  առնվազն 6 նիշ:")
        else:
            try:
                user = auth.create_user_with_email_and_password(email, pwd)
                st.success("Հաշիվը ստեղծվեց: Խնդրում ենք այժմ մուտք գործել:")
            except Exception as e:
                st.error("Գրանցվելիս տեղի ունեցավ սխալ:")
                # st.error("Registration failed: " + str(e))

def RequireLogin():
    if "user" not in st.session_state:
        st.markdown("<h5 >Ունե՞ք հաշիվ:</h5>", unsafe_allow_html=True)
        choice = st.radio("", ["Մուտք", "Գրանցում"], key="auth_choice")
        
        if choice == "Մուտք":
            LoginUI()
        else:
            RegisterUI()
        st.stop()  


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

def SingleVideoCard(title, url):
    video_id = url.split("v=")[-1].split("&")[0]
    thumb = f"https://img.youtube.com/vi/{video_id}/0.jpg"

    card_html = f"""
    <div style="
        max-width: 320px;
        border-radius: 14px;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        transition: transform 0.2s;
    " onmouseover="this.style.transform='scale(1.03)'" onmouseout="this.style.transform='scale(1)'">
        <a href="{url}" target="_blank" style="text-decoration: none;">
            <img src="{thumb}" style="width: 100%; display: block; border-radius: 14px;" />
        </a>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)



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
                    <p style="color:#555; font-size:0.9rem;">Դիտել YouTube-ում ▶️</p>
                </a>
            </div>
            """
    st.markdown(card_html, unsafe_allow_html=True)

# 5) Main app
def main():
    with st.sidebar:
        page = option_menu(
            menu_title="Ցանկ",
            options=["Գլխավոր էջ", "Մեր Մասին", "Ֆորում", "Մտքեր", "Տեսադարան", "Գիտադարան"],
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

    # Գլխավոր էջ
    if page == "Գլխավոր էջ":
        # CATEGORIES = ["Ethics", "Metaphysics", "Logic", "Politics", "Aesthetics", "Other"]

        st.title("🏛️ Welcome to the Portal")
        st.write("Explore thoughts, discussions, and ideas from the greatest minds and community voices.")

        posts = get_posts()

        # 2. Key metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("📄 Ընդհանուր հրապարոկումներ", len(posts))
        col2.metric("👥 Գրանցված օգտատերեր", get_user_count())

        st.markdown("---")

        # 3. Search bar & quick filter
        st.subheader("🔍 Փնտրել Հրապարակումներ")
        query = st.text_input("", placeholder="Փնտել հրապարակումներ՝ ըստ վերնագրի և բովանդակության:")
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

        st.subheader("📰 Վերջին Հրապարակումները")

        if sorted_posts:
            for post in sorted_posts[:5]:
                st.markdown(f"""
                    <div style="font-size: 1.3rem;">
                        <strong>{post['title']}</strong><br>
                        <em>By {post['name']} on {post['time']}</em>
                    </div>
                """, unsafe_allow_html=True)
                st.markdown("---")
        else:
            st.info("Որոնման արդյունքում ոչինչ չի գտնվել: Փորձեք այլ բանալի բառեր:")

        
        # 4. Quote of the Day
        st.subheader("💬 Օրվա Միտքը")
        quote = random.choice(GetQuotes())
        st.markdown(f"""
            <div style="font-size: 20px;">
                “{quote['text']}”  <br>
                — <strong>{quote['author']}</strong>
            </div>
        """, unsafe_allow_html=True)    
        st.markdown("---")

        # 🎯 Video of the Day
        videos = [
            ("Understanding Nietzsche: Philosophy in Modern Times", "https://www.youtube.com/watch?v=fLJBzhcSWTk", "Փիլիսոփայություն"),
            ("The Case for Idealism: Truth, Facts, and Existence", "https://www.youtube.com/watch?v=7quW8AlngH0", "Փիլիսոփայություն"),
            ("OSHO: Nobody Allows Anybody to Be Just Himself", "https://www.youtube.com/watch?v=UngV-qwNkW0", "Ինդիվիդուալիզմ"),
            ("We’re wired for conformity...", "https://www.youtube.com/watch?v=rd8VHbIYqRs", "Հոգեբանություն"),
            ("Nietzsche - Follow No One...", "https://www.youtube.com/watch?v=e-k7b8Zmh70", "Ինդիվիդուալիզմ"),
            ("Existentialism Explained", "https://www.youtube.com/watch?v=VtP-N9pqoKk", "Էքզիստենցիալիզմ"),
            ("The Philosophy of Absurdism", "https://www.youtube.com/watch?v=DTRJx1d4eks", "Աբսուրդիզմ"),
            ("Nietzsche’s Will to Power", "https://www.youtube.com/watch?v=bb7Q8Wu1HNA", "Ինդիվիդուալիզմ"),
            ("Heidegger and Being", "https://www.youtube.com/watch?v=0-yvwlKTTbk", "Էքզիստենցիալիզմ")
        ]
        st.subheader("📺 Օրվա Տեսանյութը")
        random_video = random.choice(videos)
        title, url, category = random_video

        left, right = st.columns([2, 2.2])  # Adjust ratio as needed

        with left:
            st.markdown(f"""
            <div style="font-size: 20px;">
                <strong style="font-size: 20px;">🎬 {title}</strong><br>
                🌐 <a href="{url}" target="_blank">Դիտել Տեսանյութը</a><br>
                🏷️ <em>Թեմա՝ {category}</em>
            </div>
            """, unsafe_allow_html=True)

        with right:
            SingleVideoCard(title, url)

    elif page == "Մեր Մասին":
        st.title("Մեր Մասին")

        st.subheader("🎯 Մեր Առաքելությունը")
        st.write(
            "At the Philosophy Portal, we strive to make philosophical discourse "
            "accessible, inclusive, and vibrant. We connect thinkers from around the world "
            "to explore timeless questions and contemporary issues."
        )

        # Team Profiles
        team_html = """
        ## 👤 Ծանոթացեք Մեր Թիմին 
        <div style='height:20px;'></div> 

        <div style="font-size: 1.05rem;">  <!-- Adjusted font size -->
            <div style="display:flex; flex-wrap: wrap; gap:2rem;">
                <div style="flex: 1 1 200px; text-align:center;">
                    <img src="https://your-cdn.com/you.jpg" alt="Your Name" 
                        style="width:120px;border-radius:50%;"/>
                    <p><strong style="font-size: 1.15rem;">Գեորգի Գունդակչյան</strong><br/>
                    Data Scientist & Lead Developer</p>
                    <p>✉️ <a href="mailto:georgi_gundakchyan@edu.aua.am">georgi_gundakchyan@edu.aua.am</a><br/>
                    📞 +374 99830003<br/>
                    🔗 <a href="https://linkedin.com/in/yourprofile" target="_blank">LinkedIn</a></p>
                </div>
                <div style="flex: 1 1 200px; text-align:center;">
                    <img src="https://your-cdn.com/cofounder.jpg" alt="Co-founder" 
                        style="width:120px;border-radius:50%;"/>
                    <p><strong style="font-size: 1.15rem;">Հայկ Ալեքյան</strong><br/>
                    Philosophy Enthusiast & Community Manager</p>
                    <p>✉️ <a href="mailto:hayk_alekyan@edu.aua.am">hayk_alekyan@edu.aua.am</a><br/>
                    📞 +374 98980098<br/>
                    🔗 <a href="https://twitter.com/cofounder" target="_blank">Twitter</a></p>
                </div>
                <div style="flex: 1 1 200px; text-align:center;">
                    <img src="https://your-cdn.com/cofounder.jpg" alt="Co-founder" 
                        style="width:120px;border-radius:50%;"/>
                    <p><strong style="font-size: 1.15rem;">Կարո Խաչատրյան</strong><br/>
                    Philosophy Enthusiast & Community Manager</p>
                    <p>✉️ <a href="mailto:karo_khachatryan@edu.aua.am">karo_khachatryan@edu.aua.am</a><br/>
                    📞 +374 55540022<br/>
                    🔗 <a href="https://twitter.com/cofounder" target="_blank">Twitter</a></p>
                </div>
            </div>
        </div>
        """
        st.markdown(team_html, unsafe_allow_html=True)
        st.markdown("---")

    # Forum
    elif page == "Ֆորում":
        st.title("🗣️ Ֆորում Հարթակ")
        st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)  # Vertical space

        RequireLogin()

        user_email = st.session_state.user["email"]

        name = user_email.split("@")[0]  
        st.title(f"Մուտք գործեցիք որպես {name}:")

        title = st.text_input("📝 Վերնագիր")
        content = st.text_area("💬 Բովանդակություն")


        if st.button("Հրապարակել Գրառումը"):
            if title and content:
                post = {
                    "id": int(datetime.now().timestamp()*1000),
                    "name": name,
                    "title": title,
                    "content": content,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                add_post(post)
                st.success("Հրապարակված է:")
            else:
                st.error("Խնդրում ենք լրացնել և վերնագիրը, և բովանդակությունը:")

        st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)  # Vertical space
        st.subheader("📚 Բոլոր Հրապարակումները")
        all_posts = get_posts()
        filtered = all_posts
        if filtered:
            for p in filtered:
                st.markdown(f"#### {p['title']}")
                st.write(p["content"])
                st.caption(f"{p['name']}-ի կողմից: {p['time']}")
                st.markdown("---")
        else:
            st.info("Հրապարակումներ չեն գտնվել:")
            
            for p in get_posts():
                st.markdown(f"#### {p['title']}")
                st.write(p["content"])
                st.caption(f"By {p['name']} at {p['time']}")
                st.markdown("---")

        sorted_posts = sorted(
            get_posts(),
            key=lambda x: datetime.strptime(x["time"], "%Y-%m-%d %H:%M:%S"),
            reverse=True,
        )

        st.subheader("📰 Պատասխանել Հրապարակմանը")

        for post in sorted_posts:
            st.markdown(f"**{post['title']}**")
            st.markdown(f"*{post['name']} | {post['time']}*")
            st.markdown(post["content"])

            if "replies" in post:
                for reply in post["replies"]:
                    st.markdown(f"> 💬 **{reply['name']}**: {reply['content']}")

            # 👇 Moved inside the loop
            reply_content = st.text_input(f"Պատասխանել {post['name']}-ին", key=f"reply_{post['id']}")
            if st.button("Պատասխանել", key=f"reply_btn_{post['id']}"):
                if name and reply_content:
                    reply = {
                        "name": name,
                        "content": reply_content,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    add_post(reply, reply_to_id=post["id"])
                    st.success("✅ Պատասխանը հաջողությամբ հրապարակվել է։")



    # Quotes
    elif page == "Մտքեր": 
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
            author_filter = st.selectbox("Փնտրել ըստ հեղինակի", ["Բոլորը"] + authors)
        with col2:
            show_favs = st.checkbox("Իմ Հավանածները")

        # Fetch current favorites once
        favorites = get_favorites_for_user(user_uid)

        # Filter quotes
        def matches(q):
            return (
                (author_filter == "Բոլորը" or q["author"] == author_filter)
                and (not show_favs or quote_id(q) in favorites)
            )

        filtered = [q for q in quotes if matches(q)]
        st.write(f"Ցուցադրվում են {len(filtered)} խոսքեր")

        # Render each, passing in the same `favorites` set
        for q in filtered:
            DisplayQuoteCard(q, user_uid, favorites)


    # Տեսադարան
    elif page == "Տեսադարան":
        st.title("🎥 Տեսանյութեր և Ռեպորտաժներ")
        st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)  # Vertical space

        videos = [
            (
                "Understanding Nietzsche: Philosophy in Modern Times",
                "https://www.youtube.com/watch?v=fLJBzhcSWTk",
                "Փիլիսոփայություն"
            ),  
            (   
                "The Case for Idealism: Truth, Facts, and Existence",
                "https://www.youtube.com/watch?v=7quW8AlngH0&ab_channel=NathanHawkins",
                "Փիլիսոփայություն"
            ),
            (
                "OSHO: Nobody Allows Anybody to Be Just Himself",
                "https://www.youtube.com/watch?v=UngV-qwNkW0&ab_channel=OSHOInternational",
                "Ինդիվիդուալիզմ"
            ),
            (
                "We’re wired for conformity. That’s why we have to practice dissent. Todd Rose for Big Think",
                "https://www.youtube.com/watch?v=rd8VHbIYqRs&ab_channel=BigThink",
                "Հոգեբանություն"
            ),
            (
                "Nietzsche - Follow No One, Trust Yourself",
                "https://www.youtube.com/watch?v=e-k7b8Zmh70&ab_channel=FreedominThought",
                "Ինդիվիդուալիզմ"
            ),
            (
                "Existentialism Explained: Key Concepts of Jean-Paul Sartre",
                "https://www.youtube.com/watch?v=VtP-N9pqoKk",
                "Էքզիստենցիալիզմ"
            ),  
            (
                "The Philosophy of Absurdism: Albert Camus and the Absurd",
                "https://www.youtube.com/watch?v=DTRJx1d4eks",
                "Աբսուրդիզմ"
            ),  
            (
                "Nietzsche’s Will to Power: An In-depth Analysis",
                "https://www.youtube.com/watch?v=bb7Q8Wu1HNA",
                "Ինդիվիդուալիզմ"
            ),  
            (
                "Heidegger and Being: Exploring the Concept of Being",
                "https://www.youtube.com/watch?v=0-yvwlKTTbk",
                "Էքզիստենցիալիզմ"
            )]
        all_categories = sorted(set([v[2] for v in videos]))
        st.markdown("<div style='font-size:18px; font-weight:600;'>🔍 Ընտրել թեման</div>", unsafe_allow_html=True)
        selected_category = st.selectbox("", ["Բոլորը"] + all_categories)

        # Filter based on category
        if selected_category != "Բոլորը":
            filtered_videos = [v for v in videos if v[2] == selected_category]
        else:
            filtered_videos = videos

        # render in 2-column grid
        for i in range(0, len(filtered_videos), 2):
            cols = st.columns(2, gap="large")
            for col, (title, url, category) in zip(cols, filtered_videos[i:i+2]):
                with col:
                    VideoCard(title, url)

    # Resources
    elif page == "Գիտադարան":
        st.title("Բարի Գալուստ Գիտադարան")
        st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)  # Vertical space
        resource_dir = Path("resources")
        if not resource_dir.exists():
            st.info("Ֆայլերը չեն գնտվել:")
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
                        st.markdown(f"<span style='font-size:20px;'>{icon} {name}</span>", unsafe_allow_html=True)
                        # st.write(f"{icon} **{name}**")
                    with col2:
                        if not st.session_state[f"view_{name}"]:
                            if st.button("Դիտել", key=f"btn_view_{name}"):
                                st.session_state[f"view_{name}"] = True
                    with col3:
                        data = path_obj.read_bytes()
                        st.download_button(label="Ներբեռնել", data=data, file_name=name, key=f"btn_down_{name}")

                    # Show preview if flagged
                    if st.session_state[f"view_{name}"]:
                        with st.expander(f"Նախադիտում: {name}", expanded=True):
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
                                    st.text_area("Փաստաթղթի Նախադիոտւմ", text, height=300)
                                except ImportError:
                                    st.warning("Install python-docx to preview DOCX files.")
                            # Close button
                            if st.button("Փակել", key=f"btn_close_{name}"):
                                st.session_state[f"view_{name}"] = False
                else:
                    st.error(f"Ֆայլերը չեն գտնվել: {name}")

if __name__ == "__main__":
    main() 