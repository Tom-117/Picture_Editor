# Picture Editor

A comprehensive, feature-rich image editing application built with Python. Picture Editor provides professional-grade image manipulation tools in a user-friendly desktop application with support for layers, advanced drawing tools, and batch processing capabilities.

## Overview

Picture Editor is designed to provide a complete image editing solution with an emphasis on performance and usability. The application features a modern graphical user interface built with CustomTkinter and leverages powerful image processing libraries including PIL, OpenCV, and pytesseract for OCR capabilities.

The application has been extensively optimized for smooth performance, providing instant visual feedback during drawing operations and rapid batch processing of multiple images.

## Features

### Drawing and Painting Tools

Picture Editor includes a comprehensive set of drawing tools for creating and modifying images:

- Brush tool with adjustable size and color for freehand drawing
- Line drawing tool for creating straight lines between points
- Rectangle shape tool with optional fill
- Circle shape tool with optional fill
- Eraser tool for removing content with adjustable size
- Customizable brush sizes ranging from 1 to 100 pixels
- Real-time color selection with visual feedback

### Text Editing

Add and manipulate text directly on your images:

- Text insertion at any position on the canvas
- Configurable font sizes from 10 to 200 pixels
- Independent text color selection
- Text formatting with stroke outlines for better visibility
- Automatic font loading with fallback to default system font

### Layer System

Work with multiple layers for non-destructive editing:

- Create unlimited layers for complex compositions
- Move layers up and down in the hierarchy
- Merge layers with merge down functionality
- Flatten all layers into a single layer
- Individual layer visibility toggling
- Layer opacity control from 0 to 100 percent
- Blend mode support including normal, multiply, screen, and overlay modes
- Automatic drawing layer creation and management

### Image Transformations

Transform and modify image dimensions and orientation:

- Image resizing with custom width and height
- 90-degree rotation in both directions
- Horizontal and vertical flipping
- Crop tool with visual rectangle selection
- All transformations apply to all active layers

### Filters and Effects

Apply professional filters and effects to enhance images:

- Grayscale conversion for black and white effects
- Gaussian blur with configurable kernel sizes
- Sharpening filters for enhanced details
- Sepia tone for vintage effects
- Vintage effect for aged appearance
- All filters support preview before application

### Batch Processing

Process multiple images efficiently:

- Batch import of multiple images in supported formats
- Apply consistent transformations across all selected images
- Batch filter application with uniform settings
- Progress tracking during batch operations
- Cancel functionality to stop processing at any time
- Support for PNG, JPG, JPEG, BMP, TIFF, and WEBP formats

### Advanced Image Editing

Professional-level image adjustment and manipulation:

- Background removal using GrabCut algorithm with transparent or custom background
- Optical Character Recognition (OCR) for extracting text from images
- Brightness adjustment with range from 0.1x to 3.0x
- Contrast enhancement with range from 0.1x to 3.0x
- Saturation control from 0.0x to 3.0x
- Sharpness adjustment from 0.0x to 3.0x
- Live preview of adjustments before application
- Adjustment slider interface for intuitive control

### Navigation and Viewing

Interact with images on the canvas:

- Zoom in and out with mouse wheel support
- Pan (scroll) the image with right-click dragging
- Smooth scrollbars for canvas navigation
- Real-time zoom level tracking
- Automatic adjustment for zoomed display optimization

### History and Undo/Redo

Manage your editing workflow with comprehensive history:

- Unlimited undo functionality with Ctrl+Z shortcut
- Redo functionality with Ctrl+Y shortcut
- Full history management with up to 50 edit states
- Complete state restoration including layers and adjustments
- Visual feedback on undo/redo operations

### File Management

Save and load your work:

- Open images in multiple formats (PNG, JPG, JPEG, BMP, TIFF, WEBP)
- Save edited images in PNG and JPEG formats
- Full layer composition export
- Transparency preservation for formats that support it
- Keyboard shortcuts for quick file operations (Ctrl+O to open, Ctrl+S to save)

## Installation

### System Requirements

- Python 3.8 or higher
- Windows, macOS, or Linux
- Tesseract-OCR installed for OCR functionality

### Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

Key dependencies include:
- customtkinter - Modern UI framework
- Pillow - Image processing
- opencv-python - Computer vision operations
- numpy - Numerical computing
- pytesseract - OCR integration

### Tesseract Setup

For OCR functionality to work properly, you need to install Tesseract-OCR:

Windows: Download and run the installer from https://github.com/UB-Mannheim/tesseract/wiki

