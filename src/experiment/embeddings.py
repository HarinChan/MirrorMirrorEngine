from langchain_community.embeddings import OpenVINOEmbeddings

model_name = "qwen3-embedding-06b"
model_kwargs = {"device": "CPU"}
encode_kwargs = {"mean_pooling": True, "normalize_embeddings": True}

ov_embeddings = OpenVINOEmbeddings(model_name_or_path=model_name,
                                   model_kwargs=model_kwargs,
                                   encode_kwargs=encode_kwargs)

text = "This is a test document."

query_result = ov_embeddings.embed_query(text)

print(query_result[:3])