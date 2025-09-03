"""
Convert CLIP text encoder to ONNX format for smaller deployment size.
This script extracts the text encoder from sentence-transformers CLIP and converts it to ONNX.
"""

from pathlib import Path

import onnxruntime as ort
import torch
from sentence_transformers import SentenceTransformer
from transformers import CLIPTokenizer


class CLIPTextEncoderWithProjection(torch.nn.Module):
    """Wrapper that includes both the text encoder and text projection"""

    def __init__(self, text_model, text_projection):
        super().__init__()
        self.text_model = text_model
        self.text_projection = text_projection

    def forward(self, input_ids, attention_mask):
        # Get the text embeddings from the text model
        outputs = self.text_model(input_ids=input_ids, attention_mask=attention_mask)
        last_hidden_state = outputs.last_hidden_state

        # Use the EOS token embedding (last non-padded token)
        # This matches how sentence-transformers processes CLIP embeddings
        eos_positions = attention_mask.sum(dim=1) - 1
        eos_embeddings = last_hidden_state[torch.arange(last_hidden_state.size(0)), eos_positions]

        # Apply text projection
        projected_embeddings = self.text_projection(eos_embeddings)

        return projected_embeddings


def convert_clip_to_onnx():
    """Convert CLIP text encoder to ONNX format"""

    # Create models directory
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)

    # Load the sentence-transformers CLIP model
    st_model = SentenceTransformer("clip-ViT-B-32")

    # Extract the text model and text projection from sentence-transformers
    clip_module = st_model._first_module()
    text_model = clip_module.model.text_model
    text_projection = clip_module.model.text_projection

    # Create the combined model
    combined_model = CLIPTextEncoderWithProjection(text_model, text_projection)
    combined_model.eval()

    # Get the tokenizer
    tokenizer = CLIPTokenizer.from_pretrained("openai/clip-vit-base-patch32")

    # Create dummy input for ONNX export
    dummy_text = "red and white stripes"
    inputs = tokenizer(dummy_text, return_tensors="pt", padding=True, truncation=True)

    # Export to ONNX
    onnx_path = models_dir / "clip-text-encoder.onnx"

    torch.onnx.export(
        combined_model,
        (inputs["input_ids"], inputs["attention_mask"]),
        onnx_path,
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=["input_ids", "attention_mask"],
        output_names=["text_embeddings"],
        dynamic_axes={
            "input_ids": {0: "batch_size", 1: "sequence_length"},
            "attention_mask": {0: "batch_size", 1: "sequence_length"},
            "text_embeddings": {0: "batch_size"},
        },
    )

    print(f"ONNX model saved to {onnx_path}")

    # Test the ONNX model
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])

    # Test with a sample input
    test_text = "red and white stripes"
    test_inputs = tokenizer(test_text, return_tensors="np", padding=True, truncation=True)

    outputs = session.run(
        None,
        {"input_ids": test_inputs["input_ids"], "attention_mask": test_inputs["attention_mask"]},
    )

    # Compare with sentence-transformers output
    st_embedding = st_model.encode([test_text])

    print("ONNX model test successful!")
    print(f"ONNX output shape: {outputs[0].shape}")
    print(f"Sentence-transformers output shape: {st_embedding.shape}")
    cosine_sim = torch.cosine_similarity(
        torch.from_numpy(outputs[0]), torch.from_numpy(st_embedding), dim=1
    ).item()
    print(f"Cosine similarity: {cosine_sim:.6f}")
    print(f"Model size: {onnx_path.stat().st_size / (1024 * 1024):.2f} MB")


if __name__ == "__main__":
    convert_clip_to_onnx()
