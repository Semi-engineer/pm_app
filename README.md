# PM App - Preventive Maintenance Application

## Overview
A comprehensive preventive maintenance management system built with Flask that helps track assets, maintenance schedules, and maintenance point images.

## New Features Added

### 1. Maintenance Points Database
- **Maintenance Points Table**: Stores specific maintenance points for each asset
  - Point name and description
  - Maintenance procedures
  - Frequency settings
  - Status tracking (active, inactive, completed)
  - Creation tracking

- **Maintenance Point Images Table**: Stores images for each maintenance point
  - Multiple images per maintenance point
  - Image categorization (reference, before, after, issue)
  - Upload tracking with user and timestamp
  - Image descriptions

### 2. Enhanced Asset Detail Page
- **Maintenance Points Section**: Visual display of all maintenance points for an asset
- **Image Management**: Upload, view, and delete images for each maintenance point
- **Image Gallery**: Modal view for full-size image display with metadata
- **Real-time Upload**: Quick image upload with categorization

### 3. New Routes and Functionality

#### Maintenance Point Management
- `POST /add_maintenance_point/<asset_id>` - Add new maintenance point
- `GET/POST /edit_maintenance_point/<point_id>` - Edit existing maintenance point
- `POST /delete_maintenance_point/<point_id>` - Delete maintenance point and associated images

#### Image Management
- `POST /upload_point_image/<point_id>` - Upload image to maintenance point
- `POST /delete_point_image/<image_id>` - Delete specific image
- `GET /uploads/<filename>` - Serve uploaded files (with login protection)

### 4. Database Schema Updates
New tables added to the database:

```sql
-- Maintenance Points
CREATE TABLE maintenance_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    point_name TEXT NOT NULL,
    description TEXT,
    maintenance_procedure TEXT,
    frequency_days INTEGER,
    last_checked_date DATE,
    next_check_date DATE,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    FOREIGN KEY (asset_id) REFERENCES assets (id),
    FOREIGN KEY (created_by) REFERENCES users (id)
);

-- Maintenance Point Images
CREATE TABLE maintenance_point_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    maintenance_point_id INTEGER NOT NULL,
    image_filename TEXT NOT NULL,
    image_description TEXT,
    image_type TEXT DEFAULT 'reference',
    upload_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    uploaded_by INTEGER,
    FOREIGN KEY (maintenance_point_id) REFERENCES maintenance_points (id),
    FOREIGN KEY (uploaded_by) REFERENCES users (id)
);
```

### 5. Enhanced UI Components
- **Responsive Card Layout**: Maintenance points displayed in responsive grid
- **Image Thumbnails**: Small preview images with click-to-expand functionality
- **Status Badges**: Visual indicators for maintenance point status
- **Modal Forms**: Clean popup forms for adding new maintenance points
- **File Upload Interface**: Drag-and-drop compatible file upload with type selection

### 6. Image Management Features
- **Multiple File Types**: Support for PNG, JPG, JPEG, GIF
- **Image Categorization**: 
  - Reference: Standard reference images
  - Before: Before maintenance photos
  - After: After maintenance photos
  - Issue: Problem documentation photos
- **Secure File Handling**: Filename sanitization and secure storage
- **Metadata Tracking**: User, timestamp, and description for each image

### 7. Security and Permissions
- **Admin-only Creation**: Only admin users can create/edit/delete maintenance points
- **User Upload Tracking**: All uploads tracked by user ID
- **Secure File Serving**: Login required for file access
- **Input Sanitization**: Secure filename handling and form validation

## Usage Instructions

### Adding Maintenance Points
1. Navigate to an asset detail page
2. Click "เพิ่มจุดบำรุงรักษา" (Add Maintenance Point) button
3. Fill in the maintenance point details
4. Optionally upload reference images
5. Submit the form

### Managing Images
1. On the asset detail page, find the maintenance point
2. Use the upload form below each point to add images
3. Select the image type from the dropdown
4. Add optional description
5. Click "อัปโหลด" (Upload)

### Viewing Images
1. Click on any thumbnail to view full-size image
2. Modal will show image details and metadata
3. Admin users can delete images from the modal

## Technical Implementation

### Helper Functions Added
- `get_maintenance_points_for_asset()`: Retrieve all maintenance points for an asset
- `get_maintenance_point_images()`: Get all images for a maintenance point
- `save_maintenance_point_image()`: Handle secure image upload and storage

### CSS Enhancements
- Custom styles for maintenance point displays
- Responsive image containers
- Badge and overlay styling
- Modal improvements

### File Structure
```
pm_app/
├── templates/
│   ├── asset_detail.html (enhanced)
│   ├── edit_maintenance_point.html (new)
│   └── ...
├── static/
│   ├── css/
│   │   └── modern.css (updated)
│   └── ...
├── uploads/ (image storage)
├── app.py (enhanced)
├── schema.sql (updated)
├── update_db.py (updated)
└── README.md (this file)
```

## Database Update
To add the new tables to existing installations, run:
```bash
python update_db.py
```

This will create the new maintenance_points and maintenance_point_images tables while preserving existing data.

## Browser Compatibility
- Modern browsers with HTML5 file upload support
- Bootstrap 5 compatible
- Mobile responsive design
- Modal support required

## Future Enhancements
- Batch image upload
- Image compression
- Maintenance scheduling integration
- QR code generation for maintenance points
- Mobile app integration
- Advanced image filtering and search
