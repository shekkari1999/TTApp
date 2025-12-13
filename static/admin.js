/**
 * Admin Setup Page JavaScript
 * Handles CRUD operations for teachers, subjects, and classes
 */

// Load data when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadTeachers();
    loadSubjects();
    loadClasses();
});

/**
 * TEACHERS MANAGEMENT
 */
async function loadTeachers() {
    try {
        const response = await fetch('/api/teachers');
        const data = await response.json();
        
        if (data.success) {
            displayTeachers(data.teachers);
        }
    } catch (error) {
        console.error('Error loading teachers:', error);
    }
}

function displayTeachers(teachers) {
    const container = document.getElementById('teachersList');
    
    if (teachers.length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary);">No teachers added yet. Click "Add Teacher" to get started.</p>';
        return;
    }
    
    container.innerHTML = teachers.map(teacher => `
        <div class="data-card">
            <div class="data-card-info">
                <div class="data-card-name">
                    ${teacher.name}
                    ${teacher.is_class_teacher ? '<span class="badge badge-class-teacher">Class Teacher</span>' : ''}
                    ${teacher.is_leisure ? '<span class="badge badge-leisure">Leisure</span>' : ''}
                </div>
                <div class="data-card-meta">ID: ${teacher.id}</div>
            </div>
            <div class="data-card-actions">
                <button class="btn btn-icon-only" onclick="editTeacher(${teacher.id})" title="Edit">✏️</button>
                <button class="btn btn-icon-only btn-delete" onclick="deleteTeacher(${teacher.id})" title="Delete">🗑️</button>
            </div>
        </div>
    `).join('');
}

function showAddTeacherForm() {
    document.getElementById('teacherModalTitle').textContent = 'Add Teacher';
    document.getElementById('teacherForm').reset();
    document.getElementById('teacherId').value = '';
    document.getElementById('teacherModal').style.display = 'flex';
}

async function editTeacher(id) {
    try {
        const response = await fetch('/api/teachers');
        const data = await response.json();
        const teacher = data.teachers.find(t => t.id === id);
        
        if (teacher) {
            document.getElementById('teacherModalTitle').textContent = 'Edit Teacher';
            document.getElementById('teacherId').value = teacher.id;
            document.getElementById('teacherName').value = teacher.name;
            document.getElementById('teacherIsClassTeacher').checked = teacher.is_class_teacher;
            document.getElementById('teacherIsLeisure').checked = teacher.is_leisure;
            document.getElementById('teacherModal').style.display = 'flex';
        }
    } catch (error) {
        console.error('Error loading teacher:', error);
    }
}

