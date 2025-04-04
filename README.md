# GUI-application-to-simulate-basic-logic-gates-using-nodes-with-PyQt
GUI node editor with a topbar (File: New, Open, Save, Exit; Edit: Undo, Redo, Cut, Copy, Paste, Delete; Window: theme), side panel with draggable nodes (Input, Output, AND, OR, NOT, NAND, NOR, XOR, XNOR), and tabbed main window. Supports logic operations, file saving, and text output.
# Node Editor Application

## Overview
This is a GUI-based node editor application designed for creating and simulating digital logic workflows. It features a topbar with menu options, a side panel for node selection, and a main window with tabbed interfaces for building node trees.

## IGNORE
Ignore the small implementation folder it is just for executing small task so i can come up with the whole project.
## Features

### Topbar Menus:
- **File**: New (new tab), Open (load file), Save (save active tab), Exit (close app).
- **Edit**: Undo, Redo, Cut, Copy, Paste, Delete.
- **Window**: Change application theme.

### Side Panel:
- Displays draggable nodes for drag-and-drop into the main window.

### Main Window:
- Supports multiple tabbed node editor interfaces.

## Node Types

### Input:
- Text field for user-defined values.

### Output:
- **Normal**: Displays net output of the node tree.
- **Write**: Button generates a `.txt` file with output.

### Logic Gates:
- **AND**: 2 inputs, 1 output (logical AND).
- **OR**: 2 inputs, 1 output (logical OR).
- **NOT**: 1 input, 1 output (logical NOT).
- **NAND**: 2 inputs, 1 output (logical NAND).
- **NOR**: 2 inputs, 1 output (logical NOR).
- **XOR**: 2 inputs, 1 output (logical XOR).
- **XNOR**: 2 inputs, 1 output (logical XNOR).

## Prerequisites

- **Python 3.x**
- **Required libraries**: (Specify based on implementation, e.g., `tkinter` for GUI, or `PyQt5`, etc.)
- **Operating System**: Windows, macOS, or Linux

## Installation

1. Clone or download this repository:
   ```sh
   git clone <repository-url>
   cd node-editor
   ```
2. Install dependencies:
   ```sh
   pip install PyQt5
   pip install tkinter
   ```
   (Create a `requirements.txt` with required libraries like `tkinter` or `PyQt5` if applicable.)

## How to Run

1. Navigate to the project directory:
   ```sh
   cd node-editor
   ```
2. Run the application:
   ```sh
   python main.py
   ```
   (Replace `main.py` with your main script name.)
3. The GUI will launch, allowing you to:
   - Create a new tab via `File > New`.
   - Drag nodes from the side panel to the main window.
   - Connect nodes to simulate logic operations.
   - Save your work via `File > Save`.

## Usage

- **Creating a Workflow**: Use `File > New` to start, then drag nodes (e.g., Input, AND, Output) into the tab. Connect sockets to build logic circuits.
- **Saving**: Select `File > Save` to store the active tab’s configuration.
- **Output**: Use the `Write Output` node to export results to a `.txt` file.
- **Theming**: Adjust the app’s appearance via `Window > Theme`.

## Project Structure

```
node-editor/
├── main.py                 # Main application script                
├── README.md               # This file
```

## Contributing
Feel free to fork this repository, submit pull requests, or report issues to enhance functionality.


