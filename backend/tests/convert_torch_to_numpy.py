import torch
import numpy as np
import os

# Define the path to your .pt file and where you want to save the .npy file
# Adjust these paths if your 'data' directory is located elsewhere relative to your script
pt_file_path = "backend/data/national_flags/embeddings.pt"
npy_file_path = "backend/data/national_flags/embeddings.npy"

# Ensure the directory for the .npy file exists
os.makedirs(os.path.dirname(npy_file_path), exist_ok=True)

print(f"Loading {pt_file_path}...")
try:
    # Load the PyTorch tensor.
    # map_location='cpu' ensures the tensor is loaded onto CPU memory,
    # which is necessary before converting it to a NumPy array.
    # If your .pt file was saved with weights_only=True and contains a complex model state_dict,
    # you might need to adjust this loading logic based on how it was originally saved.
    # For a simple tensor of embeddings, this line should work.
    tensor_data = torch.load(pt_file_path, map_location='cpu')

    # Convert the PyTorch tensor to a NumPy array
    numpy_array = tensor_data.numpy()

    print(f"Saving to {npy_file_path}...")
    np.save(npy_file_path, numpy_array)
    print("Conversion complete! You can now use 'embeddings.npy'.")

except Exception as e:
    print(f"An error occurred during conversion: {e}")
    print("Please ensure 'embeddings.pt' contains a directly loadable PyTorch tensor.")
