/**
 * Asset Detail Management - JavaScript Module
 * Handles dynamic loading and management of asset details, maintenance points, and history
 */

class AssetDetailManager {
    constructor(assetId) {
        this.assetId = assetId;
        this.userRole = null;
        this.init();
    }

    async init() {
        try {
            await this.loadAssetData();
            await this.loadDetailPoints();
            await this.loadMaintenanceHistory();
            this.setupEventListeners();
        } catch (error) {
            console.error('Error initializing asset detail manager:', error);
            this.showError('เกิดข้อผิดพลาดในการโหลดข้อมูล');
        }
    }

    async loadAssetData() {
        const response = await fetch(`/api/asset/${this.assetId}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to load asset data');
        }

        this.userRole = data.user_role;
        this.renderAssetInfo(data.asset, data.is_pm_due);
    }

    async loadDetailPoints() {
        const response = await fetch(`/api/asset/${this.assetId}/detail-points`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to load detail points');
        }

        this.renderDetailPoints(data.detail_points);
    }

    async loadMaintenanceHistory() {
        const response = await fetch(`/api/asset/${this.assetId}/maintenance-history`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to load maintenance history');
        }

        this.renderMaintenanceHistory(data.history);
    }

    renderAssetInfo(asset, isPmDue) {
        // Update page title
        document.getElementById('asset-title').textContent = `รายละเอียดเครื่องจักร: ${asset.name}`;
        
        // Show/hide edit button based on role
        const editButton = document.getElementById('edit-asset-btn');
        if (this.userRole === 'admin') {
            editButton.classList.remove('hidden-by-default');
            editButton.href = `/edit_asset/${asset.id}`;
        } else {
            editButton.classList.add('hidden-by-default');
        }

        // Show PM due alert
        const pmAlert = document.getElementById('pm-due-alert');
        if (isPmDue) {
            pmAlert.classList.remove('hidden-by-default');
            pmAlert.innerHTML = `
                <h4 class="alert-heading">ถึงกำหนดบำรุงรักษา!</h4>
                <p>เครื่องจักรนี้ถึงกำหนดการบำรุงรักษาเชิงป้องกัน (PM) แล้ว</p>
                <hr>
                <form action="/perform_pm/${asset.id}" method="post" class="d-inline">
                    <button type="submit" class="btn btn-success">ยืนยันการทำ PM และเลื่อนกำหนดการ</button>
                </form>
            `;
        } else {
            pmAlert.classList.add('hidden-by-default');
        }

        // Render asset image
        const imageContainer = document.getElementById('asset-image');
        if (asset.asset_image_filename) {
            imageContainer.innerHTML = `<img src="/uploads/${asset.asset_image_filename}" alt="รูปภาพของ ${asset.name}" class="img-fluid rounded shadow-sm">`;
        } else {
            imageContainer.innerHTML = `<div class="d-flex align-items-center justify-content-center bg-light rounded shadow-sm text-muted" style="height: 250px;"><span>ไม่มีรูปภาพ</span></div>`;
        }

        // Render asset details
        const detailsContainer = document.getElementById('asset-details');
        let detailsHtml = `
            <dt class="col-sm-4">ชื่อ</dt><dd class="col-sm-8">${asset.name}</dd>
            <dt class="col-sm-4">แผนก</dt><dd class="col-sm-8">${asset.location}</dd>
        `;
        
        if (asset.technician_name) {
            detailsHtml += `<dt class="col-sm-4">ผู้รับผิดชอบ</dt><dd class="col-sm-8">${asset.technician_name}</dd>`;
        }
        
        if (asset.next_pm_date) {
            detailsHtml += `<dt class="col-sm-4">PM ครั้งถัดไป</dt><dd class="col-sm-8">${asset.next_pm_date}</dd>`;
        }
        
        if (asset.pm_frequency_days) {
            detailsHtml += `<dt class="col-sm-4">ความถี่ PM</dt><dd class="col-sm-8">ทุกๆ ${asset.pm_frequency_days} วัน</dd>`;
        }

        // Add custom data
        if (asset.custom_data && typeof asset.custom_data === 'object') {
            Object.entries(asset.custom_data).forEach(([key, value]) => {
                detailsHtml += `<dt class="col-sm-4">${key}</dt><dd class="col-sm-8">${value}</dd>`;
            });
        }

        detailsContainer.innerHTML = detailsHtml;
        
        // Update export link
        const exportBtn = document.getElementById('export-history-btn');
        if (exportBtn) {
            exportBtn.href = `/export_asset_history/${asset.id}`;
        }
    }

    renderDetailPoints(detailPoints) {
        const container = document.getElementById('detail-points-container');
        
        if (detailPoints.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <p>ยังไม่มีจุดรายละเอียดการบำรุงรักษา</p>
                </div>
            `;
            return;
        }

        const pointsHtml = detailPoints.map(point => {
            const imageHtml = point.image_filename 
                ? `<img src="/uploads/${point.image_filename}" class="card-img-top detail-point-card-img" alt="${point.title}">`
                : `<div class="card-img-top d-flex align-items-center justify-content-center bg-light text-muted detail-point-placeholder"><span>ไม่มีรูปภาพ</span></div>`;
            
            const locationHtml = point.location_detail 
                ? `<p class="card-text"><small class="text-muted"><i class="fas fa-map-marker-alt"></i> ${point.location_detail}</small></p>`
                : '';
            
            const descriptionHtml = point.description 
                ? `<p class="card-text">${point.description}</p>`
                : '';
            
            const deleteButtonHtml = this.userRole === 'admin' 
                ? `<button type="button" class="btn btn-sm btn-outline-danger" onclick="assetManager.deleteDetailPoint(${point.id})">ลบ</button>`
                : '';

            return `
                <div class="col-md-6 col-lg-4 mb-4">
                    <div class="card">
                        ${imageHtml}
                        <div class="card-body">
                            <h5 class="card-title">${point.title}</h5>
                            ${locationHtml}
                            ${descriptionHtml}
                            <div class="d-flex justify-content-between align-items-center">
                                <small class="text-muted">${point.created_at.split(' ')[0]}</small>
                                <div>
                                    <button type="button" class="btn btn-sm btn-outline-secondary" onclick="assetManager.editDetailPoint(${point.id})">แก้ไข</button>
                                    ${deleteButtonHtml}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = `<div class="row">${pointsHtml}</div>`;
    }

    renderMaintenanceHistory(history) {
        const tbody = document.getElementById('maintenance-history-tbody');
        
        if (history.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted">ยังไม่มีประวัติการซ่อม</td></tr>';
            return;
        }

        const historyHtml = history.map(item => {
            const cost = item.cost !== null && item.cost !== undefined 
                ? Number(item.cost).toFixed(2)
                : 'N/A';
            
            return `
                <tr>
                    <td>${item.date.split(' ')[0]}</td>
                    <td>${item.description}</td>
                    <td>${cost}</td>
                </tr>
            `;
        }).join('');

        tbody.innerHTML = historyHtml;
    }

    setupEventListeners() {
        // Add detail point form
        const addPointForm = document.getElementById('add-detail-point-form');
        if (addPointForm) {
            addPointForm.addEventListener('submit', (e) => this.handleAddDetailPoint(e));
        }

        // Add maintenance form
        const addMaintenanceForm = document.getElementById('add-maintenance-form');
        if (addMaintenanceForm) {
            addMaintenanceForm.addEventListener('submit', (e) => this.handleAddMaintenance(e));
        }

        // File input display
        const fileInput = document.getElementById('point_image');
        const fileChosen = document.getElementById('file-chosen');
        if (fileInput && fileChosen) {
            fileInput.addEventListener('change', function() {
                fileChosen.textContent = this.files.length > 0 ? this.files[0].name : 'ยังไม่ได้เลือกไฟล์';
            });
        }
    }

    async handleAddDetailPoint(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        formData.append('asset_id', this.assetId);

        try {
            const response = await fetch('/api/detail-point', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                this.showSuccess(data.message);
                e.target.reset();
                document.getElementById('file-chosen').textContent = 'ยังไม่ได้เลือกไฟล์';
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('addDetailPointModal'));
                if (modal) modal.hide();
                
                // Reload detail points
                await this.loadDetailPoints();
            } else {
                this.showError(data.error || 'เกิดข้อผิดพลาดในการเพิ่มจุดรายละเอียด');
            }
        } catch (error) {
            console.error('Error adding detail point:', error);
            this.showError('เกิดข้อผิดพลาดในการเพิ่มจุดรายละเอียด');
        }
    }

    async handleAddMaintenance(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const data = {
            asset_id: this.assetId,
            description: formData.get('description'),
            cost: formData.get('cost') ? parseFloat(formData.get('cost')) : null
        };

        try {
            const response = await fetch('/api/maintenance', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok) {
                this.showSuccess(result.message);
                e.target.reset();
                
                // Reload maintenance history
                await this.loadMaintenanceHistory();
            } else {
                this.showError(result.error || 'เกิดข้อผิดพลาดในการเพิ่มประวัติการซ่อมบำรุง');
            }
        } catch (error) {
            console.error('Error adding maintenance:', error);
            this.showError('เกิดข้อผิดพลาดในการเพิ่มประวัติการซ่อมบำรุง');
        }
    }

    async deleteDetailPoint(pointId) {
        if (!confirm('คุณแน่ใจหรือไม่ว่าต้องการลบจุดรายละเอียดนี้?')) {
            return;
        }

        try {
            const response = await fetch(`/api/detail-point/${pointId}`, {
                method: 'DELETE'
            });

            const data = await response.json();

            if (response.ok) {
                this.showSuccess(data.message);
                await this.loadDetailPoints();
            } else {
                this.showError(data.error || 'เกิดข้อผิดพลาดในการลบจุดรายละเอียด');
            }
        } catch (error) {
            console.error('Error deleting detail point:', error);
            this.showError('เกิดข้อผิดพลาดในการลบจุดรายละเอียด');
        }
    }

    editDetailPoint(pointId) {
        // For now, redirect to edit page - could be made modal-based later
        window.location.href = `/edit_detail_point/${pointId}`;
    }

    showSuccess(message) {
        this.showAlert(message, 'success');
    }

    showError(message) {
        this.showAlert(message, 'danger');
    }

    showAlert(message, type) {
        // Remove existing alerts
        const existingAlerts = document.querySelectorAll('.dynamic-alert');
        existingAlerts.forEach(alert => alert.remove());

        // Create new alert
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show dynamic-alert`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        // Insert at top of content
        const contentArea = document.querySelector('.container-fluid > div');
        if (contentArea) {
            contentArea.insertBefore(alertDiv, contentArea.firstChild);
        }

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

// Global variable to hold the manager instance
let assetManager;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const assetId = window.location.pathname.split('/').pop();
    if (assetId && !isNaN(assetId)) {
        assetManager = new AssetDetailManager(assetId);
    }
});
