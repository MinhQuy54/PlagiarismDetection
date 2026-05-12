import streamlit as st
import grpc
import html
import os
import sys
import io
from pathlib import Path
from minio import Minio

# Add project root to sys.path to import generated grpc files
sys.path.append(str(Path(__file__).parent.parent.parent))

from src import plagiarism_pb2
from src import plagiarism_pb2_grpc

# Configuration
GRPC_SERVER = os.getenv("GRPC_SERVER", "localhost:50051")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET_NAME", "plagiarism-docs")

st.set_page_config(
    page_title="Antigravity | AI Plagiarism Detector",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for a premium look
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    .stApp {
        background: #fdfdfd;
    }

    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }

    .status-card {
        padding: 24px;
        border-radius: 16px;
        background-color: white;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
        border: 1px solid #edf2f7;
    }
    
    .metric-container {
        background: white;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        text-align: center;
    }

    .highlight-box {
        padding: 20px;
        border-left: 6px solid #4f46e5;
        background-color: #f8fafc;
        border-radius: 4px 12px 12px 4px;
        margin: 16px 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    .match-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    
    .severity-badge {
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
    }
    
    .severity-safe { background-color: #dcfce7; color: #166534; }
    .severity-low { background-color: #fef9c3; color: #854d0e; }
    .severity-medium { background-color: #ffedd5; color: #9a3412; }
    .severity-high { background-color: #fee2e2; color: #991b1b; }
    .severity-critical { background-color: #450a0a; color: #ffffff; }

    /* Custom Tooltip style for sliders */
    .stSlider label {
        font-weight: 600;
        color: #1e293b;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_grpc_stub():
    channel = grpc.insecure_channel(GRPC_SERVER)
    return plagiarism_pb2_grpc.PlagiarismServiceStub(channel)

@st.cache_resource
def get_minio_client():
    return Minio(
        MINIO_ENDPOINT.replace("http://", "").replace("https://", ""),
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False
    )

def format_severity(severity: int) -> str:
    return plagiarism_pb2.Severity.Name(severity).title()

def get_severity_class(severity: int) -> str:
    name = plagiarism_pb2.Severity.Name(severity).lower()
    return f"severity-{name}"

def main():
    st.title("AI Plagiarism Detection")
    st.caption("Enterprise-grade content integrity system powered by RAG and Llama 3.2")
    st.markdown("---")

    stub = get_grpc_stub()
    minio_client = get_minio_client()

    # Sidebar - System Status
    with st.sidebar:
        st.header("Control Center")
        
        with st.expander("System Health", expanded=True):
            if st.button("Verify Connectivity", use_container_width=True):
                try:
                    health = stub.HealthCheck(plagiarism_pb2.HealthCheckRequest(), timeout=5)
                    if health.healthy:
                        st.success("All systems operational")
                    else:
                        st.warning("Degraded performance detected")
                    for key, val in health.details.items():
                        st.write(f"**{key.capitalize()}:** {val}")
                except Exception as e:
                    st.error(f"Connection failed: {e}")
        
        st.markdown("---")
        st.markdown("### Parameter Guide")
        st.info("""
        **Similarity Threshold**
        Ngưỡng tối thiểu để coi là đạo văn. 
        - 0.0: Lấy tất cả kết quả.
        - 0.8: Chỉ lấy các đoạn giống >80%.
        
        **Maximum Matches**
        Số lượng nguồn đối chiếu tối đa sẽ hiển thị.
        """)

    # Tabs for different functionalities
    tab_check, tab_upload, tab_stats = st.tabs([
        "Check Content", 
        "Library Manager", 
        "Analytics"
    ])

    with tab_check:
        st.subheader("Analyze Document")
        
        col_input, col_info = st.columns([2, 1])
        
        with col_input:
            input_mode = st.radio("Input Method", ["Paste Text", "Upload File (PDF/TXT)"], horizontal=True)
            
            input_text = ""
            uploaded_file = None
            
            if input_mode == "Paste Text":
                input_text = st.text_area("Content to verify:", height=250, placeholder="Paste your content here...")
            else:
                uploaded_file = st.file_uploader("Drop your document here", type=["pdf", "txt"])
                if uploaded_file:
                    if uploaded_file.type == "text/plain":
                        input_text = str(uploaded_file.read(), "utf-8")
                    else:
                        st.info("PDF will be processed via gRPC service.")

            with st.expander("Advanced Analysis Settings"):
                c1, c2 = st.columns(2)
                with c1:
                    sim_threshold = st.slider(
                        "Similarity Threshold", 
                        0.0, 1.0, 0.5, 
                        help="Ngưỡng độ tương đồng tối thiểu để ghi nhận là đạo văn."
                    )
                with c2:
                    top_k = st.number_input(
                        "Maximum Matches", 
                        min_value=1, max_value=50, value=10,
                        help="Số lượng nguồn đối chiếu tối đa."
                    )
                include_ai = st.checkbox("Enable AI Deep Analysis (Llama 3.2)", value=True)

            if st.button("Run Analysis", type="primary", use_container_width=True):
                if not input_text.strip() and not uploaded_file:
                    st.warning("Please provide content to check.")
                else:
                    with st.spinner("Analyzing content & searching across indexed library..."):
                        try:
                            response = None
                            if uploaded_file and uploaded_file.type == "application/pdf":
                                # Upload to temporary bucket/path for analysis
                                temp_path = f"temp/{uploaded_file.name}"
                                minio_client.put_object(
                                    MINIO_BUCKET, temp_path, 
                                    io.BytesIO(uploaded_file.getvalue()), 
                                    length=len(uploaded_file.getvalue()),
                                    content_type=uploaded_file.type
                                )
                                
                                request = plagiarism_pb2.CheckDocumentFromMinioRequest(
                                    bucket_name=MINIO_BUCKET,
                                    object_path=temp_path,
                                    options=plagiarism_pb2.CheckOptions(
                                        min_similarity=sim_threshold,
                                        top_k=top_k,
                                        include_ai_analysis=include_ai
                                    )
                                )
                                response = stub.CheckPdfFromMinio(request, timeout=180)
                            else:
                                request = plagiarism_pb2.CheckRequest(
                                    text=input_text,
                                    options=plagiarism_pb2.CheckOptions(
                                        min_similarity=sim_threshold,
                                        top_k=top_k,
                                        include_ai_analysis=include_ai
                                    )
                                )
                                response = stub.CheckPlagiarism(request, timeout=120)
                            
                            if response:
                                # Display Result Summary
                                st.markdown("### Analysis Report")
                                m1, m2, m3 = st.columns(3)
                                
                                with m1:
                                    st.markdown(f'<div class="metric-container"><h5>Plagiarism Score</h5><h2 style="color:#4f46e5">{response.plagiarism_percentage:.1f}%</h2></div>', unsafe_allow_html=True)
                                with m2:
                                    sev_class = get_severity_class(response.severity)
                                    st.markdown(f'<div class="metric-container"><h5>Severity Level</h5><span class="severity-badge {sev_class}">{format_severity(response.severity)}</span></div>', unsafe_allow_html=True)
                                with m3:
                                    st.markdown(f'<div class="metric-container"><h5>Sources Found</h5><h2>{len(response.matches)}</h2></div>', unsafe_allow_html=True)

                                if response.explanation:
                                    st.markdown("#### 🤖 AI Summary")
                                    st.info(response.explanation)

                                # Detailed Matches
                                if response.matches:
                                    st.markdown("#### 🚩 Detailed Findings")
                                    for match in response.matches:
                                        title = html.escape(match.document_title or "Unknown Source")
                                        matched_text = html.escape(match.matched_text)
                                        with st.container():
                                            st.markdown(f"""
                                            <div class="highlight-box">
                                                <div class="match-header">
                                                    <strong>Source: {title}</strong>
                                                    <span style="color:#4f46e5; font-weight:bold">{match.similarity_score*100:.1f}% Match</span>
                                                </div>
                                                <p style="font-size:0.9rem; color:#475569; border-top: 1px solid #e2e8f0; padding-top:10px; margin-top:10px">
                                                    <em>"...{matched_text}..."</em>
                                                </p>
                                            </div>
                                            """, unsafe_allow_html=True)
                                else:
                                    st.success("✨ No significant plagiarism detected. Your content appears original!")
                                
                        except Exception as e:
                            st.error(f"Analysis failed: {e}")

        with col_info:
            st.markdown("#### Processing Pipeline")
            st.info("""
            1. **Intelligent Chunking**: Breaking text into semantic units.
            2. **Vector Embedding**: Mapping text to 768-dimensional space.
            3. **Similarity Search**: Scanning millions of records in Elasticsearch.
            4. **LLM Verification**: Final context check by Llama 3.2.
            """)
            
            st.warning("""
            **Note**: File upload supports PDF and TXT. PDF files are processed with OCR if necessary.
            """)

    with tab_upload:
        st.subheader("Library Indexing")
        st.write("Add documents to the reference library for future comparisons.")
        
        up_col1, up_col2 = st.columns([1, 1])
        
        with up_col1:
            st.markdown("#### Option 1: Direct Upload")
            new_file = st.file_uploader("Upload reference document", type=["pdf", "txt"], key="lib_upload")
            doc_title = st.text_input("Custom Title (Optional)", placeholder="Leave blank to use filename")
            lang = st.selectbox("Language", ["vi", "en"], index=0)
            
            if st.button("Index Document", use_container_width=True):
                if new_file:
                    with st.spinner("Uploading and indexing..."):
                        try:
                            # 1. Upload to MinIO
                            obj_name = f"library/{new_file.name}"
                            minio_client.put_object(
                                MINIO_BUCKET, obj_name,
                                io.BytesIO(new_file.getvalue()),
                                length=len(new_file.getvalue()),
                                content_type=new_file.type
                            )
                            
                            # 2. Call gRPC Indexing
                            req = plagiarism_pb2.IndexDocumentFromMinioRequest(
                                bucket_name=MINIO_BUCKET,
                                object_path=obj_name,
                                title=doc_title or new_file.name,
                                language=lang
                            )
                            res = stub.IndexPdfFromMinio(req, timeout=180)
                            
                            if res.success:
                                st.success(f"Indexed successfully: {res.title}")
                                st.balloons()
                            else:
                                st.error(f"Indexing failed: {res.message}")
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    st.warning("Please select a file first.")

        with up_col2:
            st.markdown("#### Option 2: MinIO Path")
            st.caption("Index documents already existing in your MinIO storage.")
            m_path = st.text_input("Object Path", placeholder="path/to/existing_file.pdf")
            m_title = st.text_input("Title", placeholder="Optional", key="m_title")
            
            if st.button(" Index from MinIO", use_container_width=True):
                if m_path:
                    try:
                        req = plagiarism_pb2.IndexDocumentFromMinioRequest(
                            bucket_name=MINIO_BUCKET,
                            object_path=m_path,
                            title=m_title,
                            language="vi"
                        )
                        res = stub.IndexPdfFromMinio(req, timeout=120)
                        if res.success:
                            st.success(f"Added: {res.title}")
                        else:
                            st.error(res.message)
                    except Exception as e:
                        st.error(f"Error: {e}")

    with tab_stats:
        st.subheader("System Analytics")
        try:
            health = stub.HealthCheck(plagiarism_pb2.HealthCheckRequest(), timeout=5)
            search = stub.SearchDocuments(plagiarism_pb2.SearchRequest(limit=10), timeout=10)

            c_s1, c_s2, c_s3 = st.columns(3)
            c_s1.metric("Server Health", "Online" if health.healthy else "Offline")
            c_s2.metric("Library Size", f"{search.total} docs")
            c_s3.metric("Backend", "Python gRPC")

            if search.documents:
                st.markdown("#### Recently Indexed Documents")
                rows = [
                    {
                        "Title": doc.title,
                        "Language": doc.language.upper(),
                        "Chunks": doc.chunk_count,
                        "Date Added": doc.created_at[:10],
                    }
                    for doc in search.documents
                ]
                st.dataframe(rows, use_container_width=True, hide_index=True)
            else:
                st.info("No documents in library yet.")
        except Exception as e:
            st.error(f"Failed to load analytics: {e}")

if __name__ == "__main__":
    main()
