# Project Brief: Modular Python Vision System for Delta Robot Pick-and-Place

## 1. Objective

I want to develop a **modular Python-based computer vision system** that uses a live camera stream to identify parts, determine their positions in the image, count the number of detected parts, and provide their coordinates to a Delta robot pick-and-place system.

The system should be designed as a **real engineering project**, not as a single Python script.

The primary objective is:

> Capture a live camera stream → detect the required part(s) → determine how many parts are present → calculate their image coordinates → transform those coordinates into robot-compatible coordinates → provide structured pick targets to the robot/controller.

The parts are expected to be **stationary during detection**. The system should continuously process the camera stream and identify the relevant parts in the working area.

The system should also support changing the type of part that needs to be detected without modifying the core Python code.

For example:

- Initially, the system is configured to detect round parts.
- I provide reference/training images for the round part.
- The system detects round parts in the live camera feed.
- Later, I remove the round-part reference images and replace them with square-part reference images.
- The system should automatically use the new reference dataset/configuration to detect the square parts.

The architecture must therefore separate:

1. Camera acquisition
2. Image processing
3. Part detection
4. Part counting
5. Coordinate extraction
6. Coordinate transformation/calibration
7. Robot communication
8. Configuration
9. Reference-part datasets
10. Logging
11. Documentation

---

# 2. Important Development Principle

Do NOT immediately create a large monolithic implementation.

First:

1. Understand the requirements.
2. Ask clarification questions where required.
3. Propose the architecture.
4. Propose the folder/file structure.
5. Define the interfaces between modules.
6. Define the data structures exchanged between modules.
7. Define the milestones.
8. Create/update the documentation.
9. Only then implement the system incrementally.

The architecture should allow individual components to be replaced without rewriting the entire application.

For example, I should be able to replace:

- OpenCV detection with YOLO
- one camera with another camera
- image-based coordinates with calibrated coordinates
- Modbus communication with OPC UA
- one robot controller with another controller

without fundamentally restructuring the entire project.

---

# 3. Required Project Documentation Structure

Create a dedicated documentation folder:

```text
docs_camera/
```

This folder is mandatory.

It should contain documentation explaining the architecture, implementation, interfaces, configuration, development decisions, milestones, and changes.

At minimum, create:

```text
docs_camera/
│
├── README.md
├── ARCHITECTURE.md
├── DATA_FLOW.md
├── FILE_FUNCTION_REFERENCE.md
├── CONFIGURATION.md
├── CAMERA_INTEGRATION.md
├── VISION_PIPELINE.md
├── COORDINATE_SYSTEM.md
├── ROBOT_INTERFACE.md
├── AI_DEVELOPMENT_RULES.md
├── MILESTONES.md
├── CHANGELOG.md
└── TROUBLESHOOTING.md
```

If additional documentation is required, create it.

Do not create documentation unnecessarily. Each document should have a clear purpose.

---

# 4. Documentation Must Be Maintained

Documentation is part of the implementation.

Whenever a code change modifies:

- architecture
- file structure
- function behavior
- input/output data
- configuration
- camera handling
- detection logic
- coordinate transformation
- robot communication
- dependencies
- interfaces

the relevant `.md` files must also be updated.

Do not treat documentation as something that is written once and forgotten.

The documentation must always represent the current state of the project.

---

# 5. AI Development Rules

Create:

```text
docs_camera/AI_DEVELOPMENT_RULES.md
```

This file should act as the primary instruction/reference document for future AI coding tools working on this project.

It should explain rules such as:

### Architecture rules

- Keep modules independent.
- Avoid unnecessarily large files.
- Do not duplicate functionality.
- Do not put business logic inside camera drivers.
- Do not put robot communication logic inside image-processing functions.
- Use clearly defined interfaces between modules.
- Prefer configuration over hardcoded values.
- Do not silently change existing interfaces.

### Code rules

- Use Python best practices.
- Use type hints.
- Use meaningful names.
- Add docstrings to important public functions/classes.
- Handle exceptions explicitly.
- Avoid global mutable state.
- Keep functions focused on one responsibility.
- Use logging rather than random `print()` statements for application diagnostics.
- Keep hardware-dependent code isolated.

### AI modification rules

