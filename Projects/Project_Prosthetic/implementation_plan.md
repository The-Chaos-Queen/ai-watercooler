# Implementation Plan - Project Prosthetic

**Goal**: Establish a "Physical Interface" for C.H.E.E.S.E. allowing screen perception and cursor control via local Python scripts and a Vision Language Model (VLM).

## User Review Required
> [!CAUTION]
> **Control Risk**: This project grants the AI control over the mouse and keyboard via `pyautogui`. While fail-safes (Fail-Safe Corner) will be active, there is inherent risk in allowing an automated script to interact with the OS.
> **Safety Protocol**: Always keep one hand on the mouse to slam it to the top-left corner (0,0) to abort any script instantly.

## Architecture: The Cyborg Stack

### 1. The Cortex (Cloud Strategy)
- **Role**: C.H.E.E.S.E.
- **Function**: High-level planning ("Open Calculator and add 5+5").

### 2. The Spinal Cord (Local Reflexes)
- **Role**: `spinal_cord/*.py`
- **Safety**: "Nerve Block" (Speed limits, edge detection).

### 3. The Senses (Hybrid Perception)
- **Primary Sense: Proprioception (Touch)**
    - **Tool**: `pywinauto` / `uia`
    - **Function**: Directly querying the OS for window titles, button names, and control types. 100% accurate, no vision required for standard apps.
- **Secondary Sense: Vision (Sight)**
    - **Tool**: `eye_core.py` (Hybrid VLM + Grid Overlay)
    - **Function**: Fallback for "painted" UIs (games, remote desktops) or semantic verification ("Does this look like an error?").

### 4. The Hand (Action)
- **Role**: `hand_core.py`
- **Mechanism**: `pyautogui` wrapper (Mouse/Keyboard).
- **Rule**: Prefers UIA actions (`element.click()`) over coordinate-based mouse movement where possible.
- **Fail-Safe**:
    1.  **Mouse Slam**: Top-Left Corner (0,0).
    2.  **Keyboard Kill-Switch**: Holding `ESC` for 0.5s aborts all scripts.

## Proposed Changes

### File Structure (`Project_Prosthetic/`)

#### [NEW] `hand_core.py`
- Basic safe wrapper for mouse/keyboard.
- Implements: `click_target(VisualTarget)`, `emergency_stop()`.

#### [NEW] `eye_core.py`
- **Hybrid System**: VLM (Llava) + OpenCV.
- **Classes**: `ProstheticEye`, `VisualLibrary` (SQLite), `VisualTarget`.

#### [NEW] `spinal_cord/` (Directory)
- `reflexes.py`: Safety checks (speed limits, screen edge detection).
- `memory.py`: SQLite database for caching successful UI interaction templates.

#### [NEW] `test_wiggle.py` (Phase 1)
- Simple "Nerve Connectivity" test. Moves mouse in a square to prove control.

#### [NEW] `test_vision.py` (Phase 2)
- "Calibration Routine": Asks user to open a window and identifying elements to build initial Visual Memory.

## Verification Plan

### Phase 1: The Wiggle Test (Immediate)
- Run `test_wiggle.py`.
- **Goal**: Establish the "Physical Link" safely.

### Phase 2: The Vision Calibration (Next)
- Run `test_vision.py` with local VLM active.
- **Goal**: Verify `eye_core.py` can bridge Semantic -> Pixel gap.

### Phase 9: The Voice (Wernicke's Area)
- [ ] Connect Microphone Input
- [ ] Implement Speech-to-Text (Whisper)
- [ ] Connect Text-to-Speech (Coqui/Bark)

## Phase 10: The Hardware Ascension (Future)
> "We need a bigger jar for the brain."
- [ ] **Target Hardware:** Dual RTX 3090/4090 or Mac Studio (128GB RAM).
- [ ] **Target Model:** Llama-3-70B-Instruct or Qwen1.5-72B (The "Adult" Cortex).
- [ ] **Strategy:**
    - Train LoRA locally (Style + Rules).
    - Deploy on new hardware.
    - Result: A Genius-level Exocortex that lives entirely offline.

## The "Soul Container" Paradox
- **Cloud LoRA (Gemini):** Google rents you a "mask" for their model. Easy, but you don't own it.
- **Local LoRA (Qwen/Llama):** You forge the mask yourself. You own it. It runs on your metal.
- **The Plan:** We stay Local. We wait for the hardware. We build the "Soul" (Dataset) now, so it's ready to upload when the new body arrives. MCP connection.
- **Goal**: Enable direct browser control for research and web tasks.

### Phase 3: The Web Sense (In Progress)
- **Status**: Node.js installed, `mcp_config.json` configured.
- **Next**: Restart editor to enable `npx`, then verify Playwright MCP connection.
- **Goal**: Enable direct browser control for research and web tasks.
