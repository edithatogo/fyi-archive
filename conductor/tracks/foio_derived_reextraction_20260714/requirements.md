# Requirements (MoSCoW)

| Priority | Requirement | Verification |
|---|---|---|
| Must | Preserve raw archive records and publish derived outputs separately. | Manifest immutability test. |
| Must | Pin source revision, FOI-O contract, NLP pipeline/model, and Hugging Face revision/digest. | Derived-manifest validation. |
| Must | Mark machine outputs as candidates and retain evidence spans and review state. | Dataset-card and schema checks. |
| Should | Produce baseline deltas for repeated extraction. | Delta report fixture. |
| Could | Add automated dataset-card generation. | Optional packaging test. |
| Won't | Capture network data or certify legal findings. | Boundary review. |
