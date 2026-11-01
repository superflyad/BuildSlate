# Supplier response evidence store

This directory is the controlled landing area for supplier-authored responses. Do not edit an ingested raw response. `python -m buildslate suppliers ingest` preserves the source bytes under `raw/<domain>/` and writes a hash-addressed receipt under `receipts/`.

An ingestion receipt means only that BuildSlate preserved and reviewed a document. It does not mean the supplier claim is verified, the component is selected, the response is approved for public disclosure, or the linked evidence package is complete.

Use `python -m buildslate suppliers queue --generate` to reproduce the review queue. Empty directories are represented by their README files until authorized supplier evidence exists.

