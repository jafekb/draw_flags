# Flag Search Backend

This is the backend for the flag search application, which uses CLIP embeddings to find similar flags based on text descriptions.

## File Structure

```
backend/
├── src/                    # Main application code
│   └── flag_searcher.py   # Core flag search functionality
├── scripts/               # Utility scripts
│   ├── convert_to_onnx.py        # Convert CLIP model to ONNX format
│   ├── debug_clip_processing.py  # Debug CLIP embedding processing
│   └── debug_model_structure.py  # Debug model structure
├── tests/                 # Test files
│   ├── test_flag_searcher.py     # Test flag searcher functionality
│   ├── test_onnx.py             # Test ONNX model
│   ├── convert_torch_to_numpy.py # Test torch to numpy conversion
│   └── speed_test_flag_searcher.py # Performance tests
├── common/               # Shared utilities
│   └── flag_data.py     # Flag data structures
├── models/               # ONNX models
│   └── clip-text-encoder.onnx
├── data/                 # Data files
├── main.py              # Main application entry point
└── pyproject.toml       # Project configuration
```

## Usage

### Running the application
```bash
uv run main.py
```

### Converting models to ONNX
```bash
uv run scripts/convert_to_onnx.py
```

### Running tests
```bash
uv run tests/test_flag_searcher.py
uv run tests/test_onnx.py
```

### Debugging
```bash
uv run scripts/debug_clip_processing.py
```

## Model Information

The application uses a CLIP text encoder converted to ONNX format for efficient inference. The ONNX model includes:
- CLIP text encoder
- EOS token selection
- Text projection layer

This ensures the ONNX model produces identical embeddings to the original sentence-transformers CLIP model. 