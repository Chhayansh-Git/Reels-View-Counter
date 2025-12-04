import streamlit as st
import requests
import time

# ================= CONFIGURATION =================
try:
    IG_USER_ID = st.secrets["IG_USER_ID"]
    ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]
except FileNotFoundError:
    st.error("Secrets not found! Please configure .streamlit/secrets.toml")
    st.stop()

# ================= CORE FUNCTIONS =================
def make_business_discovery_request(user_id, target_username, token, cursor=None):
    """
    Uses the Business Discovery API to fetch public data.
    """
    api_url = f"https://graph.facebook.com/v24.0/{user_id}"
    
    # Pagination cursor logic
    after_param = f".after({cursor})" if cursor else ""
    
    # CRITICAL FIX: We added 'view_count' to this list because your screenshot 
    # proved that is where the data is hiding.
    fields_query = (
        f"business_discovery.username({target_username})"
        f"{{media.limit(25){after_param}{{id,timestamp,caption,media_type,view_count,like_count,permalink}}}}"
    )
    
    params = {
        'fields': fields_query,
        'access_token': token
    }
    
    response = requests.get(api_url, params=params)
    return response.json()

# ================= UI LAYOUT =================
st.set_page_config(page_title="🎬Reel View Counter", page_icon="/Users/chhayanshporwal/Desktop/reel_bot/page_icon.png")

st.title("🎬Reel View Counter")
st.markdown("This version uses **Business Discovery** and reads the **'view_count'** field.")

# Inputs
ig_username = st.text_input("Your Instagram Username (without @):", value="scene._.slayer")
target_url = st.text_input("Paste 'Stopping Point' Reel URL:", placeholder="https://www.instagram.com/reel/...")

if st.button("Start Counting"):
    if not target_url or not ig_username:
        st.warning("⚠️ Please fill in both fields.")
        
    else:
        grand_total = 0
        count_posts = 0
        found_target = False
        next_cursor = None
        has_next_page = True
        
        # Container for live results
        result_box = st.container()
        status_text = st.empty()
        
        # Remove query params from target for clean matching
        clean_target = target_url.split('?')[0]
        
        while has_next_page and not found_target:
            status_text.info(f"Scanning... (Found {count_posts} reels so far)")
            
            data = make_business_discovery_request(IG_USER_ID, ig_username, ACCESS_TOKEN, next_cursor)
            
            if 'error' in data:
                st.error("API Error:")
                st.json(data['error'])
                break
                
            try:
                # Navigate the nested JSON response
                discovery = data.get('business_discovery', {})
                media_list = discovery.get('media', {})
                posts = media_list.get('data', [])
                paging = media_list.get('paging', {})
            except AttributeError:
                st.error("Could not parse data. Check username.")
                break

            for post in posts:
                # 1. Clean URL
                clean_permalink = post.get('permalink', '').split('?')[0]
                
                # 2. Check Stop Condition
                if clean_target in clean_permalink:
                    found_target = True
                    st.success(f"🛑 **Stopping Point Reached:** {post.get('caption', '')[:30]}...")
                    break
                
                # 3. Add Views
                if post.get('media_type') == 'VIDEO':
                    # THE FIX: We use 'view_count' because your inspector showed it has the data
                    views = post.get('view_count', 0)
                    
                    grand_total += views
                    count_posts += 1
                    
                    with result_box.expander(f"👁️ {views:,} | {post.get('timestamp')[:10]}"):
                        st.write(f"Link: {post.get('permalink')}")

            # Pagination Logic
            if not found_target:
                if 'cursors' in paging and 'after' in paging['cursors']:
                    next_cursor = paging['cursors']['after']
                    time.sleep(0.2) # Be nice to the API
                else:
                    has_next_page = False
        
        # Final Result
        status_text.empty()
        st.divider()
        
        if found_target:
            st.balloons()
            st.markdown(f"<h1 style='text-align: center; color: #4CAF50;'>Total Views: {grand_total:,}</h1>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center;'>Sum of the last <b>{count_posts}</b> reels.</p>", unsafe_allow_html=True)
        else:
            st.warning(f"⚠️ Target URL not found. We scanned {count_posts} posts.")
            st.info(f"Current Sum: {grand_total:,}")