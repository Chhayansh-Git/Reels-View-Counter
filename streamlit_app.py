import streamlit as st
import requests
import time

# ================= 1. PAGE CONFIG & PREVIEW HACK =================
st.set_page_config(
    page_title="Reel View Tracker",
    page_icon="page_icon.png",  # Browser tab icon
    layout="centered"
)

# === THE SOCIAL PREVIEW HACK ===
# We place the logo at the top center so Streamlit's bot captures it as the preview image.
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    try:
        st.image("page_icon.png", use_container_width=True)
    except Exception:
        st.warning("⚠️ 'page_icon.png' not found in root folder.")

# ================= 2. CONFIGURATION & FUNCTIONS =================
try:
    IG_USER_ID = st.secrets["IG_USER_ID"]
    ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]
except FileNotFoundError:
    st.error("Secrets not found! Please configure .streamlit/secrets.toml")
    st.stop()

def make_business_discovery_request(user_id, target_username, token, cursor=None):
    """Fetches public data via Business Discovery API."""
    api_url = f"https://graph.facebook.com/v24.0/{user_id}"
    after_param = f".after({cursor})" if cursor else ""
    
    # We ask for 'view_count' specifically
    fields_query = (
        f"business_discovery.username({target_username})"
        f"{{media.limit(25){after_param}{{id,timestamp,caption,media_type,view_count,like_count,permalink}}}}"
    )
    
    params = {'fields': fields_query, 'access_token': token}
    response = requests.get(api_url, params=params)
    return response.json()

# ================= 3. SIDEBAR: ABOUT ME =================
with st.sidebar:
    try:
        st.image("page_icon.png", width=50)
    except:
        pass
    
    st.header("About the Developer")
    st.markdown("""
    **Hi, I'm Chhayansh.** 👋
    
    I'm a Computer Science student and software developer. I built this tool to solve a specific problem: **Instagram doesn't let you sum up views from a specific date.**
    
    This bot uses the Meta Graph API to legally fetch public view counts and do the math for you.
    """)
    
    st.divider()
    st.markdown("### 🔗 Connect")
    st.markdown("[GitHub Profile](https://github.com/)") # You can add your link
    st.markdown("[Instagram: @scene._.slayer](https://instagram.com/scene._.slayer)")

# ================= 4. MAIN INTERFACE =================
st.title("Reel View Calculator")
st.markdown("""
**Calculate your growth instantly.** Paste the link of a specific Reel, and this tool will sum up the views of **every Reel you posted after it**.
""")

# APP DESCRIPTION / INSTRUCTIONS
with st.expander("ℹ️ How does this work?"):
    st.markdown("""
    1. **Public Data Mode:** We use the 'Business Discovery' method to read public stats.
    2. **Why this works:** It bypasses the "0 views" bug on private insights by reading the public view count (just like a follower sees).
    3. **Accuracy:** It sums up the `view_count` field for every video found until the target.
    """)

st.divider()

# INPUT SECTION
col_input1, col_input2 = st.columns([1, 2])
with col_input1:
    ig_username = st.text_input("Username:", value="scene._.slayer", help="No @ symbol needed")
with col_input2:
    target_url = st.text_input("Stopping Point (Reel URL):", placeholder="https://www.instagram.com/reel/...")

# ================= 5. EXECUTION LOGIC =================
if st.button("🚀 Calculate Growth", type="primary", use_container_width=True):
    if not target_url or not ig_username:
        st.warning("⚠️ Please fill in both fields.")
    else:
        grand_total = 0
        count_posts = 0
        found_target = False
        next_cursor = None
        has_next_page = True
        
        # UI Elements for results
        status_box = st.status("Scanning your feed...", expanded=True)
        results_container = st.container()
        clean_target = target_url.split('?')[0]
        
        # List to store reel data for the summary table
        scanned_reels = []

        # --- LOOP START ---
        while has_next_page and not found_target:
            data = make_business_discovery_request(IG_USER_ID, ig_username, ACCESS_TOKEN, next_cursor)
            
            if 'error' in data:
                status_box.update(label="❌ API Error", state="error")
                st.error(data['error'].get('message'))
                break
                
            try:
                media_list = data.get('business_discovery', {}).get('media', {})
                posts = media_list.get('data', [])
                paging = media_list.get('paging', {})
            except AttributeError:
                status_box.update(label="❌ Data Error", state="error")
                st.error("Could not parse data. Check username.")
                break

            for post in posts:
                clean_permalink = post.get('permalink', '').split('?')[0]
                
                # STOP CONDITION
                if clean_target in clean_permalink:
                    found_target = True
                    status_box.update(label=f"✅ Found stopping point: {post.get('caption', '')[:20]}...", state="complete")
                    break
                
                # COUNTING LOGIC
                if post.get('media_type') == 'VIDEO':
                    views = post.get('view_count', 0)
                    likes = post.get('like_count', 0)
                    grand_total += views
                    count_posts += 1
                    
                    # Store for display
                    scanned_reels.append({
                        "Date": post.get('timestamp')[:10],
                        "Views": views,
                        "Likes": likes,
                        "Caption": post.get('caption', 'No Caption')[:40] + "...",
                        "Link": post.get('permalink')
                    })
                    
                    # Update status slightly
                    status_box.write(f"Scanned: {views:,} views ({post.get('timestamp')[:10]})")

            # PAGINATION
            if not found_target:
                if 'cursors' in paging and 'after' in paging['cursors']:
                    next_cursor = paging['cursors']['after']
                    time.sleep(0.1)
                else:
                    has_next_page = False
                    status_box.update(label="⚠️ End of Feed Reached", state="complete")

        # --- FINAL DISPLAY ---
        st.divider()
        
        if scanned_reels:
            # 1. BIG METRIC
            st.markdown(f"<h1 style='text-align: center; font-size: 80px; color: #4CAF50;'>{grand_total:,}</h1>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; color: grey;'>Total Views across {count_posts} Reels</p>", unsafe_allow_html=True)
            
            st.divider()
            
            # 2. DETAILED LIST
            st.subheader(f"📜 Reels Included in Count ({count_posts})")
            
            for reel in scanned_reels:
                with st.expander(f"👁️ {reel['Views']:,} | 📅 {reel['Date']}"):
                    st.write(f"**Caption:** {reel['Caption']}")
                    st.write(f"**Likes:** {reel['Likes']}")
                    st.markdown(f"[Watch on Instagram]({reel['Link']})")
                    
        elif not found_target and count_posts == 0:
             st.warning("No reels found or target URL is the most recent post.")