# Reference Part Datasets

Each subfolder is one part class containing its reference images:

```
parts/
└── round_part/
    ├── reference_01.jpg
    ├── reference_02.jpg
    └── reference_03.jpg
```

- The active part is selected in `config/vision.yaml` (`active_part`).
- Supported formats: .jpg, .jpeg, .png, .bmp
- To switch the detection target: add a new folder with reference images and
  set `active_part` to its name. No code change is required.