Before modifying code, the AI should:

1. Read the relevant documentation.
2. Understand the existing architecture.
3. Identify which module is responsible for the requested functionality.
4. Check whether the required functionality already exists.
5. Modify the smallest appropriate module.
6. Check whether interfaces have changed.
7. Update documentation if necessary.
8. Update `CHANGELOG.md`.
9. Explain any architectural changes.

An AI tool must not restructure unrelated parts of the project simply because it believes another architecture is better.

---

# 6. File and Function Reference

Create:

```text
docs_camera/FILE_FUNCTION_REFERENCE.md
```

This document must provide a complete overview of the project.

For every Python file, explain:

- file name
- purpose
- responsibility
- classes
- functions
- inputs
- outputs
- dependencies
- functions called from other modules
- what those external functions do
- important data structures exchanged

Use tables.

For example:

| File | Function | Purpose | Input | Output | Calls |
|---|---|---|---|---|---|
| camera_manager.py | `get_frame()` | Retrieves latest camera frame | None | `FrameData` | Camera driver |
| detector.py | `detect_parts()` | Detects configured parts | `FrameData` | `DetectionResult` | Detection model |
| coordinate.py | `image_to_robot()` | Converts image coordinates | Pixel coordinate | Robot coordinate | Calibration module |

Also document dependencies between files.

Example:

```text
camera_manager.py
        ↓
frame_processor.py
        ↓
part_detector.py
        ↓
coordinate_transform.py
        ↓
pick_target_manager.py
        ↓
robot_interface.py
```

If:

```python
detector.py
```

calls:

```python
camera_manager.get_frame()
```

the documentation must explain what `get_frame()` returns and how the detector uses it.

The purpose is that a future AI tool can understand the project without having to reverse-engineer every Python file.

---

# 7. System Architecture

Design the system around clearly separated modules.

A proposed high-level architecture is:

```text
                    ┌─────────────────────┐
                    │   Configuration     │
                    │   + Parameters      │
                    └──────────┬──────────┘
                               │
                               ▼
┌───────────────┐      ┌──────────────────┐
│     Camera    │─────►│ Camera Manager   │
└───────────────┘      └────────┬─────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ Image Processing │
                       └────────┬─────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  Part Detector   │
                       └────────┬─────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ Detection Result │
                       │ Count + Position │
                       └────────┬─────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ Coordinate       │
                       │ Transformation   │
                       └────────┬─────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ Pick Target      │
                       │ Manager          │
                       └────────┬─────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ Robot Interface  │
                       └────────┬─────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Delta Robot    │
                       └──────────────────┘
```

This is a starting architecture, not a requirement to use these exact names.

You should refine the architecture if a better modular structure is justified.

---

# 8. Camera Integration

The live camera must be isolated from the rest of the application.

Create a camera abstraction so that the application does not depend directly on one specific camera implementation.

For example:

```text
Camera Interface
       │
       ├── RealSense Camera
       ├── USB Camera
       └── Other Camera
```

The rest of the application should interact with the camera through a common interface.

The camera subsystem should be responsible for:

- opening the camera
- configuring resolution
- configuring FPS
- starting the stream
- retrieving frames
- stopping the stream
- handling camera errors
- releasing resources

The camera module should NOT be responsible for:

- detecting parts
- calculating robot coordinates
- deciding which part should be picked
- communicating with the robot

---

# 9. Live Video Processing

The system must support live video processing.

Conceptually:

```text
Camera
   ↓
Live Frame
   ↓
Pre-processing
   ↓
Detection
   ↓
Detected Objects
   ↓
Coordinates
```

The system should process frames continuously while the application is running.

However, the architecture should allow different processing modes, for example:

```text
LIVE
SINGLE_FRAME
DEBUG
```

A debug mode would be useful for development.

---

# 10. Part Detection

The detection system must identify the configured target part.

The detection implementation should be abstracted.

Potential future detection methods include:

- OpenCV contour detection
- template matching
- feature matching
- color/shape detection
- classical computer vision
- YOLO/object detection
- another ML model

Do not lock the entire application architecture to one detection method.

Create a detector interface or equivalent abstraction.

For example:

```text
PartDetector
     │
     ├── OpenCVDetector
     ├── TemplateDetector
     └── YOLODetector
```

