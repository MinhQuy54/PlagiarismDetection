"""gRPC Server for Plagiarism Detection Service."""

import gc, logging, sys, signal, grpc

from concurrent import futures

from src import  plagiarism_pb2_grpc
from src.config.settings import get_settings
from src.logger import LoggingInterceptor, init_file_logger, get_file_logger
from src.metrics import MetricsServer, MetricsInterceptor
from src.service.plagiarism_service import PlagiarismService
from src.storage.elasticsearch import get_es_client
from src.storage.minio_client import get_minio_client
from src.embedding.ollama_embed import get_ollama_client
from src.core.analyzer import get_analyzer


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__) 

class PlagiarismServer:
    """gRPC server for plagiarism detection."""
    
    def __init__(self):
        self.settings = get_settings()
        self.server = None
        self.metrics_server = None
        self._shutdown_event = False
        
    def setup_elasticsearch(self) -> bool:
        """Setup Elasticsearch connection."""
        try:
            es_client = get_es_client()
            
            health = es_client.health_check()
            if not health.get("healthy"):
                logger.error(f"Elasticsearch not healthy: {health}")
                return False

            logger.info(f"Connected to Elasticsearch: {health.get('cluster_name')}")
            
            # Create index if not exists
            es_client.create_index(force=False)
            logger.info(f"Elasticsearch index ready: {self.settings.es_index}")
            return True
        except Exception as e:
            logger.error(f"Failed to setup Elasticsearch: {e}")
            return False
        
    def start(self):
        """Start the gRPC server."""
        # Initialize file logger for JSON structured logging
        init_file_logger(
            service_name=self.settings.service_name,
            log_dir=self.settings.log_dir,
        )
        logger.info(f"JSON logs will be written to: {self.settings.log_dir}")
        
        # Start metrics server
        metrics_port = int(self.settings.metrics_port)
        self.metrics_server = MetricsServer(
            service_name=self.settings.service_name,
            port=metrics_port,
        )
        self.metrics_server.start()
        logger.info(f"Metrics server started on port {metrics_port}")
        
        # Setup elasticsearch
        
        if not self.setup_elasticsearch():
            logger.warning("Elasticsearch setup failed, continuing anyway...")
            
        # Create gRPC server with logging and metrics interceptors
        
        self.server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=self.settings.grpc_max_workers),
            interceptors=[
                LoggingInterceptor(),
                MetricsInterceptor(service_name=self.settings.service_name),
            ],
            options=[
                ("grpc.max_send_message_length", 50 * 1024 * 1024),  # 50MB
                ("grpc.max_receive_message_length", 50 * 1024 * 1024),  # 50MB
            ],
        )
        
        # Add servicer
        plagiarism_pb2_grpc.add_PlagiarismServiceServicer_to_server(
            PlagiarismService(), self.server
        )

        # Bind to address
        address = f"{self.settings.grpc_host}:{self.settings.grpc_port}"
        
        if self.settings.grpc_tls_enabled:
            # Load TLS credentials
            try:
                with open(self.settings.grpc_cert_path, 'rb') as f:
                    private_key = f.read()
                with open(self.settings.grpc_key_path, 'rb') as f:
                    certificate_chain = f.read()
                with open(self.settings.grpc_ca_path, 'rb') as f:
                    root_certificates = f.read()
                
                # Only load CA cert if client auth is required
                ca_cert = None
                if self.settings.grpc_require_client_cert:
                    with open(self.settings.grpc_ca_path, "rb") as f:
                        ca_cert = f.read()
                
                credentials = grpc.ssl_server_credentials(
                    [(private_key, certificate_chain)],
                    root_certificates=ca_cert,
                    require_client_auth=self.settings.grpc_require_client_cert,
                )
                self.server.add_secure_port(address, credentials)
                tls_mode = "mTLS" if self.settings.grpc_require_client_cert else "TLS"
                logger.info(f"🔒 {tls_mode} enabled - Plagiarism Detection Service started on {address}")
                
            except Exception as e:
                logger.error(f"Failed to load TLS certificates: {e}")
                logger.warning("Falling back to insecure connection")
                self.server.add_insecure_port(address)
                logger.info(f"🔓 Plagiarism Detection Service started on {address} (insecure)")
        else:
            self.server.add_insecure_port(address)
            logger.info(f"🔓 Plagiarism Detection Service started on {address}")

        # Start server
        self.server.start()

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Wait for shutdown
        try:
            self.server.wait_for_termination()
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        if self.server and not self._shutdown_event:
            self._shutdown_event = True
            logger.info("Shutting down gRPC server...")
            self.server.stop(0)
            self.server.wait_for_termination()
            logger.info("gRPC server stopped")
            
            # Stop metrics server
            if self.metrics_server:
                self.metrics_server.stop()
                logger.info("Metrics server stopped")
            
            # Close Elasticsearch connection
            es_client = get_es_client()
            es_client.close()
            logger.info("Elasticsearch connection closed")
            
            # Close MinIO client
            minio_client = get_minio_client()
            minio_client.close()
            logger.info("MinIO client closed")
            
            # Close Ollama client
            ollama_client = get_ollama_client()
            ollama_client.close()
            logger.info("Ollama client closed")
            
            # Close analyzer
            analyzer = get_analyzer()
            analyzer.close()
            logger.info("Analyzer closed")
            
            # Force garbage collection
            gc.collect()
            logger.info("Garbage collection completed")
            
            logger.info("All services stopped successfully")

    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)


def main():
    """Main entry point."""
    settings = get_settings()

    # Update log level
    logging.getLogger().setLevel(settings.log_level)

    logger.info("=" * 50)
    logger.info("Plagiarism Detection Service")
    logger.info("=" * 50)
    logger.info(f"Elasticsearch: {settings.es_url}")
    logger.info(f"Ollama: {settings.ollama_host}")
    logger.info(f"gRPC Port: {settings.grpc_port}")
    logger.info("=" * 50)

    server = PlagiarismServer()
    server.start()


if __name__ == "__main__":
    main()
            