async function saveTeacher(event) {
    event.preventDefault();
    
    const id = document.getElementById('teacherId').value;
    const teacherData = {
        name: document.getElementById('teacherName').value,
        is_class_teacher: document.getElementById('teacherIsClassTeacher').checked,
        is_leisure: document.getElementById('teacherIsLeisure').checked
    };
    
    try {
        let response;
        if (id) {
            // Update
            response = await fetch(`/api/teachers/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(teacherData)
            });
        } else {
            // Create
            response = await fetch('/api/teachers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(teacherData)
            });
        }
        
        const data = await response.json();
        if (data.success) {
            closeModal('teacherModal');
            loadTeachers();
            if (id) {
                loadClasses(); // Reload classes in case class teacher changed
            }
        } else {
            alert('Error: ' + (data.message || 'Failed to save teacher'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function deleteTeacher(id) {
    if (!confirm('Are you sure you want to delete this teacher?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/teachers/${id}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        if (data.success) {
            loadTeachers();
            loadClasses(); // Reload classes in case class teacher was deleted
        } else {
            alert('Error: ' + (data.message || 'Failed to delete teacher'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

/**
 * SUBJECTS MANAGEMENT
 */
async function loadSubjects() {
    try {
        const response = await fetch('/api/subjects');
        const data = await response.json();
        
        if (data.success) {
            displaySubjects(data.subjects);
        }
    } catch (error) {
        console.error('Error loading subjects:', error);
    }
}

function displaySubjects(subjects) {
    const container = document.getElementById('subjectsList');
    
    if (subjects.length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary);">No subjects added yet. Click "Add Subject" to get started.</p>';
        return;
    }
    
    container.innerHTML = subjects.map(subject => `
        <div class="data-card">
            <div class="data-card-info">
                <div class="data-card-name">${subject.name}</div>
                <div class="data-card-meta">ID: ${subject.id}</div>
            </div>
            <div class="data-card-actions">
                <button class="btn btn-icon-only" onclick="editSubject(${subject.id})" title="Edit">✏️</button>
                <button class="btn btn-icon-only btn-delete" onclick="deleteSubject(${subject.id})" title="Delete">🗑️</button>
            </div>
        </div>
    `).join('');
}

function showAddSubjectForm() {
    document.getElementById('subjectModalTitle').textContent = 'Add Subject';
    document.getElementById('subjectForm').reset();
    document.getElementById('subjectId').value = '';
    document.getElementById('subjectModal').style.display = 'flex';
}

async function editSubject(id) {
    try {
        const response = await fetch('/api/subjects');
        const data = await response.json();
        const subject = data.subjects.find(s => s.id === id);
        
        if (subject) {
            document.getElementById('subjectModalTitle').textContent = 'Edit Subject';
            document.getElementById('subjectId').value = subject.id;
            document.getElementById('subjectName').value = subject.name;
            document.getElementById('subjectModal').style.display = 'flex';
        }
    } catch (error) {
        console.error('Error loading subject:', error);
    }
}

async function saveSubject(event) {
    event.preventDefault();
    
    const id = document.getElementById('subjectId').value;
    const subjectData = {
        name: document.getElementById('subjectName').value
    };
    
    try {
        let response;
        if (id) {
            response = await fetch(`/api/subjects/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(subjectData)
            });
        } else {
            response = await fetch('/api/subjects', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(subjectData)
            });
        }
        
        const data = await response.json();
        if (data.success) {
            closeModal('subjectModal');
            loadSubjects();
        } else {
            alert('Error: ' + (data.message || 'Failed to save subject'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function deleteSubject(id) {
    if (!confirm('Are you sure you want to delete this subject?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/subjects/${id}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        if (data.success) {
            loadSubjects();
        } else {
            alert('Error: ' + (data.message || 'Failed to delete subject'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

/**
 * CLASSES MANAGEMENT
 */
async function loadClasses() {
    try {
        const response = await fetch('/api/classes');
        const data = await response.json();
        
        if (data.success) {
            displayClasses(data.classes);
            populateClassTeacherSelect(data.classes);
        }
    } catch (error) {
        console.error('Error loading classes:', error);
    }
}

async function populateClassTeacherSelect(classes) {
    // Load teachers for the select dropdown
    const teachersResponse = await fetch('/api/teachers');
    const teachersData = await teachersResponse.json();
    
    const select = document.getElementById('classTeacherId');
    select.innerHTML = '<option value="">None</option>';
    
    if (teachersData.success) {
        teachersData.teachers.forEach(teacher => {
            const option = document.createElement('option');
            option.value = teacher.id;
            option.textContent = teacher.name;
            select.appendChild(option);
        });
    }
}

function displayClasses(classes) {
    const container = document.getElementById('classesList');
    
    if (classes.length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary);">No classes added yet. Click "Add Class" to get started.</p>';
        return;
    }
    
    // Load teachers to get names
    fetch('/api/teachers')
        .then(r => r.json())
        .then(data => {
            const teachers = data.teachers || [];
            const teacherMap = {};
            teachers.forEach(t => teacherMap[t.id] = t.name);
            
            container.innerHTML = classes.map(classObj => `
                <div class="data-card">
                    <div class="data-card-info">
                        <div class="data-card-name">${classObj.name}</div>
                        <div class="data-card-meta">
                            ${classObj.class_teacher_id ? `Class Teacher: ${teacherMap[classObj.class_teacher_id] || 'Unknown'}` : 'No class teacher assigned'}
                        </div>
                    </div>
                    <div class="data-card-actions">
                        <button class="btn btn-icon-only" onclick="editClass(${classObj.id})" title="Edit">✏️</button>
                        <button class="btn btn-icon-only btn-delete" onclick="deleteClass(${classObj.id})" title="Delete">🗑️</button>
                    </div>
                </div>
            `).join('');
        });
}

function showAddClassForm() {
    document.getElementById('classModalTitle').textContent = 'Add Class';
    document.getElementById('classForm').reset();
    document.getElementById('classId').value = '';
    populateClassTeacherSelect([]);
    document.getElementById('classModal').style.display = 'flex';
}

async function editClass(id) {
    try {
        const response = await fetch('/api/classes');
        const data = await response.json();
        const classObj = data.classes.find(c => c.id === id);
        
        if (classObj) {
            document.getElementById('classModalTitle').textContent = 'Edit Class';
            document.getElementById('classId').value = classObj.id;
            document.getElementById('className').value = classObj.name;
            await populateClassTeacherSelect([]);
            document.getElementById('classTeacherId').value = classObj.class_teacher_id || '';
            document.getElementById('classModal').style.display = 'flex';
        }
    } catch (error) {
        console.error('Error loading class:', error);
    }
}

async function saveClass(event) {
    event.preventDefault();
    
    const id = document.getElementById('classId').value;
    const classData = {
        name: document.getElementById('className').value,
        class_teacher_id: document.getElementById('classTeacherId').value || null
    };
    
    try {
        let response;
        if (id) {
            response = await fetch(`/api/classes/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(classData)
            });
        } else {
            response = await fetch('/api/classes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(classData)
            });
        }
        
        const data = await response.json();
        if (data.success) {
            closeModal('classModal');
            loadClasses();
        } else {
            alert('Error: ' + (data.message || 'Failed to save class'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function deleteClass(id) {
    if (!confirm('Are you sure you want to delete this class?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/classes/${id}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        if (data.success) {
            loadClasses();
        } else {
            alert('Error: ' + (data.message || 'Failed to delete class'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

/**
 * MODAL MANAGEMENT
 */
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modals = ['teacherModal', 'subjectModal', 'classModal'];
    modals.forEach(modalId => {
        const modal = document.getElementById(modalId);
        if (event.target === modal) {
            closeModal(modalId);
        }
    });
}

