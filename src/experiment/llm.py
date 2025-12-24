from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
from transformers import AutoTokenizer, pipeline
from optimum.intel.openvino import OVModelForCausalLM
from langchain_core.messages import SystemMessage, HumanMessage

MODEL_DIR = "qwen3-06bINT4_compressed_weights"

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)

model = OVModelForCausalLM.from_pretrained(
    MODEL_DIR,
    device="CPU"
)

gen_pipe = pipeline(
    task="text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=1024,
    do_sample=True,
    temperature=0.7,
    top_p=0.95,
    repetition_penalty=1.1,
    eos_token_id=tokenizer.eos_token_id
)

hf_llm = HuggingFacePipeline(pipeline=gen_pipe)
llm = ChatHuggingFace(llm=hf_llm)

if __name__ == "__main__":
    messages = [
        SystemMessage(content="You are a helpful assistance."),
        HumanMessage(content="Give me a brief history of programming languages.")
    ]

    resp = llm.invoke(messages)
    print(resp.content)