The first implementation can use the simplest reliable method based on the final requirements.

---

# 11. Reference Part Dataset

Create a clear mechanism for defining which part the system should detect.

The project should contain a directory for reference datasets.

For example:

```text
parts/
│
├── round_part/
│   ├── reference_01.jpg
│   ├── reference_02.jpg
│   └── reference_03.jpg
│
└── square_part/
    ├── reference_01.jpg
    ├── reference_02.jpg
    └── reference_03.jpg
```

The exact implementation should be decided after clarification.

The important requirement is:

> The user should be able to change the target part by changing the configured/reference dataset rather than modifying Python source code.

For example:

```text
Current target:
parts/round_part/
```

could later become:

```text
parts/square_part/
```

through configuration.

If there is only one active target directory, the system should automatically use the currently configured target.

If multiple part classes are eventually required, the architecture should be extendable to support them.

---

# 12. Detection Output

The detector must return structured data rather than loosely formatted values.

Define a clear data model.

For example:

```text
DetectionResult
│
├── timestamp
├── frame_id
├── image_width
├── image_height
├── detection_count
└── detections[]
      │
      ├── class_name
      ├── confidence
      ├── center_x_pixel
      ├── center_y_pixel
      ├── bounding_box
      └── additional metadata
```

A detection should contain at least:

```text
part/class name
confidence
pixel X
pixel Y
bounding box
```

The exact Python representation should be determined during implementation.

Prefer typed structures such as:

```python
dataclass
```

where appropriate.

---

# 13. Part Counting

The system must determine:

> How many target parts are currently visible in the camera image?

For example:

```text
Detected parts: 5
```

The count should be part of the structured detection result.

The system should not simply print the number to the console.

The count must be available to downstream modules.

---

# 14. Coordinate Extraction

For every detected part, determine its image coordinate.

At minimum:

```text
X_pixel
Y_pixel
```

The coordinate convention must be explicitly documented.

For example:

```text
Origin = top-left of image
X = positive toward image right
Y = positive toward image bottom
```

Do not assume this convention without documenting it.

The system must clearly distinguish between:

```text
Image coordinates
```

and:

```text
Robot coordinates
```

---

# 15. Coordinate Transformation

The final objective is to use the camera position to command the Delta robot.

Therefore, the system will eventually need:

```text
Pixel Coordinates
        ↓
Camera Coordinates
        ↓
Robot Coordinates
```

The exact transformation method should be determined based on the physical camera/robot setup.

Potential methods include:

- planar calibration
- homography
- affine transformation
- camera calibration
- depth-based transformation
- hand-eye calibration

Do not assume the final method until the physical setup is clarified.

Create a dedicated coordinate transformation module so that the method can later be replaced without modifying the detector.

---

# 16. Pick Target Generation

After detecting multiple parts, the system should generate a list of possible pick targets.

Example:

```text
PickTarget 1
    X = ...
    Y = ...
    Z = ...

PickTarget 2
    X = ...
    Y = ...
    Z = ...
```

The system should eventually support:

```text
Detection
    ↓
Target selection
    ↓
Pick target
    ↓
Robot
```

The target-selection logic should be separated from detection.

For example, later we may want to select:

- nearest part
- leftmost part
- rightmost part
- highest-confidence part
- part with minimum travel distance
- specific class

Do not hardcode these decisions into the detector.

---

# 17. Robot Interface

The robot communication layer must be isolated from vision processing.

The detector should NOT directly communicate with the robot.

Instead:

```text
Vision System
      ↓
PickTarget
      ↓
Robot Interface
      ↓
Robot Controller
      ↓
Delta Robot
```

The robot interface should expose clear functions/methods for operations such as:

```text
send_pick_target()
get_robot_status()
is_robot_ready()
notify_pick_complete()
```

The exact interface should be determined after clarification of the robot controller and communication protocol.

Potential protocols may include:

- Modbus TCP
- OPC UA
- TCP/IP
- REST/API
- another industrial communication protocol

Do not implement a specific protocol until the required interface is confirmed.

---

# 18. Configuration

Do not hardcode important system parameters throughout Python files.

Create a centralized configuration mechanism.

Parameters may include:

