/**
 * TTApp - Frontend JavaScript
 * Handles UI interactions and API calls
 */

// Initialize date picker to today
document.addEventListener('DOMContentLoaded', function() {
    const dateInput = document.getElementById('absenceDate');
    if (dateInput) {
        dateInput.value = new Date().toISOString().split('T')[0];
    }
    
    const timetableDateInput = document.getElementById('timetableDate');
    if (timetableDateInput) {
        timetableDateInput.value = new Date().toISOString().split('T')[0];
    }
    
    // Load teachers for timetable generation
    loadTeachersForTimetable();
    
    // Check if setup is needed
    checkSetupStatus();
});

/**
 * Load teachers into the select dropdown for timetable generation
 */
async function loadTeachersForTimetable() {
    try {
        const response = await fetch('/api/teachers');
        const data = await response.json();
        
        if (data.success) {
            const select = document.getElementById('teacherSelect');
            if (select) {
                select.innerHTML = '<option value="">-- Select a teacher --</option>';
                data.teachers.forEach(teacher => {
                    const option = document.createElement('option');
                    option.value = teacher.id;
                    option.textContent = teacher.name + (teacher.is_leisure ? ' (Leisure)' : '');
                    select.appendChild(option);
                });
            }
        }
    } catch (error) {
        console.error('Error loading teachers:', error);
    }
}

/**
 * Check if initial setup is needed
 */
async function checkSetupStatus() {
    try {
        const [teachersRes, subjectsRes, classesRes] = await Promise.all([
            fetch('/api/teachers'),
            fetch('/api/subjects'),
            fetch('/api/classes')
        ]);
        
        const teachersData = await teachersRes.json();
        const subjectsData = await subjectsRes.json();
        const classesData = await classesRes.json();
        
        const hasData = teachersData.success && teachersData.teachers.length > 0 &&
                       subjectsData.success && subjectsData.subjects.length > 0 &&
                       classesData.success && classesData.classes.length > 0;
        
        const reminder = document.getElementById('setupReminder');
        if (reminder) {
            reminder.style.display = hasData ? 'none' : 'block';
        }
    } catch (error) {
        console.error('Error checking setup status:', error);
    }
}

/**
 * Toggle configuration section visibility
 */
function toggleConfig() {
    const content = document.getElementById('configContent');
    const toggle = document.getElementById('configToggle');
    
    if (content.style.display === 'none') {
        content.style.display = 'block';
        toggle.textContent = '▲';
    } else {
        content.style.display = 'none';
        toggle.textContent = '▼';
    }
}

/**
 * Show loading overlay
 */
function showLoading() {
    document.getElementById('loadingOverlay').style.display = 'flex';
}

/**
 * Hide loading overlay
 */
function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

/**
 * Display message in results section
 */
