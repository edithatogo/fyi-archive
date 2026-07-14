# FOI-O capability consumer

`fyi-archive` consumes the published FOI-O capability declaration without a
runtime dependency on the FOI-O Python package. Declarations are validated at
the archive/derived-layer boundary and unknown contract versions reject by
default.

The consumer must preserve its existing immutable-manifest and Hugging Face
publication boundaries.
