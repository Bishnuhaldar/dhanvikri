import streamlit as st
import requests
import json
import re
from typing import List, Dict
import base64

GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")
GITHUB_REPO  = st.secrets.get("GITHUB_REPO") or "Bishnuhaldar/dhanvikri"
GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH") or "main"
GITHUB_FILEPATH = st.secrets.get("GITHUB_FILEPATH") or "index.html"
GITHUB_API = "https://api.github.com"

if not GITHUB_TOKEN:
    st.error("GitHub token not found. Add GITHUB_TOKEN to Streamlit Secrets or set the GITHUB_TOKEN env var for local dev.")
    st.stop()
    

# Page configuration
st.set_page_config(
    page_title="Paddy Dealer Management",
    page_icon="🌾",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
    .dealer-card {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    </style>
""", unsafe_allow_html=True)

class GitHubManager:
    def __init__(self):
        self.headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.api_url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{GITHUB_FILEPATH}"
    
    def get_file(self):
        """Fetch the HTML file from GitHub"""
        try:
            response = requests.get(self.api_url, headers=self.headers, params={"ref": GITHUB_BRANCH})
            response.raise_for_status()
            content = base64.b64decode(response.json()['content']).decode('utf-8')
            sha = response.json()['sha']
            return content, sha
        except Exception as e:
            st.error(f"Error fetching file: {str(e)}")
            return None, None
    
    def update_file(self, content, sha, commit_message):
        """Update the HTML file on GitHub"""
        try:
            data = {
                "message": commit_message,
                "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'),
                "sha": sha,
                "branch": GITHUB_BRANCH
            }
            response = requests.put(self.api_url, headers=self.headers, json=data)
            response.raise_for_status()
            return True
        except Exception as e:
            st.error(f"Error updating file: {str(e)}")
            return False

class DataManager:
    @staticmethod
    def extract_dealers_data(html_content):
        """Extract dealers data from HTML"""
        try:
            # Find the dealersData array in the JavaScript
            pattern = r'const dealersData = (\[[\s\S]*?\]);'
            match = re.search(pattern, html_content)
            
            if match:
                dealers_str = match.group(1)
                # Clean up the JavaScript array to make it valid JSON
                dealers_str = re.sub(r'(\w+):', r'"\1":', dealers_str)  # Add quotes to keys
                dealers_str = re.sub(r'â‚¹', '₹', dealers_str)  # Fix rupee symbol
                dealers_str = re.sub(r'â­', '⭐', dealers_str)  # Fix star symbol
                dealers_str = re.sub(r'ðŸ"ž', '📞', dealers_str)  # Fix phone symbol
                
                dealers = json.loads(dealers_str)
                return dealers
            return []
        except Exception as e:
            st.error(f"Error extracting dealers data: {str(e)}")
            return []
    
    @staticmethod
    def extract_regions(html_content):
        """Extract regions from HTML"""
        try:
            pattern = r'<option value="(\w+)">\1</option>'
            matches = re.findall(pattern, html_content)
            return [m for m in matches if m]
        except Exception as e:
            st.error(f"Error extracting regions: {str(e)}")
            return []
    
    @staticmethod
    def update_dealers_in_html(html_content, dealers_data):
        """Update dealers data in HTML content"""
        try:
            # Convert dealers data to JavaScript format
            dealers_js = json.dumps(dealers_data, indent=12, ensure_ascii=False)
            
            # Replace the dealersData array
            pattern = r'const dealersData = \[[\s\S]*?\];'
            new_data = f'const dealersData = {dealers_js};'
            updated_html = re.sub(pattern, new_data, html_content)
            
            return updated_html
        except Exception as e:
            st.error(f"Error updating dealers in HTML: {str(e)}")
            return html_content
    
    @staticmethod
    def update_regions_in_html(html_content, regions):
        """Update regions in HTML content"""
        try:
            # Create options HTML
            options = '\n                    '.join([
                '<option value="">-- Choose an area --</option>'
            ] + [
                f'<option value="{region}">{region}</option>' for region in sorted(regions)
            ])
            
            # Replace the select options
            pattern = r'<select class="area-select" id="areaSelect">[\s\S]*?</select>'
            new_select = f'<select class="area-select" id="areaSelect">\n                    {options}\n                </select>'
            updated_html = re.sub(pattern, new_select, html_content)
            
            return updated_html
        except Exception as e:
            st.error(f"Error updating regions in HTML: {str(e)}")
            return html_content

def main():
    st.title("🌾 Paddy Dealer Management System")
    st.markdown("---")
    
    # Initialize GitHub manager
    github_manager = GitHubManager()
    
    # Fetch current data
    if 'html_content' not in st.session_state or st.button("🔄 Refresh Data"):
        with st.spinner("Loading data from GitHub..."):
            html_content, sha = github_manager.get_file()
            if html_content:
                st.session_state.html_content = html_content
                st.session_state.sha = sha
                st.session_state.dealers = DataManager.extract_dealers_data(html_content)
                st.session_state.regions = DataManager.extract_regions(html_content)
            else:
                st.error("Failed to load data from GitHub")
                return
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["📋 Manage Dealers", "🗺️ Manage Regions", "📊 Overview"])
    
    # Tab 1: Manage Dealers
    with tab1:
        st.header("Dealer Management")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Current Dealers")
            
            # Display all dealers
            for idx, dealer in enumerate(st.session_state.dealers):
                with st.expander(f"{dealer['name']} - {dealer['rating']}", expanded=False):
                    st.write(f"**Contact:** {dealer['contact']}")
                    st.write(f"**Regions:** {', '.join(dealer['regions'])}")
                    st.write("**Paddy Types:**")
                    for paddy in dealer['paddyTypes']:
                        st.write(f"  - {paddy['name']}: {paddy['price']} {paddy['unit']}")
                    
                    col_edit, col_delete = st.columns(2)
                    with col_edit:
                        if st.button(f"✏️ Edit", key=f"edit_{idx}"):
                            st.session_state.editing_dealer = idx
                            st.rerun()
                    with col_delete:
                        if st.button(f"🗑️ Delete", key=f"delete_{idx}"):
                            st.session_state.dealers.pop(idx)
                            st.success(f"Dealer '{dealer['name']}' deleted!")
                            st.session_state.changes_made = True
        
        with col2:
            st.subheader("Add New Dealer")
            
            with st.form("add_dealer_form"):
                new_name = st.text_input("Dealer Name")
                new_contact = st.text_input("Contact", placeholder="📞 +91 XXXXX XXXXX")
                new_rating = st.text_input("Rating", placeholder="4.8 ⭐")
                new_regions = st.multiselect("Serving Regions", st.session_state.regions)
                
                st.write("**Paddy Types & Prices:**")
                num_paddy = st.number_input("Number of paddy types", min_value=1, max_value=10, value=3)
                
                paddy_types = []
                for i in range(num_paddy):
                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        paddy_name = st.text_input(f"Paddy {i+1} Name", key=f"paddy_name_{i}")
                    with col_p2:
                        paddy_price = st.text_input(f"Price", placeholder="₹2,500", key=f"paddy_price_{i}")
                    
                    if paddy_name and paddy_price:
                        paddy_types.append({
                            "name": paddy_name,
                            "price": paddy_price,
                            "unit": "per quintal"
                        })
                
                submit_add = st.form_submit_button("➕ Add Dealer")
                
                if submit_add:
                    if new_name and new_contact and new_rating and new_regions and paddy_types:
                        new_dealer = {
                            "name": new_name,
                            "contact": new_contact,
                            "rating": new_rating,
                            "regions": new_regions,
                            "paddyTypes": paddy_types
                        }
                        st.session_state.dealers.append(new_dealer)
                        st.success(f"✅ Dealer '{new_name}' added successfully!")
                        st.session_state.changes_made = True
                        st.rerun()
                    else:
                        st.error("Please fill all required fields!")
        
        # Edit dealer form
        if 'editing_dealer' in st.session_state:
            st.markdown("---")
            st.subheader("✏️ Edit Dealer")
            
            idx = st.session_state.editing_dealer
            dealer = st.session_state.dealers[idx]
            
            with st.form("edit_dealer_form"):
                edit_name = st.text_input("Dealer Name", value=dealer['name'])
                edit_contact = st.text_input("Contact", value=dealer['contact'])
                edit_rating = st.text_input("Rating", value=dealer['rating'])
                edit_regions = st.multiselect("Serving Regions", st.session_state.regions, 
                                             default=dealer['regions'])
                
                st.write("**Paddy Types & Prices:**")
                num_paddy_edit = st.number_input("Number of paddy types", min_value=1, max_value=10, 
                                                value=len(dealer['paddyTypes']))
                
                paddy_types_edit = []
                for i in range(num_paddy_edit):
                    col_p1, col_p2 = st.columns(2)
                    default_name = dealer['paddyTypes'][i]['name'] if i < len(dealer['paddyTypes']) else ""
                    default_price = dealer['paddyTypes'][i]['price'] if i < len(dealer['paddyTypes']) else ""
                    
                    with col_p1:
                        paddy_name = st.text_input(f"Paddy {i+1} Name", value=default_name, 
                                                  key=f"edit_paddy_name_{i}")
                    with col_p2:
                        paddy_price = st.text_input(f"Price", value=default_price, 
                                                   key=f"edit_paddy_price_{i}")
                    
                    if paddy_name and paddy_price:
                        paddy_types_edit.append({
                            "name": paddy_name,
                            "price": paddy_price,
                            "unit": "per quintal"
                        })
                
                col_save, col_cancel = st.columns(2)
                with col_save:
                    submit_edit = st.form_submit_button("💾 Save Changes")
                with col_cancel:
                    cancel_edit = st.form_submit_button("❌ Cancel")
                
                if submit_edit:
                    st.session_state.dealers[idx] = {
                        "name": edit_name,
                        "contact": edit_contact,
                        "rating": edit_rating,
                        "regions": edit_regions,
                        "paddyTypes": paddy_types_edit
                    }
                    st.success(f"✅ Dealer '{edit_name}' updated successfully!")
                    st.session_state.changes_made = True
                    del st.session_state.editing_dealer
                    st.rerun()
                
                if cancel_edit:
                    del st.session_state.editing_dealer
                    st.rerun()
    
    # Tab 2: Manage Regions
    with tab2:
        st.header("Region Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Current Regions")
            for region in sorted(st.session_state.regions):
                col_r1, col_r2 = st.columns([3, 1])
                with col_r1:
                    st.write(f"📍 {region}")
                with col_r2:
                    if st.button("🗑️", key=f"del_region_{region}"):
                        st.session_state.regions.remove(region)
                        st.success(f"Region '{region}' deleted!")
                        st.session_state.changes_made = True
                        st.rerun()
        
        with col2:
            st.subheader("Add New Region")
            new_region = st.text_input("Region Name")
            if st.button("➕ Add Region"):
                if new_region:
                    if new_region not in st.session_state.regions:
                        st.session_state.regions.append(new_region)
                        st.success(f"✅ Region '{new_region}' added!")
                        st.session_state.changes_made = True
                        st.rerun()
                    else:
                        st.warning("Region already exists!")
                else:
                    st.error("Please enter a region name!")
    
    # Tab 3: Overview
    with tab3:
        st.header("Overview")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Dealers", len(st.session_state.dealers))
        with col2:
            st.metric("Total Regions", len(st.session_state.regions))
        with col3:
            total_paddy_types = sum(len(d['paddyTypes']) for d in st.session_state.dealers)
            st.metric("Total Paddy Types", total_paddy_types)
        
        st.subheader("Dealers by Region")
        region_counts = {}
        for dealer in st.session_state.dealers:
            for region in dealer['regions']:
                region_counts[region] = region_counts.get(region, 0) + 1
        
        for region in sorted(region_counts.keys()):
            st.write(f"📍 **{region}**: {region_counts[region]} dealer(s)")
    
    # Save changes button
    st.markdown("---")
    if st.session_state.get('changes_made', False):
        st.warning("⚠️ You have unsaved changes!")
        
        commit_message = st.text_input("Commit Message", value="Update dealers data")
        
        if st.button("💾 Save Changes to GitHub", type="primary"):
            with st.spinner("Saving changes to GitHub..."):
                # Update HTML content
                updated_html = DataManager.update_dealers_in_html(
                    st.session_state.html_content, 
                    st.session_state.dealers
                )
                updated_html = DataManager.update_regions_in_html(
                    updated_html, 
                    st.session_state.regions
                )
                
                # Push to GitHub
                if github_manager.update_file(updated_html, st.session_state.sha, commit_message):
                    st.success("✅ Changes saved successfully to GitHub!")
                    st.balloons()
                    st.session_state.changes_made = False
                    st.session_state.html_content = updated_html
                else:
                    st.error("❌ Failed to save changes to GitHub!")

if __name__ == "__main__":
    main()