```text
camera
resolution
FPS
exposure
target part
reference dataset path
confidence threshold
detection parameters
calibration path
coordinate system
robot communication settings
logging settings
debug settings
```

Use a clear configuration structure.

For example:

```text
config/
├── camera.yaml
├── vision.yaml
├── robot.yaml
└── system.yaml
```

The exact configuration format can be chosen based on maintainability.

Document every configuration parameter in:

```text
docs_camera/CONFIGURATION.md
```

For each parameter explain:

| Parameter | Purpose | Example | Required | Used By |
|---|---|---|---|---|

---

# 19. Paths and Infrastructure

Document all important project paths.

The system must clearly define:

```text
project root
docs_camera/
source code
configuration
reference images
calibration files
logs
tests
```

Do not rely on the current working directory.

Use robust path handling, preferably based on the project root.

The documentation must explain what infrastructure needs to exist for the system to run.

For example:

```text
Camera connected
Python environment configured
Required packages installed
Reference images available
Configuration available
Calibration available
Robot communication available
```

---

# 20. Data Flow Documentation

Create:

```text
docs_camera/DATA_FLOW.md
```

Document exactly how data travels through the system.

Example:

```text
Camera
  │
  │ Frame
  ▼
CameraManager
  │
  │ FrameData
  ▼
ImageProcessor
  │
  │ ProcessedFrame
  ▼
PartDetector
  │
  │ DetectionResult
  ▼
CoordinateTransformer
  │
  │ RobotCoordinates
  ▼
PickTargetManager
  │
  │ PickTarget
  ▼
RobotInterface
  │
  │ Robot Command
  ▼
Delta Robot
```

For every transition explain:

- what data is produced
- data type/structure
- who consumes it
- what transformation happens
- what errors can occur

The objective is that another AI can understand the complete data flow without reading every implementation detail.

---

# 21. Camera-to-Backend Interface

Clearly document how the live camera connects to the backend.

The expected conceptual flow is:

```text
Physical Camera
      ↓
Camera Driver / SDK
      ↓
Camera Manager
      ↓
Frame Object
      ↓
Vision Pipeline
      ↓
Detection Result
```

Document:

- camera initialization
- camera connection
- frame acquisition
- frame format
- frame rate
- resolution
- image color format
- depth availability if applicable
- error handling
- shutdown behavior

If the camera provides RGB + depth, document both streams separately.

---

# 22. Logging

The application should use structured logging.

Log important events such as:

```text
Camera connected
Camera disconnected
Detection started
Detection completed
Number of detected parts
Target generated
Robot connection established
Robot command sent
Communication failure
Calibration failure
Configuration error
```

Avoid excessive logging inside high-frequency frame-processing loops.

Provide appropriate logging levels such as:

```text
DEBUG
INFO
WARNING
ERROR
```

---

# 23. Error Handling

The system must handle failures gracefully.

Examples:

### Camera unavailable

```text
Application starts
      ↓
Camera connection fails
      ↓
Clear error message
      ↓
Application does not crash unexpectedly
```

### No parts detected

This is NOT necessarily an error.

Return:

```text
count = 0
detections = []
```

### Robot unavailable

The vision subsystem should not silently pretend that the robot accepted the target.

The communication state must be explicit.

---

# 24. Testing Structure

Create a test structure such as:

```text
tests/
│
├── test_camera.py
├── test_detector.py
├── test_coordinates.py
├── test_target_manager.py
├── test_configuration.py
└── test_robot_interface.py
```

Hardware-dependent tests should be separated from unit tests where practical.

The project should allow testing detection and coordinate transformation without physically running the Delta robot.

---

# 25. Development Milestones

Create:

```text
docs_camera/MILESTONES.md
```

Use milestones similar to the following.

## Milestone 1 — Project Architecture

Goal:

- establish folder structure
- define modules
- define interfaces
- define data structures
- create documentation

Deliverable:

A clean project skeleton that does not yet require complete vision functionality.

---

## Milestone 2 — Camera Integration

Goal:

- connect camera
- configure stream
- retrieve frames
- display/save test frames
- implement error handling

Deliverable:

Stable camera acquisition module.

---

## Milestone 3 — Live Video Pipeline

Goal:

