import streamlit as st
import requests
import time
import math

# ================= 1. PAGE CONFIG & PREVIEW HACK =================
st.set_page_config(
    page_title="Reel View Tracker",
    page_icon="page_icon.png",  # Browser tab icon
    layout="centered"
)

# === THE SOCIAL PREVIEW HACK ===
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    try:
        st.image("page_icon.png", use_container_width=True)
    except Exception:
        # Fail silently if icon isn't there, or just show a warning
        # st.warning("⚠️ 'page_icon.png' not found in root folder.")
        pass

# ================= 2. CONFIGURATION & FUNCTIONS =================
try:
    # Ensure these are set in your .streamlit/secrets.toml file
    IG_USER_ID = st.secrets["IG_USER_ID"]
    ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]
except FileNotFoundError:
    st.error("Secrets not found! Please configure .streamlit/secrets.toml")
    st.stop()
except KeyError as e:
    st.error(f"Missing secret keys: {e}. Check your secrets.toml.")
    st.stop()

def make_business_discovery_request(user_id, target_username, token, cursor=None):
    """Fetches public data via Business Discovery API."""
    api_url = f"https://graph.facebook.com/v24.0/{user_id}"
    after_param = f".after({cursor})" if cursor else ""
    
    # UPDATED: Added 'thumbnail_url' to the requested fields
    fields_query = (
        f"business_discovery.username({target_username})"
        f"{{media.limit(25){after_param}{{id,timestamp,caption,media_type,view_count,like_count,permalink,thumbnail_url}}}}"
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
        # Initialize variables
        grand_total = 0
        count_posts = 0
        found_target = False
        next_cursor = None
        has_next_page = True
        scanned_reels = []
        clean_target = target_url.split('?')[0]
        
        # Wrap the calculation in a spinner instead of the active status box
        with st.spinner("Fetching data and calculating views... please wait."):
            # --- LOOP START ---
            while has_next_page and not found_target:
                data = make_business_discovery_request(IG_USER_ID, ig_username, ACCESS_TOKEN, next_cursor)
                
                if 'error' in data:
                    st.error(f"API Error: {data['error'].get('message')}")
                    break
                    
                try:
                    media_list = data.get('business_discovery', {}).get('media', {})
                    posts = media_list.get('data', [])
                    paging = media_list.get('paging', {})
                except AttributeError:
                    st.error("Could not parse data. Check username.")
                    break

                for post in posts:
                    clean_permalink = post.get('permalink', '').split('?')[0]
                    
                    # STOP CONDITION
                    if clean_target in clean_permalink:
                        found_target = True
                        # Scanning stops here
                        break
                    
                    # COUNTING LOGIC
                    if post.get('media_type') == 'VIDEO':
                        views = post.get('view_count', 0)
                        likes = post.get('like_count', 0)
                        # Get thumbnail URL (some older reels might not have it readily available)
                        thumb_url = post.get('thumbnail_url')

                        grand_total += views
                        count_posts += 1
                        
                        # Store data for display later
                        scanned_reels.append({
                            "Date": post.get('timestamp')[:10],
                            "Views": views,
                            "Likes": likes,
                            "Caption": post.get('caption', 'No Caption'),
                            "Link": post.get('permalink'),
                            "Thumbnail": thumb_url
                        })
                        
                # PAGINATION
                if not found_target:
                    if 'cursors' in paging and 'after' in paging['cursors']:
                        next_cursor = paging['cursors']['after']
                        time.sleep(0.1) # Small politeness delay
                    else:
                        has_next_page = False
                        # End of feed reached without finding target

        # --- FINAL DISPLAY (After spinner finishes) ---
        st.divider()
        
        if scanned_reels:
            # 1. BIG METRIC
            st.markdown(f"<h1 style='text-align: center; font-size: 80px; color: #4CAF50;'>{grand_total:,}</h1>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; color: grey;'>Total Views across {count_posts} Reels</p>", unsafe_allow_html=True)
            
            st.divider()
            
            # 2. THUMBNAIL GRID DISPLAY
            st.subheader(f"🎞️ Reels Included in Count ({count_posts})")
            
            # Grid Configuration
            cols_per_row = 3
            num_rows = math.ceil(len(scanned_reels) / cols_per_row)
            
            reel_index = 0
            for _ in range(num_rows):
                cols = st.columns(cols_per_row)
                for col in cols:
                    if reel_index < len(scanned_reels):
                        reel = scanned_reels[reel_index]
                        with col:
                            st.container(border=True)
                            # Display Thumbnail if available
                            if reel['Thumbnail']:
                                st.image(reel['Thumbnail'], use_container_width=True)
                            else:
                                # Fallback if no thumbnail url returned
                                st.warning("No Preview")
                                
                            st.markdown(f"**👁️ {reel['Views']:,}**")
                            st.caption(f"📅 {reel['Date']}")
                            
                            with st.popover("Details"):
                                st.caption(reel['Caption'][:100] + "...")
                                st.markdown(f"❤️ Likes: {reel['Likes']:,}")
                                st.markdown(f"[Watch on Instagram]({reel['Link']})")
                        reel_index += 1
                    
        elif not found_target and count_posts == 0:
             st.warning("No reels found newer than the target URL, or the target URL is your most recent post.")
        elif found_target and count_posts == 0:
             st.info("The target URL is your latest reel. 0 views gained since then.")