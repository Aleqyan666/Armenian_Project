import streamlit as st
from streamlit_option_menu import option_menu
import json
import base64
import pandas as pd
from pathlib import Path
from datetime import datetime
import random
import urllib.parse


# 1) Page config (must be first Streamlit command)
st.set_page_config(page_title="Philosophy Portal", layout="wide")

# 2) Inject custom CSS for styling
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


# 3) JSON storage path
POSTS_FILE = Path("forum_posts.json")
if not POSTS_FILE.exists():
    POSTS_FILE.write_text("[]", encoding="utf-8")

# 4) Load / save helpers
def GetPosts():
    return json.loads(POSTS_FILE.read_text(encoding="utf-8"))

def SavePosts(posts):
    POSTS_FILE.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")

def GetQuotes(json_path: str = "quotes.json") -> list[dict]:
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback to an empty list if file is missing
        return []
    
def DisplayQuoteCard(quote: dict):
    card_html = f"""
    <div style="
        background-color: #f9f9f9;
        padding: 1.2em;
        margin-bottom: 1em;
        border-radius: 10px;
        box-shadow: 2px 2px 12px rgba(0, 0, 0, 0.1);
    ">
        <p style="font-size: 1.2em; font-style: italic;">"{quote['text']}"</p>
        <p style="text-align: right; font-weight: bold; margin-top: 1em;">– {quote['author']}</p>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

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
    # pages = ["Home", "About Us", "Forum", "Quotes", "Reportages", "Resources"]
    # page = st.sidebar.radio("Go to", pages)
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
        CATEGORIES = ["Ethics", "Metaphysics", "Logic", "Politics", "Aesthetics", "Other"]

        st.title("🏛️ Welcome to the Philosophy Portal")
        st.write("Explore thoughts, discussions, and ideas from the greatest minds and community voices.")

        posts = GetPosts()

        # 2. Key metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("📄 Total Posts", len(posts))
        col2.metric("👥 Registered Users", 0 )
                    # get_user_count())
        col3.metric("🏷️ Categories", len(CATEGORIES))

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

        # 6. Posts by Category Visualization
        st.subheader("📊 Posts by Category")
        if posts:
            cat_counts = pd.Series([p["category"] for p in posts]).value_counts()
            st.bar_chart(cat_counts)
        else:
            st.info("No posts yet to visualize.")

    elif page == "About Us":
        st.title("About Us")

        team_html = """
        ### 👤 Meet the Founders  
        <div style="display:flex; gap:2rem;">
        <div style="text-align:center;">
            <img src="https://your-cdn.com/you.jpg" alt="Your Name" style="width:120px;border-radius:50%;"/>
            <p><strong>Your Name</strong><br/>Data Scientist & Lead Developer</p>
        </div>
        <div style="text-align:center;">
            <img src="https://your-cdn.com/cofounder.jpg" alt="Co-founder" style="width:120px;border-radius:50%;"/>
            <p><strong>Co-Founder</strong><br/>Philosophy Enthusiast</p>
        </div>
        </div>
        """

        st.markdown(team_html, unsafe_allow_html=True)

    # Forum
    elif page == "Forum":
        st.title("🗣️ Forum")

        CATEGORIES = ["Ethics", "Metaphysics", "Logic", "Politics", "Aesthetics", "Other"]

        for key in ("name_input", "title_input", "content_input", "category_input"):
            if key not in st.session_state:
                st.session_state[key] = "" if key != "category_input" else CATEGORIES[0]

        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("👤 Your Name & Surname", key="name_input")
        with col2:
            title = st.text_input("📝 Topic Title", key="title_input")
        category = st.selectbox("📚 Select Category", CATEGORIES, key="category_input")
        content = st.text_area("💬 Share your thoughts...", key="content_input")

        if st.button("Submit"):
            if name and title and content:
                posts = GetPosts()  
                new_post = {
                    "id": int(datetime.now().timestamp() * 1000),
                    "name": name,
                    "title": title,
                    "content": content,
                    "category": category,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                posts.append(new_post)
                SavePosts(posts)    # your existing function to write posts JSON
                st.success("✅ Post submitted!")
                # Clear inputs
                st.session_state.update({
                    "name_input": "",
                    "title_input": "",
                    "content_input": "",
                    "category_input": CATEGORIES[0]
                })
                st.experimental_rerun()
            else:
                st.error("⚠️ Please fill in all fields before submitting.")

        # Display posts
        st.subheader("📚 Forum Posts")
        posts = GetPosts()
        if posts:
            for post in reversed(posts):
                with st.container():
                    st.markdown(f"#### 🧠 {post['title']}")
                    st.write(post["content"])
                    st.markdown(
                        f"<div style='font-size:0.9em; color:grey;'>"
                        f"📁 {post.get('category','Uncategorized')} &nbsp;|&nbsp; "
                        f"✍️ {post['name']} &nbsp;|&nbsp; ⏰ {post['time']}"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    st.markdown("<hr style='border:1px solid #e0e0e0;'>", unsafe_allow_html=True)
        else:
            st.info("No posts yet. Be the first to share your thoughts!")


    # Quotes
    elif page == "Quotes":
        st.title("Famous Philosophical Quotes")
        quotes = GetQuotes()

        for quote in quotes:
            DisplayQuoteCard(quote)
    # Reportages
    elif page == "Reportages":

        st.title("🎥 Reportages & Videos")

        videos = [
    (
        "Understanding Nietzsche: Philosophy in Modern Times",
        "https://www.youtube.com/watch?v=fLJBzhcSWTk"
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
                ("Բարուց և Չարից Անդին.pdf", resource_dir / "Բարուց և Չարից Անդին.pdf")
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