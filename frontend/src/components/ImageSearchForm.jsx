import React, { useRef, useState } from "react";

// Downscale in the browser before uploading: it bounds the request size and the
// hosted VLM's token cost, and keeps any image decoding off the (tiny) backend. We
// re-encode to JPEG since uploads are photos/graphics, not something needing alpha.
const MAX_DIMENSION = 768;
const JPEG_QUALITY = 0.85;

const downscaleToDataUri = (file) =>
  new Promise((resolve, reject) => {
    const objectUrl = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(objectUrl);
      const scale = Math.min(
        1,
        MAX_DIMENSION / Math.max(img.width, img.height),
      );
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(img.width * scale));
      canvas.height = Math.max(1, Math.round(img.height * scale));
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      resolve(canvas.toDataURL("image/jpeg", JPEG_QUALITY));
    };
    img.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error("Could not read that image."));
    };
    img.src = objectUrl;
  });

const ImageSearchForm = ({ onSubmit, loading, error }) => {
  const [preview, setPreview] = useState(null);
  const inputRef = useRef(null);

  const handleChange = async (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    try {
      const dataUri = await downscaleToDataUri(file);
      setPreview(dataUri);
      await onSubmit(dataUri);
    } catch (err) {
      console.error("Image upload failed", err);
    }
  };

  return (
    <div className="image-search">
      <button
        type="button"
        className="description-submit"
        onClick={() => inputRef.current?.click()}
        disabled={loading}
      >
        {loading ? "Identifying…" : "Upload a flag photo"}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        onChange={handleChange}
        style={{ display: "none" }}
      />
      {preview && (
        <img
          className="image-search__preview"
          src={preview}
          alt="Upload preview"
        />
      )}
      {error && <p className="image-search__error">{error}</p>}
    </div>
  );
};

export default ImageSearchForm;
