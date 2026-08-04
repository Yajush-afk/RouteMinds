# ML V2 Manifests

Small ML V2 manifests are tracked here. Model JSON, Parquet encodings, datasets,
and full metric reports remain ignored because they are generated artifacts.

A tracked manifest records the model version, schema, dataset hash, package
versions, checksums, split dates, feature order, promotion status, and local
artifact paths. A manifest is not proof of promotion; check
`promotion_eligible` and `promotion_blockers` before backend activation.