macOS: Use Homebrew to install:
```bash
brew install tesseract
```

Linux: Use your package manager:
```bash
sudo apt-get install tesseract-ocr
```

After installation, ensure the Tesseract path is correctly configured in the application (default for Windows: C:\Program Files\Tesseract-OCR\tesseract.exe).

## Usage

### Starting the Application

Run the application with:

```bash
python app.py
```

The application will open with a dark theme interface divided into a left sidebar for tools and controls, and a main canvas area for image editing.

### Basic Workflow

1. Open an image using the file dialog or Ctrl+O
2. Select drawing or editing tools from the sidebar
3. Use the canvas to apply your edits
4. Adjust layers, opacity, and blend modes as needed
5. Save your work with Ctrl+S or through the File menu

### Drawing Mode

Enable drawing mode by checking the "Rajzolás be" (Drawing On) checkbox in the Drawing section. Once enabled:

1. Select your desired tool (Brush, Line, Rectangle, Circle, or Eraser)
2. Choose the color using the color picker
3. Adjust brush size using the slider (1-100 pixels)
4. Enable fill option for shapes if desired
5. Click and drag on the canvas to draw

### Text Addition

To add text to your image:

1. Check the "Szöveg mód" (Text Mode) checkbox
2. Type your desired text in the text input field
3. Click on the canvas where you want to place the text
4. A dialog will appear asking for font size (10-200)
5. The text will be placed at the clicked position with the selected color

### Layer Management

Manage your layers using the Layers panel:

1. Click "Réteg hozzáadása" (Add Layer) to create new layers
2. Use the up/down buttons to change layer order
3. Adjust opacity with the opacity slider for each layer
4. Select blend mode from the dropdown (Normal, Multiply, Screen, Overlay)
5. Click the eye icon to toggle layer visibility
6. Use "Merge Down" to combine with the layer below
7. Use "Flatten All" to merge all layers into one

### Filters and Adjustments

Apply effects to enhance your images:

1. Select a filter from the Szűrők (Filters) section
2. For adjustments (Brightness, Contrast, Saturation, Sharpness):
   - Move the sliders to preview changes
   - Click "Apply Adjustments" to finalize
   - Click "Reset Sliders" to return to default values

### Background Removal

Remove image backgrounds:

1. Click "Háttér eltávolítás" (Background Removal)
2. Select the region containing the foreground object
3. The application will analyze and extract the object
4. Choose transparent background or select a custom fill color

### OCR Text Extraction

Extract text from images:

1. Click "Szöveg kinyerése (OCR)" (Extract Text - OCR)
2. The application will analyze the image
3. Extracted text will be displayed in a dialog
4. Copy the text as needed

### Batch Processing

Process multiple images with consistent settings:

1. Click "Batch feldolgozás" (Batch Processing)
2. Select multiple images from your file system
3. Choose which operations to apply (filters, transformations)
4. Configure settings for each operation
5. Click "Start" to begin batch processing
6. Monitor progress and cancel if needed

## Performance Optimization

Picture Editor has been extensively optimized for smooth, responsive performance:

### Drawing Optimization

- Real-time drawing updates with optimized layer composition
- Separate drawing overlay combined with cached base layers
- Throttled canvas updates to maintain responsive UI while preventing excessive redraws
- Direct pixel manipulation for drawing operations

### Caching Strategy

- Base layer composition caching to avoid unnecessary recomposition
- Display image caching with zoom level tracking
- Prevents redundant image resampling for identical zoom levels
- Automatic cache invalidation when layers change

### Memory Management

- Extended history support with up to 50 undo states
- Efficient layer copying for undo/redo operations
- PhotoImage reference management to prevent garbage collection
- Proper cleanup of temporary overlay images

### Batch Processing

- Threaded operations for non-blocking UI
- Sequential file processing with progress tracking
- Cancellable operations for user control

## Keyboard Shortcuts

The application supports the following keyboard shortcuts:

- Ctrl+O: Open image
- Ctrl+S: Save image
- Ctrl+Z: Undo last action
- Ctrl+Y: Redo last action
- Ctrl+Shift+X: Toggle crop mode

## File Formats

### Supported Input Formats

- PNG (Portable Network Graphics) - with transparency
- JPG/JPEG (Joint Photographic Experts Group)
- BMP (Bitmap)
- TIFF (Tagged Image File Format)
- WEBP (WebP Image Format)

### Supported Output Formats

- PNG - preserves transparency and quality
- JPEG - efficient compression, no transparency

## User Interface

### Sidebar Controls

The left sidebar provides organized access to all tools and features:

