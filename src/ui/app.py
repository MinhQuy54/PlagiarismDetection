import streamlit as st
import grpc
import os
import sys
import pandas as pd
from pathlib import Path

# Add project root to sys.path to import generated grpc files
sys.path.append(str(Path(__file__).parent.parent.parent))

from src import plagiarism_pb2
from src import plagiarism_pb2_grpc

# Configuration
GRPC_SERVER = os.getenv("GRPC_SERVER", "localhost:50051")

st.set_page_config(
    page_title="AI Plagiarism Detector",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for a premium look
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stAlert {
        border-radius: 10px;
    }
    .status-card {
        padding: 20px;
        border-radius: 10px;
        background-color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .plagiarism-high {
        color: #dc3545;
        font-weight: bold;
    }
    .plagiarism-med {
        color: #fd7e14;
        font-weight: bold;
    }
    .plagiarism-low {
        color: #198754;
        font-weight: bold;
    }
    .highlight-box {
        padding: 15px;
        border-left: 5px solid #0d6efd;
        background-color: #e7f1ff;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_grpc_stub():
    channel = grpc.insecure_channel(GRPC_SERVER)
    return plagiarism_pb2_grpc.PlagiarismServiceStub(channel)

def main():
    st.title("🔍 AI Plagiarism Detection System")
    st.markdown("---")

    stub = get_grpc_stub()

    # Sidebar - System Status
    with st.sidebar:
        st.header("⚙️ System Control")
        if st.button("🔄 Refresh System Status"):
            try:
                health = stub.HealthCheck(plagiarism_pb2.HealthCheckRequest())
                st.success("✅ System Online")
                for key, val in health.details.items():
                    st.write(f"**{key.capitalize()}:** {val}")
            except Exception as e:
                st.error(f"❌ Connection Failed: {e}")
        
        st.markdown("---")
        st.info("Project: End-to-End Plagiarism Detection with RAG & gRPC")

    # Tabs for different functionalities
    tab_check, tab_upload, tab_stats = st.tabs(["🚀 Check Plagiarism", "📁 Library Manager", "📊 Statistics"])

    with tab_check:
        st.subheader("📝 Content Analysis")
        col1, col2 = st.columns([2, 1])

        with col1:
            input_text = st.text_area("Enter text to check:", height=300, placeholder="Paste your content here...")
            
            with st.expander("Advanced Options"):
                sim_threshold = st.slider("Similarity Threshold", 0.0, 1.0, 0.5)
                include_ai = st.checkbox("Include AI Deep Analysis", value=True)

            if st.button("🔍 Run Plagiarism Check", type="primary"):
                if not input_text.strip():
                    st.warning("Please enter some text.")
                else:
                    with st.spinner("Analyzing content & searching database..."):
                        try:
                            request = plagiarism_pb2.CheckRequest(
                                text=input_text,
                                options=plagiarism_pb2.DetectionOptions(
                                    min_similarity=sim_threshold,
                                    include_ai_analysis=include_ai
                                )
                            )
                            response = stub.CheckPlagiarism(request)
                            
                            # Display Result Summary
                            st.markdown("### 🎯 Analysis Results")
                            m1, m2, m3 = st.columns(3)
                            
                            color_class = "plagiarism-high" if response.plagiarism_percentage > 70 else "plagiarism-med" if response.plagiarism_percentage > 30 else "plagiarism-low"
                            
                            m1.metric("Plagiarism Score", f"{response.plagiarism_percentage}%")
                            m2.metric("Severity", response.severity)
                            m3.metric("Matches Found", len(response.matches))

                            if response.explanation:
                                st.info(f"**AI Insight:** {response.explanation}")

                            # Detailed Matches
                            if response.matches:
                                st.markdown("#### 🔗 Top Matches Found")
                                for i, match in enumerate(response.matches):
                                    with st.container():
                                        st.markdown(f"""
                                        <div class="highlight-box">
                                            <strong>Source:</strong> {match.document_title} <br/>
                                            <strong>Similarity:</strong> {match.similarity_score:.2f} <br/>
                                            <p style="margin-top:10px"><em>"...{match.matched_text}..."</em></p>
                                        </div>
                                        """, unsafe_allow_html=True)
                            else:
                                st.success("No significant plagiarism detected in database.")
                                
                        except Exception as e:
                            st.error(f"Error during analysis: {e}")

        with col2:
            st.markdown("#### How it works")
            st.write("""
            1. **Chunking**: Input is split into meaningful segments.
            2. **Vector Search**: Each segment is converted to a high-dimensional vector.
            3. **Similarity**: Compared against millions of indexed documents.
            4. **AI Verification**: LLM (Llama 3.2) validates context and intent.
            """)

    with tab_upload:
        st.subheader("📚 Document Indexing")
        st.write("Upload reference documents to the knowledge base.")
        
        up_col1, up_col2 = st.columns(2)
        
        with up_col1:
            uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
            language = st.selectbox("Document Language", ["vi", "en"])
            
            if st.button("📤 Upload & Index"):
                if uploaded_file:
                    st.warning("Note: Direct upload to MinIO needs to be implemented via backend. Using IndexPdfFromMinio for demo.")
                    st.info("For Demo: Ensure file exists in MinIO bucket 'plagiarism-docs'")
                    
                    try:
                        # Assuming the file is already in MinIO or we provide path
                        req = plagiarism_pb2.IndexDocumentFromMinioRequest(
                            bucket_name="plagiarism-docs",
                            object_path=uploaded_file.name,
                            language=language
                        )
                        res = stub.IndexPdfFromMinio(req)
                        if res.success:
                            st.success(f"Successfully indexed: {res.title}")
                            st.write(f"Chunks created: {len(res.chunks)}")
                        else:
                            st.error(f"Failed: {res.message}")
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.error("Please select a file.")

    with tab_stats:
        st.subheader("📈 Database Statistics")
        try:
            stats = stub.GetStats(plagiarism_pb2.StatsRequest())
            col_s1, col_s2, col_s3 = st.columns(3)
            col_s1.metric("Total Documents", stats.total_documents)
            col_s2.metric("Total Chunks", stats.total_chunks)
            col_s3.metric("Storage Used", f"{stats.storage_size_bytes / 1024 / 1024:.2f} MB")
        except Exception as e:
            st.write("Could not fetch statistics.")

if __name__ == "__main__":
    main()
