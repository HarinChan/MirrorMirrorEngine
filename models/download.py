import huggingface_hub as hf_hub

model_id = "OpenVINO/DeepSeek-R1-Distill-Qwen-1.5B-int4-cw-ov"
model_path = "DeepSeek-R1-Distill-Qwen-1.5B-int4-cw-ov"

hf_hub.snapshot_download(model_id, local_dir=model_path)