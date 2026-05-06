import streamlit as st
import grpc
import html
import os
import sys
from pathlib import Path

# Add project root to sys.path to import generated grpc files
sys.path.append(str(Path(__file__).parent.parent.parent))

from src import plagiarism_pb2
from src import plagiarism_pb2_grpc

# Configuration
GRPC_SERVER = os.getenv("GRPC_SERVER", "localhost:50051")

st.set_page_config(
    page_title="AI Plagiarism Detector",
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


def format_severity(severity: int) -> str:
    return plagiarism_pb2.Severity.Name(severity).title()


def main():
    st.title("AI Plagiarism Detection System")
    st.markdown("---")

    stub = get_grpc_stub()

    # Sidebar - System Status
    with st.sidebar:
        st.header("System Control")
        if st.button("Refresh System Status"):
            try:
                health = stub.HealthCheck(plagiarism_pb2.HealthCheckRequest(), timeout=5)
                if health.healthy:
                    st.success("System online")
                else:
                    st.warning("System responded, but one or more services are not healthy")
                for key, val in health.details.items():
                    st.write(f"**{key.capitalize()}:** {val}")
            except Exception as e:
                st.error(f"Connection failed: {e}")
        
        st.markdown("---")
        st.info("Project: End-to-End Plagiarism Detection with RAG & gRPC")

    # Tabs for different functionalities
    tab_check, tab_upload, tab_stats = st.tabs(["Check Plagiarism", "Library Manager", "Statistics"])

    with tab_check:
        st.subheader("Content Analysis")
        col1, col2 = st.columns([2, 1])

        with col1:
            input_text = st.text_area("Enter text to check:", height=300, placeholder="Paste your content here...")
            
            with st.expander("Advanced Options"):
                sim_threshold = st.slider("Similarity Threshold", 0.0, 1.0, 0.5)
                top_k = st.number_input("Maximum Matches", min_value=1, max_value=50, value=10)
                include_ai = st.checkbox("Include AI Deep Analysis", value=True)

            if st.button("Run Plagiarism Check", type="primary"):
                if not input_text.strip():
                    st.warning("Please enter some text.")
                else:
                    with st.spinner("Analyzing content & searching database..."):
                        try:
                            request = plagiarism_pb2.CheckRequest(
                                text=input_text,
                                options=plagiarism_pb2.CheckOptions(
                                    min_similarity=sim_threshold,
                                    top_k=top_k,
                                    include_ai_analysis=include_ai
                                )
                            )
                            response = stub.CheckPlagiarism(request, timeout=60)
                            
                            # Display Result Summary
                            st.markdown("### Analysis Results")
                            m1, m2, m3 = st.columns(3)
                            
                            m1.metric("Plagiarism Score", f"{response.plagiarism_percentage:.2f}%")
                            m2.metric("Severity", format_severity(response.severity))
                            m3.metric("Matches Found", len(response.matches))

                            if response.explanation:
                                st.info(f"**AI Insight:** {response.explanation}")

                            # Detailed Matches
                            if response.matches:
                                st.markdown("#### Top Matches Found")
                                for match in response.matches:
                                    title = html.escape(match.document_title or "Untitled source")
                                    matched_text = html.escape(match.matched_text)
                                    with st.container():
                                        st.markdown(f"""
                                        <div class="highlight-box">
                                            <strong>Source:</strong> {title} <br/>
                                            <strong>Similarity:</strong> {match.similarity_score:.2f} <br/>
                                            <p style="margin-top:10px"><em>"...{matched_text}..."</em></p>
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
        st.subheader("Document Indexing")
        st.write("Index reference documents that already exist in the MinIO bucket.")
        
        up_col1, _ = st.columns(2)
        
        with up_col1:
            object_path = st.text_input("MinIO object path", placeholder="example.pdf")
            title = st.text_input("Document title", placeholder="Optional")
            language = st.selectbox("Document Language", ["vi", "en"])
            
            if st.button("Index Document"):
                if object_path.strip():
                    try:
                        req = plagiarism_pb2.IndexDocumentFromMinioRequest(
                            bucket_name="plagiarism-docs",
                            object_path=object_path.strip(),
                            title=title.strip(),
                            language=language
                        )
                        res = stub.IndexPdfFromMinio(req, timeout=120)
                        if res.success:
                            st.success(f"Successfully indexed: {res.title}")
                            st.write(f"Chunks created: {len(res.chunks)}")
                        else:
                            st.error(f"Failed: {res.message}")
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.error("Please enter a MinIO object path.")

    with tab_stats:
        st.subheader("Database Statistics")
        try:
            health = stub.HealthCheck(plagiarism_pb2.HealthCheckRequest(), timeout=5)
            search = stub.SearchDocuments(plagiarism_pb2.SearchRequest(limit=5), timeout=10)

            col_s1, col_s2 = st.columns(2)
            col_s1.metric("Service Health", "Healthy" if health.healthy else "Degraded")
            col_s2.metric("Total Documents", search.total)

            if search.documents:
                st.markdown("#### Recent Documents")
                rows = [
                    {
                        "Title": doc.title,
                        "Language": doc.language,
                        "Chunks": doc.chunk_count,
                        "Created At": doc.created_at,
                    }
                    for doc in search.documents
                ]
                st.dataframe(rows, use_container_width=True, hide_index=True)
            else:
                st.info("No documents found.")
        except Exception as e:
            st.error(f"Could not fetch statistics: {e}")

if __name__ == "__main__":
    main()