function showMessage(message, type = 'success') {
    const resultsSection = document.getElementById('resultsSection');
    const resultsContent = document.getElementById('resultsContent');
    
    resultsSection.style.display = 'block';
    resultsContent.innerHTML = `<div class="message message-${type}">${message}</div>`;
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Generate initial schedule
 */
document.getElementById('generateScheduleBtn').addEventListener('click', async function() {
    showLoading();
    
    const numClasses = parseInt(document.getElementById('numClasses').value) || 5;
    const numSubjects = parseInt(document.getElementById('numSubjects').value) || 7;
    const periodsPerDay = parseInt(document.getElementById('periodsPerDay').value) || 8;
    
    try {
        const response = await fetch('/api/generate-schedule', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                num_classes: numClasses,
                num_subjects: numSubjects,
                periods_per_day: periodsPerDay
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage(data.message, 'success');
        } else {
            showMessage(data.message || 'Error generating schedule', 'error');
        }
    } catch (error) {
        showMessage('Network error: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
});

/**
 * View absent teachers and substitutions
 */
document.getElementById('viewAbsentBtn').addEventListener('click', async function() {
    showLoading();
    
    const dateInput = document.getElementById('absenceDate');
    const selectedDate = dateInput.value || new Date().toISOString().split('T')[0];
    
    try {
        const response = await fetch(`/api/absent-teachers?date=${selectedDate}`);
        const data = await response.json();
        
        if (data.success) {
            displayAbsentTeachers(data);
        } else {
            showMessage(data.message || 'Error fetching absent teachers', 'error');
        }
    } catch (error) {
        showMessage('Network error: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
});

/**
 * Display absent teachers and substitution suggestions
 */
function displayAbsentTeachers(data) {
    const absentSection = document.getElementById('absentDetailsSection');
    const absentContent = document.getElementById('absentDetailsContent');
    
    absentSection.style.display = 'block';
    
    if (data.absences.length === 0) {
        absentContent.innerHTML = `
            <div class="message message-success">
                <strong>✅ No absences recorded for ${data.date}</strong>
                <p>All teachers are present today!</p>
            </div>
        `;
    } else {
        let html = '';
        
        data.absences.forEach(absence => {
            html += `
                <div class="absence-card">
                    <h3>❌ ${absence.teacher.name} is absent</h3>
                    <p><strong>Date:</strong> ${data.date}</p>
                    <p><strong>Status:</strong> ${absence.is_substituted ? '✅ Substituted' : '⚠️ Not yet substituted'}</p>
                    
                    <div class="substitution-suggestions">
                        <h4>Substitution Suggestions:</h4>
            `;
            
            if (absence.substitution_suggestions.length === 0) {
                html += '<p>No substitution suggestions available at this time.</p>';
            } else {
                absence.substitution_suggestions.forEach(suggestion => {
                    html += `
                        <div class="substitution-item">
                            <h4>${suggestion.class_name} - Period ${suggestion.period} (${suggestion.subject_name})</h4>
                            <p><strong>Available Substitutes:</strong></p>
                            <div class="substitute-list">
                    `;
                    
                    if (suggestion.available_substitutes.length === 0) {
                        html += '<span class="substitute-badge">No available substitutes</span>';
                    } else {
                        suggestion.available_substitutes.forEach(substitute => {
                            html += `<span class="substitute-badge">${substitute.name}</span>`;
                        });
                    }
                    
                    html += `
                            </div>
                        </div>
                    `;
                });
            }
            
            html += `
                    </div>
                </div>
            `;
        });
        
        absentContent.innerHTML = html;
    }
    
    // Scroll to absent section
    absentSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Update absent teachers when date changes
 */
document.getElementById('absenceDate')?.addEventListener('change', function() {
    // Auto-refresh when date changes (if absent section is visible)
    if (document.getElementById('absentDetailsSection').style.display !== 'none') {
        document.getElementById('viewAbsentBtn').click();
    }
});

/**
 * Generate timetable for selected teacher
 */
document.getElementById('generateTeacherTimetableBtn')?.addEventListener('click', async function() {
    const teacherId = document.getElementById('teacherSelect').value;
    const dateInput = document.getElementById('timetableDate');
    const selectedDate = dateInput.value || new Date().toISOString().split('T')[0];
    
    if (!teacherId) {
        alert('Please select a teacher first.');
        return;
    }
    
    showLoading();
    
    try {
        const response = await fetch(`/api/teacher-timetable/${teacherId}?date=${selectedDate}`);
        const data = await response.json();
        
        if (data.success) {
            displayTeacherTimetable(data);
        } else {
            showMessage(data.message || 'Error generating timetable', 'error');
        }
    } catch (error) {
        showMessage('Network error: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
});

/**
 * Display teacher timetable
 */
function displayTeacherTimetable(data) {
    const resultDiv = document.getElementById('teacherTimetableResult');
    
    if (!resultDiv) return;
    
    resultDiv.style.display = 'block';
    
    if (data.timetable.length === 0) {
        const message = data.message || 'No classes scheduled for this day.';
        resultDiv.innerHTML = `
            <div class="message message-success">
                <strong>📅 ${data.teacher.name}'s Timetable for ${data.day_name} (${data.date})</strong>
                <p>${message}</p>
                ${data.day_name === 'Saturday' || data.day_name === 'Sunday' ? '<p><em>💡 Tip: Try selecting a weekday (Monday-Friday) to view the schedule.</em></p>' : ''}
            </div>
        `;
    } else {
        let html = `
            <div class="timetable-header">
                <h3>📅 ${data.teacher.name}'s Timetable</h3>
                <p><strong>Date:</strong> ${data.day_name}, ${data.date}</p>
            </div>
            <table class="timetable-table">
                <thead>
                    <tr>
                        <th>Period</th>
                        <th>Class</th>
                        <th>Subject</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        data.timetable.forEach(item => {
            html += `
                <tr>
                    <td><strong>Period ${item.period}</strong></td>
                    <td>${item.class_name}</td>
                    <td>${item.subject_name}</td>
                </tr>
            `;
        });
        
        html += `
                </tbody>
            </table>
        `;
        
        resultDiv.innerHTML = html;
    }
    
    // Scroll to result
    resultDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

