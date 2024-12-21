// Show change password modal
window.showChangePasswordModal = function() {
    document.getElementById('changePasswordModal').style.display = 'block';
}

// Close change password modal
window.closeChangePasswordModal = function() {
    document.getElementById('changePasswordModal').style.display = 'none';
    document.getElementById('changePasswordForm').reset();
}

// Handle change password form submission
window.handleChangePassword = async function(event) {
    event.preventDefault();
    
    const currentPassword = document.getElementById('currentPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    if (newPassword !== confirmPassword) {
        alert('New passwords do not match!');
        return;
    }
    
    try {
        const response = await fetch('/change-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                currentPassword: currentPassword,
                newPassword: newPassword
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert('Password changed successfully!');
            closeChangePasswordModal();
        } else {
            alert(data.error || 'Failed to change password');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred while changing password');
    }
} 