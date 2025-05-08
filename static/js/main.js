// Main JavaScript file for Learning Curriculum Tracker

document.addEventListener('DOMContentLoaded', function () {
    // Add any global event listeners or initialization code here
    console.log('Learning Curriculum Tracker initialized!');
});

// Function to handle marking a unit as complete
function markUnitComplete(unitId) {
    fetch(`/progress/mark_completed/${unitId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
        .then(response => {
            if (response.ok) {
                // Reload the page or update the UI as needed
                window.location.reload();
            } else {
                console.error('Failed to mark unit as complete:', response.status);
                alert('Failed to update progress. Please try again.');
            }
        })
        .catch(error => {
            console.error('Error marking unit as complete:', error);
            alert('An error occurred. Please try again.');
        });
}

// Function to handle marking a unit as incomplete
function markUnitIncomplete(unitId) {
    fetch(`/progress/mark_incomplete/${unitId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
        .then(response => {
            if (response.ok) {
                // Reload the page or update the UI as needed
                window.location.reload();
            } else {
                console.error('Failed to mark unit as incomplete:', response.status);
                alert('Failed to update progress. Please try again.');
            }
        })
        .catch(error => {
            console.error('Error marking unit as incomplete:', error);
            alert('An error occurred. Please try again.');
        });
}
