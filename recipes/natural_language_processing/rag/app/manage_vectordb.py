from langchain_community.vectorstores import Chroma
from chromadb import HttpClient
from chromadb.config import Settings
import chromadb.utils.embedding_functions as embedding_functions
from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Milvus
from pymilvus import MilvusClient, connections, utility

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

import socket

def is_collector_running(host="localhost", port=4317):
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (socket.timeout, ConnectionRefusedError):
        return False

if is_collector_running("localhost", 4317):
    # OpenTelemetry configuration
    provider = TracerProvider()
    exporter = OTLPSpanExporter(endpoint="localhost:4317", insecure=True)
    span_processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(span_processor)
    print("OpenTelemetry initialized: sending traces to localhost:4317")
else:
    # Fallback to ConsoleSpanExporter (or no-op)
    provider = TracerProvider()
    span_processor = SimpleSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(span_processor)

tracer = trace.get_tracer(__name__)

class VectorDB:
    def __init__(self, vector_vendor, host, port, collection_name, embedding_model):
        self.vector_vendor = vector_vendor
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.embedding_model = embedding_model

    def connect(self):
        with tracer.start_as_current_span("connect_to_vector_db"):
            # Connection logic
            print(f"Connecting to {self.host}:{self.port}...")
            if self.vector_vendor == "chromadb":
                self.client = HttpClient(host=self.host,
                                         port=self.port,
                                         settings=Settings(allow_reset=True,))
            elif self.vector_vendor == "milvus":
                self.client = MilvusClient(uri=f"http://{self.host}:{self.port}")
            return self.client

    def populate_db(self, documents):
        with tracer.start_as_current_span("populate_vector_db") as span:
            # Logic to populate the VectorDB with vectors
            e = SentenceTransformerEmbeddings(model_name=self.embedding_model)
            span.set_attribute("vector_vendor", self.vector_vendor)
            print(f"Populating VectorDB with vectors...")
            if self.vector_vendor == "chromadb":
                embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=self.embedding_model)
                collection = self.client.get_or_create_collection(self.collection_name,
                                                                  embedding_function=embedding_func)
                if collection.count() < 1:
                    db = Chroma.from_documents(
                        documents=documents,
                        embedding=e,
                        collection_name=self.collection_name,
                        client=self.client
                    )
                    print("DB populated")
                else:
                    db = Chroma(client=self.client,
                                collection_name=self.collection_name,
                                embedding_function=e,
                                )
                    print("DB already populated")

            elif self.vector_vendor == "milvus":
                connections.connect(host=self.host, port=self.port)
                if not utility.has_collection(self.collection_name):
                    print("Populating VectorDB with vectors...")
                    db = Milvus.from_documents(
                        documents,
                        e,
                        collection_name=self.collection_name,
                        connection_args={"host": self.host, "port": self.port},
                    )
                    print("DB populated")
                else:
                    print("DB already populated")
                    db = Milvus(
                        e,
                        collection_name=self.collection_name,
                        connection_args={"host": self.host, "port": self.port},
                    )
            return db

    def clear_db(self):
        with tracer.start_as_current_span("clear_vector_db"):
            print(f"Clearing VectorDB...")
            try:
                if self.vector_vendor == "chromadb":
                    self.client.delete_collection(self.collection_name)
                elif self.vector_vendor == "milvus":
                    self.client.drop_collection(self.collection_name)
                print("Cleared DB")
            except Exception as e:
                print(f"Couldn't clear the collection: {e}")