- **File Operations**: Open and save buttons
- **Drawing Tools**: Tool selection and color picker
- **Brush Size**: Slider for adjusting brush/eraser size
- **Text Tools**: Text mode toggle and color selection
- **Layers Panel**: Layer management with visibility and opacity controls
- **Adjustments**: Sliders for brightness, contrast, saturation, and sharpness
- **Batch Processing**: Access to batch operations
- **Transformations**: Image rotation, flipping, and cropping
- **Filters**: Quick access to filter effects
- **Background Removal**: GrabCut-based background extraction
- **History**: Undo and redo buttons plus full application reset

### Main Canvas

The central canvas area displays:

- The current image with all applied edits
- Drawing overlay during brush/eraser operations
- Crop selection rectangle in crop mode
- Scrollbars for navigating large images
- Support for zoom in/out with mouse wheel

## Troubleshooting

### Application Runs Slowly

- Reduce image resolution if working with very large files
- Disable live preview for adjustments to improve responsiveness
- Close other applications to free system resources
- Reduce number of undo history states if memory is constrained

### OCR Text Extraction Not Working

- Verify Tesseract-OCR is installed correctly
- Check that the Tesseract path in the code matches your installation
- Ensure image contains clear, readable text
- Try improving image quality or contrast before OCR

### Background Removal Produces Poor Results

- Ensure good lighting and contrast in the foreground object
- Try adjusting the selection rectangle to focus on the main object
- Increase contrast using filters before background removal
- For complex backgrounds, consider manual editing with drawing tools

### Drawing Tools Feel Unresponsive

- Check system resources and close memory-intensive applications
- Reduce brush size for faster rendering
- Ensure zoom level is not excessively high
- Verify graphics card drivers are up to date

## Development and Customization

### Code Structure

The application is organized as a single Python file with a main `PictureEditor` class:

- UI Setup: `setup_ui()` method
- Event Handling: `on_click()`, `on_drag()`, `on_release()` methods
- Image Processing: `apply_filter()`, `compose_layers()`, `blend_images()` methods
- File I/O: `open_image()`, `save_image()` methods
- Layer Management: `add_layer()`, `merge_down()`, `flatten_all()` methods

### Extending Functionality

To add new features:

1. Add UI controls in the `setup_ui()` method
2. Implement feature logic in appropriate methods
3. Update layer composition if working with layers
4. Add keyboard bindings in `setup_bindings()` if needed
5. Include undo support by calling `save_state()` before modifications

### Performance Tweaks

Adjustable parameters for performance tuning:

- `adjustment_throttle_ms`: Delay between adjustment slider updates (default: 100ms)
- History limit: Currently set to 50 states, can be increased for more undo depth
- Drawing updates: Occur on every drag event for immediate feedback
- Resampling method: BILINEAR used for preview performance, LANCZOS for final exports

## Architecture Overview

### Layer Composition System

The application uses an efficient layer composition system:

- Base layers are composed once and cached as `base_cache`
- Drawing overlay is merged with cached base for instant preview
- Layer visibility and opacity are computed during composition
- Blend modes (normal, multiply, screen, overlay) are applied during composition
- Cache is invalidated when layers are modified

### Drawing System

Drawing operations are optimized for responsiveness:

- Drawing created on temporary overlay image
- Overlay merged with base only when released
- No full recomposition during drawing, only overlay blend
- Supports brush, eraser, line, rectangle, and circle tools
- Real-time visual feedback as user draws

### History System

The undo/redo system maintains full application state:

- Each edit state stores complete layer data and adjustments
- Up to 50 history states kept in memory
- Full state restoration on undo/redo
- Efficient memory management through copy operations

## Future Enhancements

Potential improvements for future versions:

- Support for additional file formats (GIF, animated WebP)
- Layer groups and hierarchical organization
- Selection tools (rectangle, ellipse, lasso, magic wand)
- Path and vector drawing tools
- Color correction and tone mapping
- Adjustment layers for non-destructive editing
- Plugin system for custom filters
- Network support for collaborative editing
- Advanced masking capabilities
- Gradient tools
- Pattern fill options

## License

This project is open source and available under the MIT License.

## Support and Contribution

For bug reports, feature requests, or contributions, please refer to the project repository.

## Acknowledgments

Picture Editor is built on top of several excellent open-source libraries:

- CustomTkinter for the modern UI framework
- Pillow (PIL) for image processing
- OpenCV for advanced computer vision operations
- pytesseract for OCR integration
- NumPy for numerical operations
- Tkinter for the underlying GUI toolkit