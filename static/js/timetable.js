// DOM Elements
const classSelect = document.getElementById('classSelect');
const loading = document.getElementById('loading');
const error = document.getElementById('error');
const timetableContainer = document.getElementById('timetableContainer');
const timetableBody = document.getElementById('timetableBody');
const emptyState = document.getElementById('emptyState');

// State
let currentClassId = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadClasses();
});

// Load all available classes
async function loadClasses() {
    try {
        const response = await fetch('/api/classes');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const classes = await response.json();
        
        // Clear existing options
        classSelect.innerHTML = '';
        
        if (classes.length === 0) {
            classSelect.innerHTML = '<option value="">No classes available</option>';
            return;
        }
        
        // Add default option
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = 'Select a class...';
        classSelect.appendChild(defaultOption);
        
        // Populate dropdown with classes
        classes.forEach(cls => {
            const option = document.createElement('option');
            option.value = cls.id;
            option.textContent = cls.name;
            classSelect.appendChild(option);
        });
        
        // Auto-select first class and load its timetable
        if (classes.length > 0) {
            classSelect.value = classes[0].id;
            currentClassId = classes[0].id;
            loadTimetable(currentClassId);
        }
        
    } catch (err) {
        console.error('Error loading classes:', err);
        classSelect.innerHTML = '<option value="">Error loading classes</option>';
        showError();
    }
}

// Load timetable for selected class
async function loadTimetable(classId) {
    if (!classId) {
        hideAll();
        return;
    }
    
    // Show loading state
    showLoading();
    
    try {
        const response = await fetch(`/api/class-schedules?classId=${classId}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const schedule = await response.json();
        
        // Check if schedule has data
        if (!schedule.slots || schedule.slots.length === 0) {
            showEmptyState();
            return;
        }
        
        // Render the timetable
        renderTimetable(schedule);
        showTimetable();
        
    } catch (err) {
        console.error('Error loading timetable:', err);
        showError();
    }
}

// Render timetable grid
function renderTimetable(schedule) {
    // Clear existing content
    timetableBody.innerHTML = '';
    
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
    const periods = schedule.periods || [1, 2, 3, 4, 5, 6];
    
    // Create a map for quick lookup
    const slotsMap = new Map();
    schedule.slots.forEach(slot => {
        const key = `${slot.day}-${slot.period}`;
        slotsMap.set(key, slot);
    });
    
    // Generate rows for each period
    periods.forEach(period => {
        const row = document.createElement('tr');
        
        // Period number cell
        const periodCell = document.createElement('td');
        periodCell.className = 'period-number';
        periodCell.textContent = `Period ${period}`;
        row.appendChild(periodCell);
        
        // Cells for each day
        days.forEach(day => {
            const cell = document.createElement('td');
            const key = `${day}-${period}`;
            const slot = slotsMap.get(key);
            
            if (slot) {
                // Create slot info HTML
                const slotDiv = document.createElement('div');
                slotDiv.className = 'slot-info';
                
                const subjectDiv = document.createElement('div');
                subjectDiv.className = 'subject';
                subjectDiv.textContent = slot.subject;
                
                const teacherDiv = document.createElement('div');
                teacherDiv.className = 'teacher';
                teacherDiv.textContent = `(${slot.teacher})`;
                
                slotDiv.appendChild(subjectDiv);
                slotDiv.appendChild(teacherDiv);
                cell.appendChild(slotDiv);
            } else {
                // Empty slot
                const emptyDiv = document.createElement('div');
                emptyDiv.className = 'empty-slot';
                emptyDiv.textContent = '-';
                cell.appendChild(emptyDiv);
            }
            
            row.appendChild(cell);
        });
        
        timetableBody.appendChild(row);
    });
}

// UI State Management Functions
function showLoading() {
    loading.style.display = 'block';
    error.style.display = 'none';
    timetableContainer.style.display = 'none';
    emptyState.style.display = 'none';
}

function showTimetable() {
    loading.style.display = 'none';
    error.style.display = 'none';
    timetableContainer.style.display = 'block';
    emptyState.style.display = 'none';
}

function showError() {
    loading.style.display = 'none';
    error.style.display = 'block';
    timetableContainer.style.display = 'none';
    emptyState.style.display = 'none';
}

function showEmptyState() {
    loading.style.display = 'none';
    error.style.display = 'none';
    timetableContainer.style.display = 'none';
    emptyState.style.display = 'block';
}

function hideAll() {
    loading.style.display = 'none';
    error.style.display = 'none';
    timetableContainer.style.display = 'none';
    emptyState.style.display = 'none';
}

// Event Listeners
classSelect.addEventListener('change', (e) => {
    const selectedClassId = e.target.value;
    currentClassId = selectedClassId;
    
    if (selectedClassId) {
        loadTimetable(selectedClassId);
    } else {
        hideAll();
    }
});

// Retry button for error state (if you want to add one)
function retry() {
    if (currentClassId) {
        loadTimetable(currentClassId);
    } else {
        loadClasses();
    }
}