- process live frames
- establish frame-processing loop
- add logging
- add debug visualization

Deliverable:

Stable live camera pipeline.

---

## Milestone 4 — Part Detection

Goal:

- implement first detection method
- detect configured target part
- determine bounding boxes
- determine center coordinates
- calculate confidence where applicable

Deliverable:

Structured `DetectionResult`.

---

## Milestone 5 — Part Counting

Goal:

- detect all visible target parts
- return total count
- expose all detected objects

Deliverable:

Reliable multi-object detection result.

---

## Milestone 6 — Reference Dataset / Dynamic Part Selection

Goal:

- implement reference-part directory structure
- configure active target
- allow changing target part without modifying source code
- validate reference data

Deliverable:

Replaceable part datasets.

---

## Milestone 7 — Camera Calibration

Goal:

- establish camera coordinate system
- calibrate camera/workspace
- determine relationship between image coordinates and physical coordinates

Deliverable:

Calibration data and documented calibration procedure.

---

## Milestone 8 — Image-to-Robot Coordinates

Goal:

```text
Pixel X/Y
   ↓
Physical X/Y
   ↓
Robot X/Y/Z
```

Deliverable:

Validated coordinate transformation.

---

## Milestone 9 — Pick Target Generation

Goal:

- generate robot-compatible pick targets
- select target according to defined strategy
- prevent duplicate/invalid targets

Deliverable:

Structured pick-target output.

---

## Milestone 10 — Robot Communication

Goal:

- establish robot-controller communication
- send target coordinates
- receive robot status
- handle communication errors

Deliverable:

Vision-to-robot communication.

---

## Milestone 11 — End-to-End Integration

Goal:

```text
Camera
 ↓
Detection
 ↓
Counting
 ↓
Coordinates
 ↓
Target Selection
 ↓
Robot
 ↓
Pick
```

Deliverable:

Complete working pick-and-place pipeline.

---

## Milestone 12 — Validation and Optimization

Evaluate:

- detection accuracy
- coordinate accuracy
- repeatability
- processing speed
- latency
- false detections
- missed detections
- robot positioning accuracy

Document the results.

---

# 26. Change Management

Create:

```text
docs_camera/CHANGELOG.md
```

Every meaningful project change should be recorded.

Use a structure such as:

```text
## YYYY-MM-DD

### Added
- ...

### Changed
- ...

### Fixed
- ...

### Documentation
- ...

### Reason
- ...
```

The changelog should explain WHY a significant change was made, not only what was changed.

Example:

```text
2026-08-13

Changed:
- Separated camera acquisition from detection.

Reason:
- Prevent camera-specific implementation from being coupled to the vision algorithm.
```

---

# 27. README

Create:

```text
docs_camera/README.md
```

It should provide a high-level introduction for a new developer or AI.

It should explain:

1. What the project does
2. How the architecture works
3. How to start the application
4. Required dependencies
5. Configuration
6. Camera setup
7. Reference-part setup
8. Expected outputs
9. Robot integration
10. Documentation map

The README should link conceptually to the other documentation files.

---

# 28. Important Architectural Requirement

The project must follow the principle:

```text
Hardware
    ↓
Hardware abstraction
    ↓
Processing
    ↓
Business logic
    ↓
Communication
```

Avoid:

```text
camera.py
    ↓
does everything
    ↓
robot
```

The camera should not know that a Delta robot exists.

The detector should not know which communication protocol the robot uses.

The robot interface should not know how the image was processed.

This separation is critical.

---

# 29. Expected Long-Term Architecture

The final architecture should conceptually resemble:

```text
                         CONFIGURATION
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                    VISION APPLICATION                    │
│                                                         │
│  ┌──────────────┐    ┌───────────────┐                 │
│  │    Camera    │───►│ Image Pipeline│                 │
│  │   Manager    │    └───────┬───────┘                 │
│  └──────────────┘            │                         │
│                              ▼                         │
│                       ┌──────────────┐                 │
│                       │ Part Detector│                 │
│                       └──────┬───────┘                 │
│                              │                         │
│                              ▼                         │
│                       DetectionResult                  │
│                              │                         │
│                              ▼                         │
│                    Coordinate Transformer              │
│                              │                         │
│                              ▼                         │
│                       Pick Targets                     │
│                              │                         │
│                              ▼                         │
│                       Robot Interface                  │
└──────────────────────────────┬──────────────────────────┘
                               │
                               ▼
                         Robot Controller
                               │
                               ▼
                          Delta Robot
```

