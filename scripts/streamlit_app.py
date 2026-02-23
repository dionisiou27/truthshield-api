import streamlit as st
import json
from datetime import datetime

# Page config
st.set_page_config(
    page_title="TruthShield API Demo",
    page_icon="🛡️",
    layout="wide"
)

# Header
st.title("🛡️ TruthShield")
st.subheader("AI-powered fact-checking service for enterprises")

# Sidebar
st.sidebar.title("TruthShield Demo")
st.sidebar.write("**Protecting European Democracy Through German Innovation**")

# Main demo
col1, col2 = st.columns(2)

with col1:
    st.header("🔍 Content Analysis")
    
    # Input
    content_type = st.selectbox("Content Type", ["Social Media Post", "News Article", "Company Statement"])
    fake_news = st.text_area("Enter potential misinformation:", 
                            placeholder="e.g., BMW EVs explode in winter temperatures",
                            height=100)
    
    company = st.selectbox("Target Company", ["BMW", "Vodafone", "Bayer", "Siemens", "Mercedes-Benz"])
    
    if st.button("🚀 Analyze with TruthShield", type="primary"):
        if fake_news:
            with st.spinner("Analyzing content..."):
                # Simulate analysis
                import time
                time.sleep(2)
                
                # Store results in session state
                st.session_state.analysis_done = True
                st.session_state.fake_news = fake_news
                st.session_state.company = company

with col2:
    st.header("🤖 AI Response")
    
    if hasattr(st.session_state, 'analysis_done') and st.session_state.analysis_done:
        # Analysis Results
        st.success("✅ Analysis Complete!")
        
        # Confidence Score
        confidence = 95
        st.metric("Fake News Confidence", f"{confidence}%", "High Risk")
        
        # AI Character Response
        st.subheader(f"🤖 {st.session_state.company} TruthBot Response:")
        
        if st.session_state.company == "BMW":
            response = "BMW EVs explodieren bei Kälte? 😊 Ach komm, mein i4 übersteht -40°C Arktis-Tests! Hier die süßen Eisbär-Videos als Beweis 🐻‍❄️"
        elif st.session_state.company == "Vodafone":
            response = "5G Towers schädlich? Mein lieber Freund, das ist wissenschaftlich widerlegt. Hier die WHO-Studien! 📡🧬"
        else:
            response = f"{st.session_state.company} TruthBot: Das ist nicht korrekt! Hier sind die verifizierten Fakten..."
            
        st.info(response)
        
        # Impact Metrics
        st.subheader("📊 Projected Impact")
        col3, col4, col5 = st.columns(3)
        
        with col3:
            st.metric("Response Time", "30 min", "-48 hours vs traditional")
        with col4:
            st.metric("Crisis Cost Prevented", "€2.3M", "+100% vs no response")
        with col5:
            st.metric("Engagement Boost", "+89%", "Positive sentiment")

# Business Model Section
st.divider()
st.header("💼 Enterprise Solution")

col6, col7, col8 = st.columns(3)

with col6:
    st.subheader("🎯 Target Market")
    st.write("- DAX 40 companies")
    st.write("- Large Mittelstand")
    st.write("- EU expansion ready")
    st.write("- €150M TAM")

with col7:
    st.subheader("💰 Pricing")
    st.write("**Setup:** €50K per customer")
    st.write("**Monthly:** €25K per company")
    st.write("**Annual Value:** €350K")
    st.write("**ROI:** 30:1 LTV:CAC")

with col8:
    st.subheader("🚀 Competition")
    st.write("✅ Only AI fact-checking influencer")
    st.write("✅ German cultural optimization")
    st.write("✅ Enterprise B2B focus")
    st.write("✅ EU compliance by design")

# Footer
st.divider()
st.write("**TruthShield: German Engineering. European Values. Global Impact.**")
st.write("🔗 GitHub: https://github.com/dionisiou27/truthshield-api")
st.write("📧 Contact: contact@truthshield.eu")