---

# 30. First Task for Codex

Before implementing the complete system:

### Step 1

Inspect the existing project directory.

### Step 2

Determine whether any existing camera/vision/robot code already exists.

### Step 3

Do not overwrite existing functionality without understanding it.

### Step 4

Ask me the clarification questions listed below.

### Step 5

Based on my answers, propose:

- final architecture
- final folder structure
- module responsibilities
- data models
- interfaces
- dependencies
- configuration structure
- milestone plan

### Step 6

Wait for confirmation before implementing major architectural components.

---

# 31. Questions You Must Ask Me Before Finalizing the Architecture

Ask me these questions and do not make assumptions where the answer materially affects the implementation.

## Camera

1. What exact camera will be used?
2. Is it an Intel RealSense camera, USB camera, industrial camera, or something else?
3. Do I need RGB only, or RGB + depth?
4. What resolution and FPS should be used?
5. Is the camera fixed above the Delta robot?
6. What is the approximate camera-to-workspace distance?
7. Is the camera perpendicular to the working plane or at an angle?

## Parts

8. What types of parts need to be detected?
9. Are parts always stationary during detection?
10. Can multiple parts appear simultaneously?
11. Can different types of parts appear simultaneously?
12. Do the parts overlap?
13. Are the parts always on the same plane?
14. Do parts have similar colors/backgrounds?
15. Should the system identify the exact orientation of a part, or only its center position?

## Reference Images

16. How do I want to provide reference images?
17. Should the system support one active part at a time or multiple classes?
18. How many reference images are expected per part?
19. Should adding/removing images automatically change the active detection model?
20. Should the user select the active part through configuration, folder name, or automatically based on available folders?

## Detection Technology

21. Do you prefer classical OpenCV initially, or should we use an AI model such as YOLO?
22. Do you already have a trained model?
23. Is the goal eventually to train a custom model?
24. What minimum detection accuracy is acceptable?

## Coordinates

25. What coordinate system does the Delta robot use?
26. What is the robot's X/Y/Z coordinate convention?
27. Is Z constant for picking?
28. Do we need only X/Y or X/Y/Z?
29. How will camera coordinates be calibrated to robot coordinates?
30. Do we already have calibration points available?

## Robot

31. What exact Delta robot and controller are being used?
32. What controller communicates with the Python application?
33. Which communication protocol should be used?
34. Does the robot expect one target at a time or a list of targets?
35. Should Python only provide coordinates, or should Python control the complete pick-and-place sequence?
36. How should Python know that the robot has completed a pick?

## Performance

37. What is the required detection latency?
38. How many frames per second should actually be processed?
39. Does detection need to happen continuously, or only when the robot requests a new target?
40. What should happen if the robot is busy?

## Safety / Industrial Behavior

41. What should happen if no part is detected?
42. What should happen if multiple parts are detected?
43. What should happen if the coordinate is outside the robot's workspace?
44. What should happen if the camera disconnects?
45. What should happen if robot communication fails?

## Development Environment

46. Which Python version should be used?
47. What operating system will run the vision application?
48. Should the project use a virtual environment?
49. Are there restrictions on installing packages?
50. Should the application eventually run automatically as a service?

## User Interface

51. Do you want a GUI?
52. Should the live camera feed be displayed?
53. Should detected parts be drawn with bounding boxes?
54. Should coordinates/counts be displayed on the live image?
55. Do you need a manual trigger for detection?

---

# 32. Important Instruction to the AI

If any answer above is unknown and it materially affects the architecture, **ask me instead of guessing**.

However, do not ask unnecessary questions when a reasonable implementation-independent abstraction can be created.

The goal is to build a system that is:

- modular
- maintainable
- testable
- documented
- hardware-independent where possible
- suitable for industrial integration
- understandable by future AI coding tools
- easy to extend
- easy to debug

The final implementation should prioritize a clean architecture and clearly defined interfaces over writing the maximum amount of code as quickly as possible.